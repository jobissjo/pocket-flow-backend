from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services.email import EmailService, email_service


@pytest.mark.asyncio
async def test_email_service_disabled():
    """When SMTP is disabled, send_email_async should return False without attempting connection."""
    with patch.object(settings, "SMTP_ENABLED", False):
        service = EmailService()
        result = await service.send_email_async(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<p>Test Content</p>",
        )
        assert result is False


@pytest.mark.asyncio
async def test_email_service_send_success():
    """When SMTP is enabled and valid, aiosmtplib.send should be called with correct arguments."""
    with patch.object(settings, "SMTP_ENABLED", True), \
         patch.object(settings, "SMTP_HOST", "smtp.example.com"), \
         patch.object(settings, "SMTP_PORT", 587), \
         patch.object(settings, "SMTP_USER", "mailer@example.com"), \
         patch.object(settings, "SMTP_PASSWORD", "secret123"), \
         patch.object(settings, "SMTP_TLS", True), \
         patch.object(settings, "SMTP_SSL", False), \
         patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:

        mock_send.return_value = ({}, "250 OK")
        service = EmailService()

        result = await service.send_registration_otp_email(
            to_email="newuser@example.com",
            full_name="New User",
            otp="123456",
        )

        assert result is True
        assert mock_send.call_count == 1
        args, kwargs = mock_send.call_args
        message = args[0]
        assert message["To"] == "newuser@example.com"
        assert "123456" in message["Subject"]
        assert kwargs["hostname"] == "smtp.example.com"
        assert kwargs["port"] == 587
        assert kwargs["username"] == "mailer@example.com"
        assert kwargs["password"] == "secret123"
        assert kwargs["start_tls"] is True
        assert kwargs["use_tls"] is False


@pytest.mark.asyncio
async def test_email_service_send_exception_handling():
    """Exceptions during SMTP communication should be caught and return False."""
    with patch.object(settings, "SMTP_ENABLED", True), \
         patch.object(settings, "SMTP_HOST", "smtp.example.com"), \
         patch.object(settings, "SMTP_PORT", 587), \
         patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:

        mock_send.side_effect = Exception("SMTP connection timed out")
        service = EmailService()

        result = await service.send_registration_otp_email(
            to_email="newuser@example.com",
            full_name="New User",
            otp="654321",
        )

        assert result is False


@pytest.mark.asyncio
async def test_registration_flow_triggers_email_background(client: AsyncClient):
    """Register endpoint should dispatch email sending in background."""
    with patch("app.services.email.email_service.send_registration_otp_email", new_callable=AsyncMock) as mock_send_reg:
        mock_send_reg.return_value = True

        payload = {
            "email": "async.email@example.com",
            "full_name": "Async Tester",
            "password": "SecurePassword123!",
        }

        response = await client.post("/api/auth/register", json=payload)
        assert response.status_code == 201

        # Check background task was executed
        assert mock_send_reg.call_count == 1
        call_kwargs = mock_send_reg.call_args.kwargs
        assert call_kwargs["to_email"] == "async.email@example.com"
        assert call_kwargs["full_name"] == "Async Tester"
        assert len(call_kwargs["otp"]) == 6
