from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field


class User(Document):
    email: Indexed(str, unique=True)
    mobile: Optional[Indexed(str)] = None
    full_name: str
    hashed_password: Optional[str] = None
    is_active: bool = False
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    auth_provider: str = "local"
    otp: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "users"
        use_state_management = True
