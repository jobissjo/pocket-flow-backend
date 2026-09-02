import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def _is_configured(self) -> bool:
        """Check if SMTP is enabled and adequately configured."""
        return bool(
            settings.SMTP_ENABLED
            and settings.SMTP_HOST
            and settings.SMTP_PORT
        )

    def _get_from_email(self) -> str:
        """Get sender email address."""
        return settings.EMAILS_FROM_EMAIL or settings.SMTP_USER or "noreply@pocketflow.local"

    async def send_email_async(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Sends an email asynchronously via SMTP.
        Returns True if sent successfully, False otherwise.
        """
        if not self._is_configured():
            logger.info(
                "SMTP is disabled or not configured. Skipped sending email to '%s' (Subject: '%s').",
                to_email,
                subject,
            )
            return False

        from_email = self._get_from_email()
        from_header = f"{settings.EMAILS_FROM_NAME} <{from_email}>"

        message = MIMEMultipart("alternative")
        message["From"] = from_header
        message["To"] = to_email
        message["Subject"] = subject

        if text_content:
            message.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            message.attach(MIMEText(html_content, "html", "utf-8"))

        # Smart TLS/SSL selection based on port and configuration
        if settings.SMTP_PORT == 465:
            use_tls = True
            start_tls = False
        elif settings.SMTP_PORT == 587:
            use_tls = False
            start_tls = True
        else:
            use_tls = bool(settings.SMTP_SSL)
            start_tls = bool(settings.SMTP_TLS) if not use_tls else False

        username = settings.SMTP_USER if settings.SMTP_USER else None
        password = settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=username,
                password=password,
                use_tls=use_tls,
                start_tls=start_tls,
                timeout=15,
            )
            logger.info("Successfully sent email to %s (Subject: '%s')", to_email, subject)
            return True
        except (aiosmtplib.errors.SMTPAuthenticationError, aiosmtplib.errors.SMTPServerDisconnected) as e:
            logger.error(
                "SMTP authentication failed or connection rejected by %s:%s for '%s'. "
                "Please check SMTP_USER and SMTP_PASSWORD (or App Password) in .env. Details: %s",
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                username,
                e,
            )
            return False
        except (aiosmtplib.errors.SMTPConnectTimeoutError, aiosmtplib.errors.SMTPTimeoutError, TimeoutError) as e:
            logger.error(
                "SMTP connection timed out while reaching %s:%s. Please verify host and network settings: %s",
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                e,
            )
            return False
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e), exc_info=True)
            return False

    async def send_registration_otp_email(
        self,
        to_email: str,
        full_name: str,
        otp: str,
    ) -> bool:
        """Send account verification OTP email to newly registered user."""
        subject = f"{otp} is your PocketFlow verification code"
        name = full_name.strip() if full_name else "there"

        text_content = (
            f"Hello {name},\n\n"
            f"Thank you for signing up for PocketFlow!\n\n"
            f"Your verification code is: {otp}\n\n"
            f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
            f"If you did not request this code, you can safely ignore this email.\n\n"
            f"Best regards,\nThe PocketFlow Team"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PocketFlow Verification Code</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f4f6f9;
      margin: 0;
      padding: 24px;
      color: #1e293b;
    }}
    .container {{
      max-width: 520px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      border: 1px solid #e2e8f0;
    }}
    .header {{
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      padding: 32px 24px;
      text-align: center;
      color: #ffffff;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
    .content {{
      padding: 32px 28px;
    }}
    .greeting {{
      font-size: 16px;
      margin-bottom: 16px;
      color: #334155;
    }}
    .otp-container {{
      text-align: center;
      margin: 28px 0;
      background: #f8fafc;
      border: 2px dashed #cbd5e1;
      border-radius: 8px;
      padding: 20px;
    }}
    .otp-code {{
      font-size: 32px;
      font-weight: 800;
      letter-spacing: 8px;
      color: #4f46e5;
      font-family: 'Courier New', Courier, monospace;
    }}
    .expiry {{
      font-size: 13px;
      color: #64748b;
      margin-top: 8px;
    }}
    .notice {{
      font-size: 13px;
      color: #64748b;
      line-height: 1.5;
      border-top: 1px solid #e2e8f0;
      padding-top: 20px;
      margin-top: 24px;
    }}
    .footer {{
      background: #f8fafc;
      padding: 16px;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
      border-top: 1px solid #e2e8f0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>PocketFlow</h1>
    </div>
    <div class="content">
      <p class="greeting">Hello <strong>{name}</strong>,</p>
      <p>Thank you for signing up! Please enter the verification code below to activate your PocketFlow account:</p>
      <div class="otp-container">
        <div class="otp-code">{otp}</div>
        <div class="expiry">Valid for the next {settings.OTP_EXPIRE_MINUTES} minutes</div>
      </div>
      <p class="notice">
        If you did not create an account with PocketFlow, please disregard this email.
      </p>
    </div>
    <div class="footer">
      &copy; PocketFlow. All rights reserved.
    </div>
  </div>
</body>
</html>"""
        return await self.send_email_async(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_resend_otp_email(
        self,
        to_email: str,
        full_name: str,
        otp: str,
    ) -> bool:
        """Send a new verification OTP email."""
        subject = f"{otp} is your new PocketFlow verification code"
        name = full_name.strip() if full_name else "there"

        text_content = (
            f"Hello {name},\n\n"
            f"Here is your new verification code: {otp}\n\n"
            f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Best regards,\nThe PocketFlow Team"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PocketFlow Verification Code</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f4f6f9;
      margin: 0;
      padding: 24px;
      color: #1e293b;
    }}
    .container {{
      max-width: 520px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      border: 1px solid #e2e8f0;
    }}
    .header {{
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      padding: 32px 24px;
      text-align: center;
      color: #ffffff;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 700;
    }}
    .content {{
      padding: 32px 28px;
    }}
    .otp-container {{
      text-align: center;
      margin: 28px 0;
      background: #f8fafc;
      border: 2px dashed #cbd5e1;
      border-radius: 8px;
      padding: 20px;
    }}
    .otp-code {{
      font-size: 32px;
      font-weight: 800;
      letter-spacing: 8px;
      color: #4f46e5;
      font-family: 'Courier New', Courier, monospace;
    }}
    .expiry {{
      font-size: 13px;
      color: #64748b;
      margin-top: 8px;
    }}
    .notice {{
      font-size: 13px;
      color: #64748b;
      line-height: 1.5;
      border-top: 1px solid #e2e8f0;
      padding-top: 20px;
      margin-top: 24px;
    }}
    .footer {{
      background: #f8fafc;
      padding: 16px;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
      border-top: 1px solid #e2e8f0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>PocketFlow</h1>
    </div>
    <div class="content">
      <p>Hello <strong>{name}</strong>,</p>
      <p>Here is your new One-Time Password (OTP) to verify your account:</p>
      <div class="otp-container">
        <div class="otp-code">{otp}</div>
        <div class="expiry">Valid for {settings.OTP_EXPIRE_MINUTES} minutes</div>
      </div>
      <p class="notice">
        If you did not request this OTP, no action is needed.
      </p>
    </div>
    <div class="footer">
      &copy; PocketFlow. All rights reserved.
    </div>
  </div>
</body>
</html>"""
        return await self.send_email_async(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_password_reset_otp_email(
        self,
        to_email: str,
        full_name: str,
        otp: str,
    ) -> bool:
        """Send password reset OTP email."""
        subject = f"{otp} is your PocketFlow password reset code"
        name = full_name.strip() if full_name else "there"

        text_content = (
            f"Hello {name},\n\n"
            f"We received a request to reset your PocketFlow password.\n\n"
            f"Your reset code is: {otp}\n\n"
            f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
            f"If you did not request a password reset, please ignore this email.\n\n"
            f"Best regards,\nThe PocketFlow Team"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your PocketFlow Password</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f4f6f9;
      margin: 0;
      padding: 24px;
      color: #1e293b;
    }}
    .container {{
      max-width: 520px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      border: 1px solid #e2e8f0;
    }}
    .header {{
      background: linear-gradient(135deg, #ef4444 0%, #f97316 100%);
      padding: 32px 24px;
      text-align: center;
      color: #ffffff;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 700;
    }}
    .content {{
      padding: 32px 28px;
    }}
    .otp-container {{
      text-align: center;
      margin: 28px 0;
      background: #fff1f2;
      border: 2px dashed #fca5a5;
      border-radius: 8px;
      padding: 20px;
    }}
    .otp-code {{
      font-size: 32px;
      font-weight: 800;
      letter-spacing: 8px;
      color: #dc2626;
      font-family: 'Courier New', Courier, monospace;
    }}
    .expiry {{
      font-size: 13px;
      color: #64748b;
      margin-top: 8px;
    }}
    .notice {{
      font-size: 13px;
      color: #64748b;
      line-height: 1.5;
      border-top: 1px solid #e2e8f0;
      padding-top: 20px;
      margin-top: 24px;
    }}
    .footer {{
      background: #f8fafc;
      padding: 16px;
      text-align: center;
      font-size: 12px;
      color: #94a3b8;
      border-top: 1px solid #e2e8f0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>PocketFlow Password Reset</h1>
    </div>
    <div class="content">
      <p>Hello <strong>{name}</strong>,</p>
      <p>We received a request to reset your password. Use the following code to proceed:</p>
      <div class="otp-container">
        <div class="otp-code">{otp}</div>
        <div class="expiry">Valid for {settings.OTP_EXPIRE_MINUTES} minutes</div>
      </div>
      <p class="notice">
        If you did not request a password reset, please ignore this email or review your account security.
      </p>
    </div>
    <div class="footer">
      &copy; PocketFlow. All rights reserved.
    </div>
  </div>
</body>
</html>"""
        return await self.send_email_async(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


email_service = EmailService()
