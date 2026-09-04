from typing import Any, Dict
from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    ResetPasswordRequest,
    ResendOTPRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    VerifyOTPRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services.auth import auth_service
from app.services.user import user_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in or register with Google",
    description="Validates Google ID Token from Google Identity Services, creates or links account, and returns a JWT access token.",
)
async def google_login(data: GoogleLoginRequest) -> TokenResponse:
    return await auth_service.google_login(data.credential)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a user and sends an initial verification OTP.",
)
async def register(
    data: UserRegisterRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    return await auth_service.register(data, background_tasks=background_tasks)


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verify registration OTP",
    description="Verifies the OTP, activates the user, and returns an access token.",
)
async def verify_otp(data: VerifyOTPRequest) -> TokenResponse:
    return await auth_service.verify_otp(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticates user credentials and returns a JWT access token.",
)
async def login(data: UserLoginRequest) -> TokenResponse:
    return await auth_service.login(data)


@router.post(
    "/resend-otp",
    summary="Resend OTP",
    description="Regenerates and resends a verification OTP.",
)
async def resend_otp(
    data: ResendOTPRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    return await auth_service.resend_otp(data.email, background_tasks=background_tasks)


@router.post(
    "/forgot-password",
    summary="Request password reset",
    description="Sends a password reset OTP to the user's email.",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    return await auth_service.forgot_password(data, background_tasks=background_tasks)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with OTP",
    description="Validates the OTP and updates the user's password.",
)
async def reset_password(data: ResetPasswordRequest) -> MessageResponse:
    result = await auth_service.reset_password(data)
    return MessageResponse(message=result["message"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user details",
    description="Returns the profile details of the authenticated user.",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return user_service.get_profile(current_user)
