import difflib
import re
from typing import Any, Dict, List, Optional, Tuple
from beanie import PydanticObjectId

from app.models.account import Account
from app.models.category import Category, CategoryType
from app.models.credit_card import CreditCard
from app.models.transaction import Transaction, TransactionType
from app.transaction_import.schemas import EntityMatch

# Common merchant to category keywords
CATEGORY_KEYWORD_RULES: Dict[str, List[str]] = {
    "Food & Dining": [
        "restaurant", "cafe", "coffee", "tea", "swiggy", "zomato", "mcdonald", "starbucks",
        "kfc", "domino", "pizza", "burger", "baker", "dine", "kitchen", "bar", "food",
    ],
    "Groceries": [
        "grocery", "supermarket", "mart", "blinkit", "zepto", "instamart", "bigbasket",
        "nature basket", "spencer", "dmart", "reliance fresh", "vegetable", "fruits", "dairy",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "zara", "h&m", "nike", "adidas", "ajio",
        "clothing", "retail", "store", "mall", "electronics",
    ],
    "Transportation": [
        "uber", "ola", "rapido", "metro", "fuel", "petrol", "diesel", "hpcl", "bpcl",
        "iocl", "shell", "parking", "toll", "fastag", "taxi", "irctc", "rail",
    ],
    "Utilities & Bills": [
        "electricity", "water", "gas", "bescom", "tneb", "tatapower", "airtel", "jio",
        "vodafone", "vi", "broadband", "wifi", "recharge", "dth", "bill",
    ],
    "Entertainment": [
        "netflix", "spotify", "prime", "hotstar", "cinema", "pvr", "inox", "bookmyshow",
        "theatre", "movie", "gaming", "steam", "playstation",
    ],
    "Health & Medical": [
        "pharmacy", "chemist", "apollo", "medplus", "1mg", "hospital", "clinic", "doctor",
        "dental", "diagnostic", "pathology", "lab", "medicine",
    ],
    "Personal Care": [
        "salon", "spa", "beauty", "hair", "skin", "nykaa", "parlour", "grooming",
    ],
    "Travel": [
        "flight", "hotel", "makemytrip", "goibibo", "airbnb", "cleartrip", "indigo",
        "air india", "resort", "booking.com", "yatra",
    ],
    "Education": [
        "school", "college", "university", "course", "udemy", "coursera", "book",
        "tuition", "academy", "training",
    ],
    "Salary": [
        "salary", "payroll", "wage", "employer", "stipend",
    ],
    "Investment Returns": [
        "dividend", "interest", "zerodha", "groww", "mutual fund", "stocks", "crypto",
    ],
}


def _normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", text.strip().lower())


def _similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


