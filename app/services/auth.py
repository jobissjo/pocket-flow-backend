import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import BackgroundTasks, HTTPException, status

from app.core.config import settings
from app.services.email import email_service
from app.core.security import (
    create_access_token,
    generate_otp,
    get_otp_expiry,
    get_password_hash,
    utc_now,
    verify_password,
)
from app.models.user import User
from app.repositories.user import user_repo
from app.schemas.auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    VerifyOTPRequest,
)
from app.schemas.user import UserResponse


class AuthService:
    async def register(
        self,
        data: UserRegisterRequest,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Dict[str, Any]:
        existing_email = await user_repo.get_by_email(data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists.",
            )

        if data.mobile:
            existing_mobile = await user_repo.get_by_mobile(data.mobile)
            if existing_mobile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this mobile number already exists.",
                )

        otp = generate_otp()
        otp_expiry = get_otp_expiry(settings.OTP_EXPIRE_MINUTES)
        hashed_password = get_password_hash(data.password)

        new_user = User(
            email=data.email.lower(),
            mobile=data.mobile,
            full_name=data.full_name,
            hashed_password=hashed_password,
            is_active=False,
            otp=otp,
            otp_expires_at=otp_expiry,
        )
        saved_user = await user_repo.create(new_user)

        # Dispatch async email sending
        if background_tasks:
            background_tasks.add_task(
                email_service.send_registration_otp_email,
                to_email=saved_user.email,
                full_name=saved_user.full_name,
                otp=otp,
            )
        else:
            asyncio.create_task(
                email_service.send_registration_otp_email(
                    to_email=saved_user.email,
                    full_name=saved_user.full_name,
                    otp=otp,
                )
            )

        return {
            "message": "Registration successful. Please verify the OTP sent to your email.",
            "otp_preview": otp if settings.DEBUG else None,  # For local testing convenience
            "user": UserResponse(
                id=str(saved_user.id),
                email=saved_user.email,
                mobile=saved_user.mobile,
                full_name=saved_user.full_name,
                is_active=saved_user.is_active,
                created_at=saved_user.created_at,
                updated_at=saved_user.updated_at,
            ),
        }

    async def verify_otp(self, data: VerifyOTPRequest) -> TokenResponse:
        user = await user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found.",
            )

        if not user.otp or user.otp != data.otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP.",
            )

        now = utc_now()
        otp_expiry = user.otp_expires_at.replace(tzinfo=None) if user.otp_expires_at else None
        if otp_expiry and otp_expiry < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )

        # Activate user and clear OTP
        user.is_active = True
        user.otp = None
        user.otp_expires_at = None
        user.updated_at = now
        await user_repo.save(user)

        token = create_access_token(subject=str(user.id))
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def login(self, data: UserLoginRequest) -> TokenResponse:
        user = await user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is not activated. Please verify your OTP.",
            )

        token = create_access_token(subject=str(user.id))
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def resend_otp(
        self,
        email: str,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Dict[str, Any]:
        user = await user_repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email does not exist.",
            )

        otp = generate_otp()
        user.otp = otp
        user.otp_expires_at = get_otp_expiry(settings.OTP_EXPIRE_MINUTES)
        user.updated_at = utc_now()
        await user_repo.save(user)

        if background_tasks:
            background_tasks.add_task(
                email_service.send_resend_otp_email,
                to_email=user.email,
                full_name=user.full_name,
                otp=otp,
            )
        else:
            asyncio.create_task(
                email_service.send_resend_otp_email(
                    to_email=user.email,
                    full_name=user.full_name,
                    otp=otp,
                )
            )

        return {
            "message": "A new OTP has been sent.",
            "otp_preview": otp if settings.DEBUG else None,
        }

    async def forgot_password(
        self,
        data: ForgotPasswordRequest,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> Dict[str, Any]:
        user = await user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email address.",
            )

        otp = generate_otp()
        user.otp = otp
        user.otp_expires_at = get_otp_expiry(settings.OTP_EXPIRE_MINUTES)
        user.updated_at = utc_now()
        await user_repo.save(user)

        if background_tasks:
            background_tasks.add_task(
                email_service.send_password_reset_otp_email,
                to_email=user.email,
                full_name=user.full_name,
                otp=otp,
            )
        else:
            asyncio.create_task(
                email_service.send_password_reset_otp_email(
                    to_email=user.email,
                    full_name=user.full_name,
                    otp=otp,
                )
            )

        return {
            "message": "Password reset OTP has been sent.",
            "otp_preview": otp if settings.DEBUG else None,
        }

    async def reset_password(self, data: ResetPasswordRequest) -> Dict[str, Any]:
        user = await user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        if not user.otp or user.otp != data.otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP.",
            )

        now = utc_now()
        otp_expiry = user.otp_expires_at.replace(tzinfo=None) if user.otp_expires_at else None
        if otp_expiry and otp_expiry < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )

        user.hashed_password = get_password_hash(data.new_password)
        user.otp = None
        user.otp_expires_at = None
        user.updated_at = now
        await user_repo.save(user)

        return {"message": "Password reset successfully. You can now log in."}


auth_service = AuthService()
