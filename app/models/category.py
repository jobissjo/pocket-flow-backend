from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Category(Document):
    name: str
    type: CategoryType
    icon: str = "tag"
    is_system: bool = False
    user_id: Optional[Indexed(PydanticObjectId)] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class Settings:
        name = "categories"
        use_state_management = True
