import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_account_lifecycle_and_isolation(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    # 1. Create account
    create_resp = await client.post(
        "/api/accounts",
        headers=auth_headers,
        json={
            "name": "HDFC Primary Savings",
            "bank_name": "HDFC Bank",
            "account_type": "savings",
            "account_number": "987654321098",
            "balance": 15000.0,
        },
    )
    assert create_resp.status_code == 201
    acc_data = create_resp.json()
    assert acc_data["name"] == "HDFC Primary Savings"
    assert acc_data["last_four"] == "1098"
    assert "account_number" not in acc_data  # Account number should be masked / not exposed
    account_id = acc_data["id"]

    # 2. List accounts
    list_resp = await client.get("/api/accounts", headers=auth_headers)
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert len(accounts) == 1
    assert accounts[0]["id"] == account_id

    # 3. Cross-user isolation: second user should not see first user's account
    second_list = await client.get("/api/accounts", headers=second_auth_headers)
    assert second_list.status_code == 200
    assert len(second_list.json()) == 0

    second_get = await client.get(
        f"/api/accounts/{account_id}", headers=second_auth_headers
    )
    assert second_get.status_code == 404

    # 4. Update account
    update_resp = await client.patch(
        f"/api/accounts/{account_id}",
        headers=auth_headers,
        json={"name": "HDFC Salary Account", "balance": 20000.0},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "HDFC Salary Account"
    assert update_resp.json()["balance"] == 20000.0

    # 5. Delete account
    del_resp = await client.delete(
        f"/api/accounts/{account_id}", headers=auth_headers
    )
    assert del_resp.status_code == 200

    # 6. Verify deleted
    get_del = await client.get(f"/api/accounts/{account_id}", headers=auth_headers)
    assert get_del.status_code == 404