class EntityMatcher:
    """Matches AI extracted entities (accounts, credit cards, categories, merchants) with user database records."""

    async def match_account(
        self,
        user_id: PydanticObjectId,
        extracted_name: Optional[str],
        extracted_ref: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> EntityMatch:
        accounts: List[Account] = await Account.find(Account.user_id == user_id).to_list()
        if not accounts:
            return EntityMatch(
                extracted_name=extracted_name,
                status="not_found",
                confidence=0.0,
            )

        # 1. Check last 4 digits if present in reference_id or extracted_name
        text_corpus = f"{extracted_name or ''} {extracted_ref or ''}"
        four_digit_matches = re.findall(r"\b\d{4}\b", text_corpus)

        scored_candidates: List[Tuple[Account, float]] = []

        for acc in accounts:
            score = 0.0
            # If last four digits match
            if acc.last_four and acc.last_four in four_digit_matches:
                score = max(score, 0.95)

            if extracted_name:
                norm_ext = _normalize(extracted_name)
                norm_name = _normalize(acc.name)
                norm_bank = _normalize(acc.bank_name)

                # Exact normalized matches
                if norm_ext == norm_name or norm_ext == norm_bank:
                    score = max(score, 0.95)
                elif norm_bank and (norm_bank in norm_ext or norm_ext in norm_bank):
                    score = max(score, 0.85)
                elif norm_name and (norm_name in norm_ext or norm_ext in norm_name):
                    score = max(score, 0.85)
                else:
                    # Fuzzy match
                    sim_name = _similarity(extracted_name, acc.name)
                    sim_bank = _similarity(extracted_name, acc.bank_name)
                    max_sim = max(sim_name, sim_bank)
                    if max_sim > 0.6:
                        score = max(score, max_sim * 0.8)

            if score > 0.5:
                scored_candidates.append((acc, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if not scored_candidates:
            # Fallback: if only 1 account exists and payment was via UPI or bank transfer
            if len(accounts) == 1 and payment_method in ["upi", "bank_transfer"]:
                return EntityMatch(
                    extracted_name=extracted_name,
                    matched_id=str(accounts[0].id),
                    matched_name=accounts[0].name,
                    confidence=0.6,
                    status="needs_confirmation",
                    possible_matches=[{"id": str(accounts[0].id), "name": accounts[0].name}],
                )

            return EntityMatch(
                extracted_name=extracted_name,
                status="not_found",
                confidence=0.0,
                possible_matches=[{"id": str(a.id), "name": a.name} for a in accounts],
            )

        top_acc, top_score = scored_candidates[0]

        # Check for ambiguity
        if len(scored_candidates) > 1:
            second_acc, second_score = scored_candidates[1]
            if top_score - second_score < 0.15 and top_score < 0.9:
                return EntityMatch(
                    extracted_name=extracted_name,
                    matched_id=str(top_acc.id),
                    matched_name=top_acc.name,
                    confidence=round(top_score, 2),
                    status="ambiguous",
                    possible_matches=[
                        {"id": str(a.id), "name": a.name, "score": round(s, 2)}
                        for a, s in scored_candidates[:5]
                    ],
                )

        status_label = "matched" if top_score >= 0.8 else "needs_confirmation"
        return EntityMatch(
            extracted_name=extracted_name,
            matched_id=str(top_acc.id),
            matched_name=top_acc.name,
            confidence=round(top_score, 2),
            status=status_label,
            possible_matches=[
                {"id": str(a.id), "name": a.name, "score": round(s, 2)}
                for a, s in scored_candidates[:5]
            ],
        )

    async def match_credit_card(
        self,
        user_id: PydanticObjectId,
        extracted_name: Optional[str],
        extracted_ref: Optional[str] = None,
    ) -> EntityMatch:
        cards: List[CreditCard] = await CreditCard.find(CreditCard.user_id == user_id).to_list()
        if not cards:
            return EntityMatch(
                extracted_name=extracted_name,
                status="not_found",
                confidence=0.0,
            )

        text_corpus = f"{extracted_name or ''} {extracted_ref or ''}"
        four_digit_matches = re.findall(r"\b\d{4}\b", text_corpus)

        scored_candidates: List[Tuple[CreditCard, float]] = []

        for card in cards:
            score = 0.0
            if card.last_four and card.last_four in four_digit_matches:
                score = max(score, 0.95)

            if extracted_name:
                norm_ext = _normalize(extracted_name)
                norm_name = _normalize(card.card_name)
                norm_prov = _normalize(card.provider)

                if norm_ext == norm_name or norm_ext == norm_prov:
                    score = max(score, 0.95)
                elif norm_prov and (norm_prov in norm_ext or norm_ext in norm_prov):
                    score = max(score, 0.85)
                elif norm_name and (norm_name in norm_ext or norm_ext in norm_name):
                    score = max(score, 0.85)
                else:
                    sim_name = _similarity(extracted_name, card.card_name)
                    sim_prov = _similarity(extracted_name, card.provider)
                    max_sim = max(sim_name, sim_prov)
                    if max_sim > 0.6:
                        score = max(score, max_sim * 0.8)

            if score > 0.5:
                scored_candidates.append((card, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if not scored_candidates:
            return EntityMatch(
                extracted_name=extracted_name,
                status="not_found",
                confidence=0.0,
                possible_matches=[{"id": str(c.id), "name": c.card_name} for c in cards],
            )

        top_card, top_score = scored_candidates[0]

        if len(scored_candidates) > 1:
            second_card, second_score = scored_candidates[1]
            if top_score - second_score < 0.15 and top_score < 0.9:
                return EntityMatch(
                    extracted_name=extracted_name,
                    matched_id=str(top_card.id),
                    matched_name=top_card.card_name,
                    confidence=round(top_score, 2),
                    status="ambiguous",
                    possible_matches=[
                        {"id": str(c.id), "name": c.card_name, "score": round(s, 2)}
                        for c, s in scored_candidates[:5]
                    ],
                )

        status_label = "matched" if top_score >= 0.8 else "needs_confirmation"
        return EntityMatch(
            extracted_name=extracted_name,
            matched_id=str(top_card.id),
            matched_name=top_card.card_name,
            confidence=round(top_score, 2),
            status=status_label,
            possible_matches=[
                {"id": str(c.id), "name": c.card_name, "score": round(s, 2)}
                for c, s in scored_candidates[:5]
            ],
        )

    async def match_category(
        self,
        user_id: PydanticObjectId,
        extracted_category: Optional[str],
        merchant_name: Optional[str] = None,
        line_items_text: Optional[str] = None,
        trans_type: TransactionType = TransactionType.EXPENSE,
    ) -> EntityMatch:
        categories: List[Category] = await Category.find(
            {
                "$and": [
                    {"$or": [{"user_id": user_id}, {"is_system": True}]},
                    {"type": trans_type.value},
                ]
            }
        ).to_list()

        if not categories:
            # Fallback to any category
            categories = await Category.find(
                {"$or": [{"user_id": user_id}, {"is_system": True}]}
            ).to_list()

        if not categories:
            return EntityMatch(
                extracted_name=extracted_category,
                status="not_found",
                confidence=0.0,
            )

        scored_candidates: List[Tuple[Category, float]] = []

        context_text = f"{merchant_name or ''} {line_items_text or ''}".lower()

        for cat in categories:
            score = 0.0

            # 1. Exact or close name match with extracted category
            if extracted_category:
                if _normalize(cat.name) == _normalize(extracted_category):
                    score = max(score, 0.98)
                elif _normalize(extracted_category) in _normalize(cat.name) or _normalize(cat.name) in _normalize(extracted_category):
                    score = max(score, 0.85)
                else:
                    sim = _similarity(extracted_category, cat.name)
                    if sim > 0.6:
                        score = max(score, sim * 0.8)

            # 2. Match based on keyword rules from merchant/items context
            keywords = CATEGORY_KEYWORD_RULES.get(cat.name, [])
            for kw in keywords:
                if kw in context_text:
                    score = max(score, 0.82)
                    break

            if score > 0.4:
                scored_candidates.append((cat, score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        if not scored_candidates:
            # Pick default category if available (e.g. "Other Expense" or "Other Income")
            fallback_cat = next(
                (c for c in categories if "other" in c.name.lower()),
                categories[0] if categories else None,
            )
            if fallback_cat:
                return EntityMatch(
                    extracted_name=extracted_category,
                    matched_id=str(fallback_cat.id),
                    matched_name=fallback_cat.name,
                    confidence=0.4,
                    status="needs_confirmation",
                    possible_matches=[{"id": str(c.id), "name": c.name} for c in categories[:8]],
                )

            return EntityMatch(
                extracted_name=extracted_category,
                status="not_found",
                confidence=0.0,
            )

        top_cat, top_score = scored_candidates[0]

        if len(scored_candidates) > 1:
            second_cat, second_score = scored_candidates[1]
            if top_score - second_score < 0.1 and top_score < 0.9:
                return EntityMatch(
                    extracted_name=extracted_category,
                    matched_id=str(top_cat.id),
                    matched_name=top_cat.name,
                    confidence=round(top_score, 2),
                    status="ambiguous",
                    possible_matches=[
                        {"id": str(c.id), "name": c.name, "score": round(s, 2)}
                        for c, s in scored_candidates[:5]
                    ],
                )

        status_label = "matched" if top_score >= 0.8 else "needs_confirmation"
        return EntityMatch(
            extracted_name=extracted_category,
            matched_id=str(top_cat.id),
            matched_name=top_cat.name,
            confidence=round(top_score, 2),
            status=status_label,
            possible_matches=[
                {"id": str(c.id), "name": c.name, "score": round(s, 2)}
                for c, s in scored_candidates[:5]
            ],
        )

    async def match_merchant(
        self,
        user_id: PydanticObjectId,
        extracted_merchant: Optional[str],
    ) -> EntityMatch:
        if not extracted_merchant:
            return EntityMatch(status="not_found", confidence=0.0)

        # Look up recent user transactions to see if this merchant has appeared
        recent_txs = await Transaction.find(Transaction.user_id == user_id).limit(100).to_list()
        
        known_titles = {tx.title for tx in recent_txs if tx.title}
        scored: List[Tuple[str, float]] = []

        for title in known_titles:
            if _normalize(title) == _normalize(extracted_merchant):
                scored.append((title, 0.95))
            else:
                sim = _similarity(extracted_merchant, title)
                if sim > 0.7:
                    scored.append((title, sim * 0.85))

        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored:
            return EntityMatch(
                extracted_name=extracted_merchant,
                matched_name=extracted_merchant,
                confidence=0.5,
                status="needs_confirmation",
            )

        top_name, top_score = scored[0]
        return EntityMatch(
            extracted_name=extracted_merchant,
            matched_name=top_name,
            confidence=round(top_score, 2),
            status="matched" if top_score >= 0.8 else "needs_confirmation",
            possible_matches=[{"name": name, "score": round(s, 2)} for name, s in scored[:5]],
        )


entity_matcher = EntityMatcher()
