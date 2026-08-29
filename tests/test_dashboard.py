import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_summary_and_analytics(
    client: AsyncClient, auth_headers: dict
):
    # 1. Setup account
    acc_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "Dashboard Checking",
            "bank_name": "Test Bank",
            "account_type": "savings",
            "account_number": "12345678",
            "balance": 25000.0,
        },
    )
    acc_id = acc_resp.json()["id"]

    # 2. Setup credit card
    card_resp = await client.post(
        "/api/credit-cards",
        headers=auth_headers,
        json={
            "card_name": "Rewards Card",
            "provider": "Visa",
            "last_four": "1111",
            "credit_limit": 50000.0,
            "outstanding_amount": 5000.0,
            "billing_date": 1,
            "payment_due_date": 20,
        },
    )

    # 3. Fetch category IDs
    cats_resp = await client.get("/api/categories", headers=auth_headers)
    cats = cats_resp.json()
    salary_cat = next(c["id"] for c in cats if c["name"] == "Salary")
    food_cat = next(c["id"] for c in cats if c["name"] == "Food & Dining")

    # 4. Add income and expense transactions
    await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Monthly Paycheck",
            "amount": 10000.0,
            "type": "income",
            "category_id": salary_cat,
            "account_id": acc_id,
        },
    )

    await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Grocery Shopping",
            "amount": 2500.0,
            "type": "expense",
            "category_id": food_cat,
            "account_id": acc_id,
        },
    )

    # 5. Add EMI
    await client.post(
        "/api/emi",
        headers=auth_headers,
        json={
            "name": "Car Loan",
            "total_amount": 120000.0,
            "monthly_emi_amount": 10000.0,
            "total_installments": 12,
            "paid_installments": 2,
            "start_date": "2026-01-01T00:00:00Z",
            "due_day": 15,
            "account_id": acc_id,
        },
    )

    # 6. Test GET /api/dashboard/summary
    summary_resp = await client.get("/api/dashboard/summary", headers=auth_headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_income"] == 10000.0
    assert summary["total_expenses"] == 2500.0
    assert summary["net_savings"] == 7500.0
    assert summary["savings_percentage"] == 75.0
    assert summary["total_credit_card_outstanding"] == 5000.0

    # 7. Test GET /api/dashboard/analytics
    analytics_resp = await client.get(
        "/api/dashboard/analytics", headers=auth_headers
    )
    assert analytics_resp.status_code == 200
    analytics = analytics_resp.json()
    assert "income_vs_expense" in analytics
    assert "expense_breakdown" in analytics
    assert "income_breakdown" in analytics
    assert len(analytics["expense_breakdown"]) == 1
    assert analytics["expense_breakdown"][0]["category_name"] == "Food & Dining"
    assert analytics["expense_breakdown"][0]["percentage"] == 100.0

    # 8. Test GET /api/dashboard/recent-transactions
    recent_resp = await client.get(
        "/api/dashboard/recent-transactions", headers=auth_headers
    )
    assert recent_resp.status_code == 200
    assert len(recent_resp.json()) == 2

    # 9. Test GET /api/dashboard/upcoming-emi
    upcoming_resp = await client.get(
        "/api/dashboard/upcoming-emi", headers=auth_headers
    )
    assert upcoming_resp.status_code == 200
    assert len(upcoming_resp.json()) == 1
    assert upcoming_resp.json()[0]["name"] == "Car Loan"
