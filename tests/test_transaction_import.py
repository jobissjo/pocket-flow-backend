import io
import pytest
from httpx import AsyncClient

from app.models.account import Account, AccountType
from app.models.category import Category, CategoryType
from app.models.credit_card import CreditCard
from app.models.transaction import Transaction, TransactionType
from app.models.transaction_import import TransactionImport, TransactionImportStatus
from app.transaction_import.extractor import (
    BaseTransactionImageExtractor,
    set_extractor,
)
from app.transaction_import.schemas import (
    ExtractedLineItem,
    ExtractedTransaction,
)

# 1x1 valid transparent PNG bytes
TINY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


class MockExtractor(BaseTransactionImageExtractor):
    """Configurable mock extractor for testing."""

    def __init__(self, response: ExtractedTransaction):
        self.response = response

    async def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedTransaction:
        return self.response


@pytest.mark.asyncio
async def test_upload_receipt_and_draft_generation(client: AsyncClient, auth_headers: dict):
    # 1. Setup user account
    acc_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "HDFC Salary Account",
            "bank_name": "HDFC Bank",
            "account_type": "savings",
            "account_number": "123456789012",
            "last_four": "9012",
            "balance": 10000.0,
        },
    )
    assert acc_resp.status_code == 201
    account_id = acc_resp.json()["id"]

    # 2. Mock AI extractor with a restaurant receipt
    mock_extracted = ExtractedTransaction(
        transaction_type="expense",
        amount=450.0,
        currency="INR",
        merchant_name="Starbucks Coffee",
        account_name="HDFC Bank",
        category_name="Food & Dining",
        transaction_date="2026-08-15",
        transaction_time="14:30:00",
        payment_method="upi",
        reference_id="UPI987654321",
        description="Coffee with colleagues",
        subtotal=400.0,
        tax=50.0,
        discount=0.0,
        source_type="receipt",
        items=[
            ExtractedLineItem(name="Caffe Latte", quantity=1, unit_price=250.0, amount=250.0),
            ExtractedLineItem(name="Blueberry Muffin", quantity=1, unit_price=150.0, amount=150.0),
        ],
        confidence=0.95,
    )
    set_extractor(MockExtractor(mock_extracted))

    # 3. Upload image
    files = {"file": ("receipt.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    response = await client.post("/api/transaction-imports/image", headers=auth_headers, files=files)
    assert response.status_code == 201
    data = response.json()

    import_id = data["id"]
    assert data["status"] == "review"
    assert data["source_type"] == "receipt"
    draft = data["draft"]
    assert draft["title"] == "Starbucks Coffee"
    assert draft["amount"] == 450.0
    assert draft["transaction_type"] == "expense"
    assert len(draft["items"]) == 2
    assert draft["items"][0]["name"] == "Caffe Latte"

    # Category matching check
    assert draft["category"] is not None
    assert draft["category"]["status"] == "matched"
    assert draft["category"]["matched_name"] == "Food & Dining"

    # Account matching check
    assert draft["account"] is not None
    assert draft["account"]["matched_id"] == account_id
    assert draft["account"]["matched_name"] == "HDFC Salary Account"


@pytest.mark.asyncio
async def test_confirm_transaction_import_creates_transaction(client: AsyncClient, auth_headers: dict):
    # 1. Setup account
    acc_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "SBI Savings",
            "bank_name": "State Bank of India",
            "account_type": "savings",
            "account_number": "987654321098",
            "last_four": "1098",
            "balance": 5000.0,
        },
    )
    assert acc_resp.status_code == 201
    account_id = acc_resp.json()["id"]

    # 2. Get category ID for Groceries
    cats_resp = await client.get("/api/categories", headers=auth_headers)
    groceries_cat = next(c for c in cats_resp.json() if c["name"] == "Groceries")

    # 3. Mock extraction
    mock_extracted = ExtractedTransaction(
        transaction_type="expense",
        amount=1200.0,
        currency="INR",
        merchant_name="Reliance Fresh",
        account_name="SBI",
        category_name="Groceries",
        transaction_date="2026-08-20",
        payment_method="upi",
        source_type="receipt",
        confidence=0.9,
    )
    set_extractor(MockExtractor(mock_extracted))

    # 4. Upload
    files = {"file": ("grocery.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    upload_resp = await client.post("/api/transaction-imports/image", headers=auth_headers, files=files)
    assert upload_resp.status_code == 201
    import_id = upload_resp.json()["id"]

    # 5. Confirm draft with user edits
    confirm_resp = await client.post(
        f"/api/transaction-imports/{import_id}/confirm",
        headers=auth_headers,
        json={
            "title": "Reliance Fresh Weekly Groceries",
            "amount": 1200.0,
            "type": "expense",
            "category_id": groceries_cat["id"],
            "account_id": account_id,
            "date": "2026-08-20T10:00:00Z",
            "notes": "Vegetables and fruits",
        },
    )
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data["status"] == "confirmed"
    assert confirm_data["created_transaction_id"] is not None

    # Verify real transaction was created
    tx_id = confirm_data["created_transaction_id"]
    tx_resp = await client.get(f"/api/transactions/{tx_id}", headers=auth_headers)
    assert tx_resp.status_code == 200
    tx_data = tx_resp.json()
    assert tx_data["title"] == "Reliance Fresh Weekly Groceries"
    assert tx_data["amount"] == 1200.0

    # Verify account balance was deducted (5000 - 1200 = 3800)
    acc_check = await client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert acc_check.json()["balance"] == 3800.0

    # Verify duplicate confirmation is rejected
    second_confirm = await client.post(
        f"/api/transaction-imports/{import_id}/confirm",
        headers=auth_headers,
        json={
            "title": "Reliance Fresh Weekly Groceries",
            "amount": 1200.0,
            "type": "expense",
            "category_id": groceries_cat["id"],
            "account_id": account_id,
        },
    )
    assert second_confirm.status_code == 400


@pytest.mark.asyncio
async def test_reject_transaction_import(client: AsyncClient, auth_headers: dict):
    mock_extracted = ExtractedTransaction(
        transaction_type="expense",
        amount=100.0,
        merchant_name="Unknown Store",
        source_type="receipt",
        confidence=0.5,
    )
    set_extractor(MockExtractor(mock_extracted))

    files = {"file": ("unknown.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    upload_resp = await client.post("/api/transaction-imports/image", headers=auth_headers, files=files)
    assert upload_resp.status_code == 201
    import_id = upload_resp.json()["id"]

    reject_resp = await client.post(f"/api/transaction-imports/{import_id}/reject", headers=auth_headers)
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_duplicate_detection(client: AsyncClient, auth_headers: dict):
    # 1. Setup account & category
    acc_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "Main Bank",
            "bank_name": "ICICI Bank",
            "account_type": "savings",
            "account_number": "112233445566",
            "last_four": "5566",
            "balance": 10000.0,
        },
    )
    acc_id = acc_resp.json()["id"]

    cats_resp = await client.get("/api/categories", headers=auth_headers)
    cat_id = cats_resp.json()[0]["id"]

    # 2. Create an existing transaction with reference ID in notes
    await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Swiggy Order",
            "amount": 350.0,
            "type": "expense",
            "category_id": cat_id,
            "account_id": acc_id,
            "notes": "Ref ID: UPI_SWIGGY_9988",
        },
    )

    # 3. Upload screenshot with matching reference ID
    mock_extracted = ExtractedTransaction(
        transaction_type="expense",
        amount=350.0,
        merchant_name="Swiggy",
        reference_id="UPI_SWIGGY_9988",
        payment_method="upi",
        source_type="payment_screenshot",
        confidence=0.95,
    )
    set_extractor(MockExtractor(mock_extracted))

    files = {"file": ("swiggy.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    resp = await client.post("/api/transaction-imports/image", headers=auth_headers, files=files)
    assert resp.status_code == 201
    draft = resp.json()["draft"]
    assert draft["is_duplicate"] is True
    assert any("Duplicate detected" in w for w in draft["warnings"])


@pytest.mark.asyncio
async def test_receipt_totals_math_mismatch_warning(client: AsyncClient, auth_headers: dict):
    mock_extracted = ExtractedTransaction(
        transaction_type="expense",
        amount=500.0,  # mismatch with subtotal 400 + tax 50 = 450
        subtotal=400.0,
        tax=50.0,
        discount=0.0,
        merchant_name="Cafe Delight",
        source_type="receipt",
        confidence=0.8,
    )
    set_extractor(MockExtractor(mock_extracted))

    files = {"file": ("cafe.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    resp = await client.post("/api/transaction-imports/image", headers=auth_headers, files=files)
    assert resp.status_code == 201
    draft = resp.json()["draft"]
    assert any("totals mismatch" in w.lower() for w in draft["warnings"])


@pytest.mark.asyncio
async def test_unsupported_image_handling(client: AsyncClient, auth_headers: dict):
    mock_extracted = ExtractedTransaction(
        source_type="unsupported",
        confidence=0.0,
        unsupported_reason="Bank statement containing multiple unrelated transactions.",
    )
    set_extractor(MockExtractor(mock_extracted))

    files = {"file": ("statement.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    resp = await client.post("/api/transaction-imports/image", headers=auth_headers, files=files)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "failed"
    assert "multiple unrelated transactions" in data["error_message"]


@pytest.mark.asyncio
async def test_user_isolation_security(client: AsyncClient, auth_headers: dict, second_auth_headers: dict):
    mock_extracted = ExtractedTransaction(
        transaction_type="expense",
        amount=250.0,
        merchant_name="User1 Store",
        source_type="receipt",
        confidence=0.8,
    )
    set_extractor(MockExtractor(mock_extracted))

    # User 1 uploads
    files = {"file": ("user1.png", io.BytesIO(TINY_PNG_BYTES), "image/png")}
    upload_resp = await client.post("/api/transaction-imports/image", headers=auth_headers, files=files)
    assert upload_resp.status_code == 201
    import_id = upload_resp.json()["id"]

    # User 2 tries to fetch User 1's import
    get_resp = await client.get(f"/api/transaction-imports/{import_id}", headers=second_auth_headers)
    assert get_resp.status_code == 404

    # User 2 tries to reject User 1's import
    rej_resp = await client.post(f"/api/transaction-imports/{import_id}/reject", headers=second_auth_headers)
    assert rej_resp.status_code == 404
