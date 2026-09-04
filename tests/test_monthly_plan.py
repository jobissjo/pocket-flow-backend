import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_monthly_plan_lifecycle_and_shortfall(
    client: AsyncClient, auth_headers: dict
):
    year = 2026
    month = 9

    # 1. GET initial empty plan
    resp = await client.get(
        f"/api/monthly-planner?year={year}&month={month}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == year
    assert data["month"] == month
    assert data["planned_income"] == 0.0
    assert len(data["category_budgets"]) == 0

    # 2. Get category IDs
    cats_resp = await client.get("/api/categories", headers=auth_headers)
    cats = cats_resp.json()
    salary_cat = next(c["id"] for c in cats if c["name"] == "Salary")
    groceries_cat = next(c["id"] for c in cats if c["name"] == "Groceries")
    dining_cat = next(c["id"] for c in cats if c["name"] == "Food & Dining")

    # 3. Create plan where planned expenses EXCEED planned income (Deficit / Income Shortfall scenario)
    # Income: 50,000 (Salary: 50,000)
    # Groceries: 15,000, Dining: 10,000, Custom Item (Vacation): 35,000 => Total Expenses: 60,000
    # Shortfall: 10,000!
    save_payload = {
        "planned_income": 50000.0,
        "income_sources": [
            {"title": "Day Job Salary", "amount": 50000.0, "is_received": False}
        ],
        "category_budgets": [
            {"category_id": groceries_cat, "planned_amount": 15000.0, "notes": "Monthly food"},
            {"category_id": dining_cat, "planned_amount": 10000.0, "notes": "Weekends"},
        ],
        "custom_items": [
            {"title": "Vacation Booking", "planned_amount": 35000.0, "is_completed": False}
        ],
        "review_notes": "Planning to do freelance work to cover the 10k deficit.",
    }

    put_resp = await client.put(
        f"/api/monthly-planner?year={year}&month={month}",
        headers=auth_headers,
        json=save_payload,
    )
    assert put_resp.status_code == 200
    saved = put_resp.json()
    assert saved["planned_income"] == 50000.0
    assert saved["total_planned_expenses"] == 60000.0
    assert saved["funding_status"] == "deficit"
    assert saved["income_shortfall"] == 10000.0
    assert saved["net_planned_buffer"] == -10000.0
    assert len(saved["category_budgets"]) == 2
    assert len(saved["custom_items"]) == 1

    # 4. Setup Bank Account and record transactions in Sep 2026
    acc_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "Checking Account",
            "bank_name": "Axis Bank",
            "account_type": "savings",
            "account_number": "9999",
            "balance": 100000.0,
        },
    )
    acc_id = acc_resp.json()["id"]

    # Salary Income: 50,000
    await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "September Salary",
            "amount": 50000.0,
            "type": "income",
            "category_id": salary_cat,
            "account_id": acc_id,
            "date": "2026-09-01T10:00:00Z",
        },
    )

    # Groceries: Spent 12,000 (Under budget! Planned was 15,000 => Saved 3,000)
    await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Supermarket Supplies",
            "amount": 12000.0,
            "type": "expense",
            "category_id": groceries_cat,
            "account_id": acc_id,
            "date": "2026-09-10T12:00:00Z",
        },
    )

    # Dining: Spent 14,000 (Over budget! Planned was 10,000 => Overspent 4,000)
    await client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "title": "Luxury Dining and Parties",
            "amount": 14000.0,
            "type": "expense",
            "category_id": dining_cat,
            "account_id": acc_id,
            "date": "2026-09-15T20:00:00Z",
        },
    )

    # 5. GET Comparison & Month-End Review
    comp_resp = await client.get(
        f"/api/monthly-planner/comparison?year={year}&month={month}",
        headers=auth_headers,
    )
    assert comp_resp.status_code == 200
    comp = comp_resp.json()
    assert comp["planned_income"] == 50000.0
    assert comp["actual_income"] == 50000.0
    assert comp["planned_expenses"] == 60000.0
    assert comp["actual_expenses"] == 26000.0
    assert comp["funding_status"] == "deficit"
    assert comp["income_shortfall"] == 10000.0

    # Category comparisons check
    groceries_comp = next(c for c in comp["category_comparisons"] if c["category_id"] == groceries_cat)
    assert groceries_comp["planned_amount"] == 15000.0
    assert groceries_comp["actual_amount"] == 12000.0
    assert groceries_comp["variance"] == 3000.0
    assert groceries_comp["status"] == "under_budget"

    dining_comp = next(c for c in comp["category_comparisons"] if c["category_id"] == dining_cat)
    assert dining_comp["planned_amount"] == 10000.0
    assert dining_comp["actual_amount"] == 14000.0
    assert dining_comp["variance"] == -4000.0
    assert dining_comp["status"] == "over_budget"

    # Automated what_went_well & what_went_wrong check
    assert any("Under Budget on Groceries" in msg for msg in comp["what_went_well"])
    assert any("Overspent on Food & Dining" in msg for msg in comp["what_went_wrong"])

    # 6. Test Copy to October 2026
    copy_resp = await client.post(
        "/api/monthly-planner/copy-previous",
        headers=auth_headers,
        json={
            "target_year": 2026,
            "target_month": 10,
            "source_year": 2026,
            "source_month": 9,
        },
    )
    assert copy_resp.status_code == 200
    oct_plan = copy_resp.json()
    assert oct_plan["year"] == 2026
    assert oct_plan["month"] == 10
    assert oct_plan["planned_income"] == 50000.0
    assert len(oct_plan["category_budgets"]) == 2
