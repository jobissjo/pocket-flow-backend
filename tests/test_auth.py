import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration_flow(client: AsyncClient):
    # 1. Register User
    payload = {
        "email": "john.doe@example.com",
        "mobile": "9998887776",
        "full_name": "John Doe",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert data["user"]["email"] == "john.doe@example.com"
    assert data["user"]["is_active"] is False
    otp = data.get("otp_preview")
    assert otp is not None

    # 2. Duplicate registration should fail
    dup_resp = await client.post("/api/auth/register", json=payload)
    assert dup_resp.status_code == 400
    assert "already exists" in dup_resp.json()["detail"]

    # 3. Login before verification should fail
    login_fail = await client.post(
        "/api/auth/login",
        json={"email": "john.doe@example.com", "password": "SecurePassword123!"},
    )
    assert login_fail.status_code == 400
    assert "not activated" in login_fail.json()["detail"]

    # 4. Verify OTP with invalid code
    bad_otp_resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "john.doe@example.com", "otp": "000000"},
    )
    assert bad_otp_resp.status_code == 400

    # 5. Verify OTP with correct code
    verify_resp = await client.post(
        "/api/auth/verify-otp",
        json={"email": "john.doe@example.com", "otp": otp},
    )
    assert verify_resp.status_code == 200
    token_data = verify_resp.json()
    assert "access_token" in token_data

    # 6. Login after activation
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "john.doe@example.com", "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # 7. Get current user via /api/auth/me
    token = login_resp.json()["access_token"]
    me_resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "john.doe@example.com"


@pytest.mark.asyncio
async def test_resend_otp_and_forgot_password(client: AsyncClient):
    # Register user
    await client.post(
        "/api/auth/register",
        json={
            "email": "reset@example.com",
            "full_name": "Reset User",
            "password": "InitialPassword123!",
        },
    )

    # Resend OTP
    resend_resp = await client.post(
        "/api/auth/resend-otp", json={"email": "reset@example.com"}
    )
    assert resend_resp.status_code == 200
    new_otp = resend_resp.json().get("otp_preview")
    assert new_otp is not None

    # Verify and activate
    await client.post(
        "/api/auth/verify-otp",
        json={"email": "reset@example.com", "otp": new_otp},
    )

    # Forgot password request
    forgot_resp = await client.post(
        "/api/auth/forgot-password", json={"email": "reset@example.com"}
    )
    assert forgot_resp.status_code == 200
    reset_otp = forgot_resp.json().get("otp_preview")

    # Reset password
    reset_resp = await client.post(
        "/api/auth/reset-password",
        json={
            "email": "reset@example.com",
            "otp": reset_otp,
            "new_password": "NewSecretPassword456!",
        },
    )
    assert reset_resp.status_code == 200

    # Login with new password
    login_new = await client.post(
        "/api/auth/login",
        json={
            "email": "reset@example.com",
            "password": "NewSecretPassword456!",
        },
    )
    assert login_new.status_code == 200
