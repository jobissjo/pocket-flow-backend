import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_credit_card_lifecycle(client: AsyncClient, auth_headers: dict):
    # 1. Create Credit Card
    create_resp = await client.post(
        "/api/credit-cards",
        headers=auth_headers,
        json={
            "card_name": "Amazon Pay ICICI",
            "provider": "ICICI",
            "last_four": "4321",
            "credit_limit": 100000.0,
            "outstanding_amount": 12500.0,
            "billing_date": 15,
            "payment_due_date": 5,
        },
    )
    assert create_resp.status_code == 201
    card_data = create_resp.json()
    assert card_data["card_name"] == "Amazon Pay ICICI"
    assert card_data["available_limit"] == 87500.0
    card_id = card_data["id"]

    # 2. List Credit Cards
    list_resp = await client.get("/api/credit-cards", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 3. Get Credit Card
    get_resp = await client.get(f"/api/credit-cards/{card_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == card_id

    # 4. Update Credit Card
    up_resp = await client.patch(
        f"/api/credit-cards/{card_id}",
        headers=auth_headers,
        json={"credit_limit": 150000.0},
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["credit_limit"] == 150000.0
    assert up_resp.json()["available_limit"] == 137500.0

    # 5. Delete Credit Card
    del_resp = await client.delete(
        f"/api/credit-cards/{card_id}", headers=auth_headers
    )
    assert del_resp.status_code == 200
