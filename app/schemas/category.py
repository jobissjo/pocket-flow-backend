from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.category import CategoryType


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    type: CategoryType
    icon: str = Field(default="tag", max_length=50)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    type: Optional[CategoryType] = None
    icon: Optional[str] = Field(None, max_length=50)


class CategoryResponse(BaseModel):
    id: str
    name: str
    type: CategoryType
    icon: str
    is_system: bool
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
