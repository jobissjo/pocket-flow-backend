import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_transaction_lifecycle_and_balance_tracking(
    client: AsyncClient, auth_headers: dict
):
    # 1. Create a bank account with initial balance 50,000
    acc_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "Main Checking",
            "bank_name": "Chase",
            "account_type": "savings",
            "account_number": "111122223333",
            "balance": 50000.0,
        },
    )
    assert acc_resp.status_code == 201
    account_id = acc_resp.json()["id"]

    # 2. Create a credit card with outstanding 0
    card_resp = await client.post(
        "/api/credit-cards",
        headers=auth_headers,
        json={
            "card_name": "Sapphire Reserve",
            "provider": "Chase",
            "last_four": "9999",
            "credit_limit": 100000.0,
            "outstanding_amount": 0.0,
            "billing_date": 20,
            "payment_due_date": 10,
        },
    )
    assert card_resp.status_code == 201
    card_id = card_resp.json()["id"]

    # 3. Get category ID for Food & Dining and Salary
    cats_resp = await client.get("/api/categories", headers=auth_headers)
    cats = cats_resp.json()
    food_cat_id = next(c["id"] for c in cats if c["name"] == "Food & Dining")
    salary_cat_id = next(c["id"] for c in cats if c["name"] == "Salary")

    # 4. Create an Expense on Bank Account -> 2,000
    tx_exp_acc = await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Dinner with friends",
            "amount": 2000.0,
            "type": "expense",
            "category_id": food_cat_id,
            "account_id": account_id,
        },
    )
    assert tx_exp_acc.status_code == 201
    tx_exp_id = tx_exp_acc.json()["id"]
    assert tx_exp_acc.json()["account_name"] == "Main Checking"

    # Check that bank account balance decreased to 48,000
    acc_check = await client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert acc_check.json()["balance"] == 48000.0

    # 5. Create an Income on Bank Account -> 10,000
    tx_inc = await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Monthly Salary",
            "amount": 10000.0,
            "type": "income",
            "category_id": salary_cat_id,
            "account_id": account_id,
        },
    )
    assert tx_inc.status_code == 201

    # Check bank account balance increased to 58,000
    acc_check2 = await client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert acc_check2.json()["balance"] == 58000.0

    # 6. Create an Expense on Credit Card -> 5,000
    tx_card_exp = await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Online Electronics Order",
            "amount": 5000.0,
            "type": "expense",
            "category_id": food_cat_id,
            "credit_card_id": card_id,
        },
    )
    assert tx_card_exp.status_code == 201

    # Check credit card outstanding increased to 5,000
    card_check = await client.get(f"/api/credit-cards/{card_id}", headers=auth_headers)
    assert card_check.json()["outstanding_amount"] == 5000.0
    assert card_check.json()["available_limit"] == 95000.0

    # 7. Invalid transaction: Income on credit card (should fail validation)
    invalid_tx = await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Invalid Income",
            "amount": 1000.0,
            "type": "income",
            "category_id": salary_cat_id,
            "credit_card_id": card_id,
        },
    )
    assert invalid_tx.status_code == 422

    # 8. List transactions with pagination and filters
    tx_list = await client.get(
        "/api/transactions?type=expense&limit=10", headers=auth_headers
    )
    assert tx_list.status_code == 200
    paginated = tx_list.json()
    assert paginated["total"] == 2
    assert len(paginated["items"]) == 2

    # 9. Update transaction: change amount from 2000 to 3000
    up_tx = await client.patch(
        f"/api/transactions/{tx_exp_id}",
        headers=auth_headers,
        json={"amount": 3000.0},
    )
    assert up_tx.status_code == 200
    # Bank balance should now be 57,000 (was 58,000 before update, now extra 1,000 deducted)
    acc_check3 = await client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert acc_check3.json()["balance"] == 57000.0

    # 10. Delete transaction: deleting the 3000 expense should restore balance to 60,000
    del_tx = await client.delete(
        f"/api/transactions/{tx_exp_id}", headers=auth_headers
    )
    assert del_tx.status_code == 200
    acc_check4 = await client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert acc_check4.json()["balance"] == 60000.0
