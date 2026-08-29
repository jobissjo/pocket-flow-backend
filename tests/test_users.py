import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_profile_endpoints(client: AsyncClient, auth_headers: dict):
    # 1. Get profile
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    user_data = resp.json()
    assert user_data["email"] == "testuser@example.com"
    assert user_data["full_name"] == "Test User"

    # 2. Update profile
    update_resp = await client.patch(
        "/api/users/me",
        headers=auth_headers,
        json={"full_name": "Updated Test User", "mobile": "9123456780"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["full_name"] == "Updated Test User"
    assert update_resp.json()["mobile"] == "9123456780"

    # 3. Delete profile
    del_resp = await client.delete("/api/users/me", headers=auth_headers)
    assert del_resp.status_code == 200

    # 4. Token should no longer work
    fail_resp = await client.get("/api/users/me", headers=auth_headers)
    assert fail_resp.status_code == 401
