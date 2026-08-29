import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_emi_lifecycle_and_mark_paid(
    client: AsyncClient, auth_headers: dict
):
    # 1. Create account for EMI deduction
    acc_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "EMI Bank Account",
            "bank_name": "Axis Bank",
            "account_type": "savings",
            "account_number": "555566667777",
            "balance": 20000.0,
        },
    )
    assert acc_resp.status_code == 201
    account_id = acc_resp.json()["id"]

    # 2. Create EMI (3 installments, 1 paid initially)
    create_resp = await client.post(
        "/api/emi",
        headers=auth_headers,
        json={
            "name": "MacBook Pro EMI",
            "total_amount": 60000.0,
            "monthly_emi_amount": 20000.0,
            "total_installments": 3,
            "paid_installments": 1,
            "start_date": "2026-01-01T00:00:00Z",
            "due_day": 10,
            "account_id": account_id,
        },
    )
    assert create_resp.status_code == 201
    emi_data = create_resp.json()
    assert emi_data["name"] == "MacBook Pro EMI"
    assert emi_data["remaining_installments"] == 2
    assert emi_data["status"] in ["active", "overdue"]
    assert emi_data["next_payment_date"] is not None
    emi_id = emi_data["id"]

    # 3. List EMIs
    list_resp = await client.get("/api/emi", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 4. Mark 2nd installment as paid
    pay1_resp = await client.post(
        f"/api/emi/{emi_id}/mark-paid", headers=auth_headers
    )
    assert pay1_resp.status_code == 200
    pay1_data = pay1_resp.json()["emi"]
    assert pay1_data["paid_installments"] == 2
    assert pay1_data["remaining_installments"] == 1
    assert pay1_data["status"] in ["active", "overdue"]

    # Account balance should have deducted 20,000 -> balance becomes 0
    acc_check = await client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert acc_check.json()["balance"] == 0.0

    # 5. Mark final installment (3rd) as paid
    pay2_resp = await client.post(
        f"/api/emi/{emi_id}/mark-paid", headers=auth_headers
    )
    assert pay2_resp.status_code == 200
    pay2_data = pay2_resp.json()["emi"]
    assert pay2_data["paid_installments"] == 3
    assert pay2_data["remaining_installments"] == 0
    assert pay2_data["status"] == "completed"
    assert pay2_data["next_payment_date"] is None

    # 6. Attempting to mark paid again when already completed should fail
    fail_pay = await client.post(
        f"/api/emi/{emi_id}/mark-paid", headers=auth_headers
    )
    assert fail_pay.status_code == 400

    # 7. Delete EMI
    del_resp = await client.delete(f"/api/emi/{emi_id}", headers=auth_headers)
    assert del_resp.status_code == 200
