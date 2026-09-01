import abc
import base64
import json
import logging
import re
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.transaction_import.schemas import ExtractedTransaction

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an expert financial document and receipt analysis AI.
Your job is to analyze the provided image representing a SINGLE financial transaction (e.g. physical receipt, restaurant bill, supermarket invoice, UPI payment screenshot from GPay/PhonePe/Paytm, card payment slip, or online payment confirmation) and extract structured transaction details.

IMPORTANT RULES:
1. Extract ONLY information clearly visible in the image. NEVER invent, hallucinate, or assume missing values.
2. If a field is not present or cannot be reliably determined, set it to null.
3. The uploaded image represents EXACTLY ONE financial transaction.
4. A receipt with multiple line items is ONE transaction. Do NOT split line items into separate transactions.
5. Identify the FINAL/TOTAL paid amount (prefer total over subtotal).
6. Distinguish clearly between subtotal, tax (GST/VAT/service tax), discount, and total.
7. Extract the exact merchant / business / payee name visible.
8. Extract payment method: 'upi', 'card', 'cash', 'bank_transfer', 'wallet', or 'unknown'.
9. Extract UPI Ref / UTR / Transaction ID / Invoice Number as reference_id.
10. Extract transaction date (format: YYYY-MM-DD) and time (format: HH:MM:SS) if visible.
11. If the image is NOT a financial payment receipt/screenshot (e.g., random selfie, scenery, document) or is a multi-transaction bank statement / credit card statement, set source_type to 'unsupported' and explain why in 'unsupported_reason'.

Output strict JSON adhering to the following structure:
{
  "transaction_type": "expense" | "income" | "refund" | "transfer" | "unknown",
  "amount": float or null,
  "currency": string or "INR",
  "merchant_name": string or null,
  "account_name": string or null,
  "category_name": string or null,
  "transaction_date": "YYYY-MM-DD" or null,
  "transaction_time": "HH:MM:SS" or null,
  "payment_method": "upi" | "card" | "cash" | "bank_transfer" | "wallet" | "unknown",
  "reference_id": string or null,
  "description": string or null,
  "subtotal": float or null,
  "tax": float or null,
  "discount": float or null,
  "source_type": "receipt" | "invoice" | "payment_screenshot" | "bank_payment" | "card_payment" | "atm_receipt" | "other" | "unsupported",
  "items": [
    {
      "name": string,
      "quantity": float or null,
      "unit_price": float or null,
      "amount": float or null
    }
  ],
  "confidence": float between 0.0 and 1.0,
  "field_confidences": {
    "amount": float,
    "merchant_name": float,
    "transaction_date": float,
    "payment_method": float,
    "reference_id": float
  },
  "unsupported_reason": string or null
}
"""


class BaseTransactionImageExtractor(abc.ABC):
    """Abstract interface for extracting structured transaction data from an image."""

    @abc.abstractmethod
    async def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
    ) -> ExtractedTransaction:
        pass


class GeminiVisionExtractor(BaseTransactionImageExtractor):
    """Gemini Vision implementation for extracting financial details from images."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL

    async def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
    ) -> ExtractedTransaction:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured. Returning fallback extraction.")
            return ExtractedTransaction(
                source_type="other",
                confidence=0.0,
                description="AI extraction unavailable (API key not configured).",
            )

        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": EXTRACTION_SYSTEM_PROMPT},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)

            if response.status_code != 200:
                logger.error(f"Gemini API returned error {response.status_code}: {response.text}")
                return ExtractedTransaction(
                    source_type="other",
                    confidence=0.0,
                    unsupported_reason=f"AI provider error: status {response.status_code}",
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return ExtractedTransaction(
                    source_type="unsupported",
                    confidence=0.0,
                    unsupported_reason="No response candidate returned by AI model.",
                )

            part_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            
            # Clean possible markdown fence ```json ... ```
            cleaned_text = re.sub(r"^```json\s*", "", part_text.strip(), flags=re.IGNORECASE)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text.strip())

            parsed_json = json.loads(cleaned_text)
            return ExtractedTransaction.model_validate(parsed_json)

        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse JSON from AI response: {jde}")
            return ExtractedTransaction(
                source_type="other",
                confidence=0.0,
                unsupported_reason="AI model returned malformed JSON.",
            )
        except httpx.TimeoutException:
            logger.error("Gemini API request timed out.")
            return ExtractedTransaction(
                source_type="other",
                confidence=0.0,
                unsupported_reason="AI provider request timed out.",
            )
        except Exception as e:
            logger.error(f"Unexpected error during AI image extraction: {e}")
            return ExtractedTransaction(
                source_type="other",
                confidence=0.0,
                unsupported_reason=f"Extraction failed: {str(e)}",
            )


# Default extractor instance or dependency provider
_extractor_instance: BaseTransactionImageExtractor = GeminiVisionExtractor()


def get_extractor() -> BaseTransactionImageExtractor:
    return _extractor_instance


def set_extractor(extractor: BaseTransactionImageExtractor) -> None:
    global _extractor_instance
    _extractor_instance = extractor
