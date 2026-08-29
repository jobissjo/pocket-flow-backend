import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_category_endpoints_and_system_protection(
    client: AsyncClient, auth_headers: dict
):
    # 1. List default system categories
    list_resp = await client.get("/api/categories", headers=auth_headers)
    assert list_resp.status_code == 200
    categories = list_resp.json()
    assert len(categories) > 0

    # Pick a system category
    system_cat = next(c for c in categories if c["is_system"] is True)
    system_id = system_cat["id"]

    # 2. Attempt to update system category -> should fail (403)
    mod_sys = await client.patch(
        f"/api/categories/{system_id}",
        headers=auth_headers,
        json={"name": "Hacked System Name"},
    )
    assert mod_sys.status_code == 403

    # 3. Attempt to delete system category -> should fail (403)
    del_sys = await client.delete(
        f"/api/categories/{system_id}", headers=auth_headers
    )
    assert del_sys.status_code == 403

    # 4. Create custom category
    custom_resp = await client.post(
        "/api/categories",
        headers=auth_headers,
        json={
            "name": "Side Hustle Tech",
            "type": "income",
            "icon": "code",
        },
    )
    assert custom_resp.status_code == 201
    custom_data = custom_resp.json()
    assert custom_data["is_system"] is False
    custom_id = custom_data["id"]

    # 5. Update custom category
    update_custom = await client.patch(
        f"/api/categories/{custom_id}",
        headers=auth_headers,
        json={"name": "SaaS Side Project"},
    )
    assert update_custom.status_code == 200
    assert update_custom.json()["name"] == "SaaS Side Project"

    # 6. Delete custom category
    del_custom = await client.delete(
        f"/api/categories/{custom_id}", headers=auth_headers
    )
    assert del_custom.status_code == 200
