from typing import Any, Dict, List, Optional

from app.mcp.context import resolve_user
from app.mcp.registry import register_tool
from app.models.category import CategoryType
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.category import category_service


@register_tool(
    name="list_categories",
    description="List all income and expense categories (both system-default and user-created).",
    category="categories",
)
async def list_categories(
    type: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List categories, optionally filtered by 'income' or 'expense'."""
    user = await resolve_user(user_id)
    cat_type = CategoryType(type.lower()) if type else None
    cats = await category_service.list_categories(user, category_type=cat_type)
    return [c.model_dump(mode="json") for c in cats]


@register_tool(
    name="get_category",
    description="Retrieve details of a specific category by its ID.",
    category="categories",
)
async def get_category(category_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get category by ID."""
    user = await resolve_user(user_id)
    cat = await category_service.get_category(category_id, user)
    return cat.model_dump(mode="json")


@register_tool(
    name="create_category",
    description="Create a new custom category (type: 'income' or 'expense').",
    category="categories",
)
async def create_category(
    name: str,
    type: str,
    icon: str = "tag",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create custom category."""
    user = await resolve_user(user_id)
    cat_data = CategoryCreate(
        name=name,
        type=CategoryType(type.lower()),
        icon=icon,
    )
    saved = await category_service.create_category(user, cat_data)
    return saved.model_dump(mode="json")


@register_tool(
    name="update_category",
    description="Update a custom user category's name, type, or icon. (System default categories cannot be modified).",
    category="categories",
)
async def update_category(
    category_id: str,
    name: Optional[str] = None,
    type: Optional[str] = None,
    icon: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update custom category."""
    user = await resolve_user(user_id)
    cat_update = CategoryUpdate(
        name=name,
        type=CategoryType(type.lower()) if type else None,
        icon=icon,
    )
    updated = await category_service.update_category(category_id, user, cat_update)
    return updated.model_dump(mode="json")


@register_tool(
    name="delete_category",
    description="Delete a custom user category by ID. (System default categories cannot be deleted).",
    category="categories",
)
async def delete_category(category_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete custom category."""
    user = await resolve_user(user_id)
    await category_service.delete_category(category_id, user)
    return {"message": f"Category '{category_id}' deleted successfully."}
