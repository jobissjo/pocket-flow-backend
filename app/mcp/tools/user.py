from typing import Any, Dict, Optional

from app.mcp.context import resolve_user
from app.mcp.registry import register_tool
from app.schemas.user import UserUpdate
from app.services.user import user_service


@register_tool(
    name="get_user_profile",
    description="Retrieve profile information of the current user (name, email, mobile, account status).",
    category="user",
)
async def get_user_profile(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get user profile."""
    user = await resolve_user(user_id)
    profile = user_service.get_profile(user)
    return profile.model_dump(mode="json")


@register_tool(
    name="update_user_profile",
    description="Update user profile information such as full name or mobile number.",
    category="user",
)
async def update_user_profile(
    full_name: Optional[str] = None,
    mobile: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update user profile fields."""
    user = await resolve_user(user_id)
    update_data = UserUpdate(
        full_name=full_name,
        mobile=mobile,
    )
    updated = await user_service.update_profile(user, update_data)
    return updated.model_dump(mode="json")
