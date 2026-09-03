import os
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional
from beanie import PydanticObjectId
from fastapi import HTTPException

from app.models.user import User
from app.repositories.user import user_repo

current_user_id_ctx: ContextVar[Optional[str]] = ContextVar("current_user_id_ctx", default=None)


@contextmanager
def user_context(user_id: str):
    """Context manager to set the active user ID for tool executions."""
    token = current_user_id_ctx.set(user_id)
    try:
        yield
    finally:
        current_user_id_ctx.reset(token)


async def resolve_user(user_id: Optional[str] = None) -> User:
    """
    Resolves and returns the User object for tool execution.
    Precedence:
    1. Explicitly passed `user_id`
    2. Context variable `current_user_id_ctx`
    3. Environment variable `POCKETFLOW_DEFAULT_USER_ID`
    4. Environment variable `POCKETFLOW_DEFAULT_USER_EMAIL`
    5. Single active user fallback (if only 1 user exists in the database)
    """
    target_id = user_id or current_user_id_ctx.get() or os.getenv("POCKETFLOW_DEFAULT_USER_ID")
    
    if target_id:
        try:
            oid = PydanticObjectId(target_id)
        except Exception:
            raise ValueError(f"Invalid user ID format: '{target_id}'")
        user = await user_repo.get_by_id(oid)
        if not user:
            raise ValueError(f"User with ID '{target_id}' not found.")
        return user

    default_email = os.getenv("POCKETFLOW_DEFAULT_USER_EMAIL")
    if default_email:
        user = await user_repo.get_by_email(default_email)
        if not user:
            raise ValueError(f"User with default email '{default_email}' not found.")
        return user

    # Fallback: check if exactly one user exists in the database (e.g. personal single-user setup)
    users = await User.find_all().limit(2).to_list()
    if len(users) == 1:
        return users[0]

    raise ValueError(
        "User context is required for this operation. "
        "Provide 'user_id' in the tool parameters, use 'user_context()', "
        "or set 'POCKETFLOW_DEFAULT_USER_ID' in your environment."
    )
