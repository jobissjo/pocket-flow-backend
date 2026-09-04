import pytest
from unittest.mock import patch
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_google_login_new_user(client: AsyncClient):
    """Test that a new user signing in with Google gets an active account and access token."""
    mock_id_info = {
        "sub": "google-uid-12345",
        "email": "googleuser@example.com",
        "name": "Google User",
        "picture": "https://lh3.googleusercontent.com/a/photo.jpg",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        resp = await client.post(
            "/api/auth/google",
            json={"credential": "mock-valid-google-jwt-token"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # Verify user was created in database
    user = await User.find_one(User.email == "googleuser@example.com")
    assert user is not None
    assert user.full_name == "Google User"
    assert user.google_id == "google-uid-12345"
    assert user.avatar_url == "https://lh3.googleusercontent.com/a/photo.jpg"
    assert user.is_active is True
    assert user.auth_provider == "google"
    assert user.hashed_password is None


@pytest.mark.asyncio
async def test_google_login_existing_user_linking(client: AsyncClient):
    """Test that an existing registered user signing in with Google has their account linked and activated."""
    # Create existing unactivated user (pending OTP)
    existing_user = User(
        email="existing@example.com",
        full_name="Existing User",
        hashed_password="some-hashed-password",
        is_active=False,
        otp="123456",
    )
    await existing_user.create()

    mock_id_info = {
        "sub": "google-uid-67890",
        "email": "existing@example.com",
        "name": "Existing User From Google",
        "picture": "https://lh3.googleusercontent.com/a/avatar.jpg",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        resp = await client.post(
            "/api/auth/google",
            json={"credential": "mock-google-credential-token"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data

    # Verify existing user is now activated and linked
    updated = await User.find_one(User.email == "existing@example.com")
    assert updated is not None
    assert updated.google_id == "google-uid-67890"
    assert updated.is_active is True
    assert updated.otp is None
    assert updated.avatar_url == "https://lh3.googleusercontent.com/a/avatar.jpg"


@pytest.mark.asyncio
async def test_google_login_invalid_credential(client: AsyncClient):
    """Test that invalid Google token returns 400 Bad Request."""
    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Token expired")):
        resp = await client.post(
            "/api/auth/google",
            json={"credential": "expired-or-malformed-token"},
        )

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Invalid Google credential token" in detail


@pytest.mark.asyncio
async def test_google_login_token_without_email(client: AsyncClient):
    """Test that Google token missing an email returns 400 Bad Request."""
    mock_id_info = {
        "sub": "google-uid-99999",
        "name": "No Email User",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        resp = await client.post(
            "/api/auth/google",
            json={"credential": "mock-token-no-email"},
        )

    assert resp.status_code == 400
    assert "did not contain a valid email address" in resp.json()["detail"]
