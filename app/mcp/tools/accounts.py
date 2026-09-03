from typing import Any, Dict, List, Optional

from app.mcp.context import resolve_user
from app.mcp.registry import register_tool
from app.models.account import AccountType
from app.schemas.account import AccountCreate, AccountUpdate
from app.services.account import account_service


@register_tool(
    name="list_accounts",
    description="List all bank accounts, wallets, and cash balances for the user.",
    category="accounts",
)
async def list_accounts(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all accounts for the user."""
    user = await resolve_user(user_id)
    accounts = await account_service.list_accounts(user)
    return [acc.model_dump(mode="json") for acc in accounts]


@register_tool(
    name="get_account",
    description="Retrieve details of a specific account by its account ID.",
    category="accounts",
)
async def get_account(account_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get single account details by ID."""
    user = await resolve_user(user_id)
    acc = await account_service.get_account(account_id, user)
    return acc.model_dump(mode="json")


@register_tool(
    name="create_account",
    description="Create a new bank account, cash account, or wallet.",
    category="accounts",
)
async def create_account(
    name: str,
    bank_name: str,
    account_number: str,
    account_type: str = "savings",
    balance: float = 0.0,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new account with specified type and initial balance."""
    user = await resolve_user(user_id)
    account_data = AccountCreate(
        name=name,
        bank_name=bank_name,
        account_number=account_number,
        account_type=AccountType(account_type.lower()),
        balance=balance,
    )
    saved = await account_service.create_account(user, account_data)
    return saved.model_dump(mode="json")


@register_tool(
    name="update_account",
    description="Update an existing account's name, bank name, balance, or type.",
    category="accounts",
)
async def update_account(
    account_id: str,
    name: Optional[str] = None,
    bank_name: Optional[str] = None,
    account_number: Optional[str] = None,
    account_type: Optional[str] = None,
    balance: Optional[float] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update fields of an account."""
    user = await resolve_user(user_id)
    update_data = AccountUpdate(
        name=name,
        bank_name=bank_name,
        account_number=account_number,
        account_type=AccountType(account_type.lower()) if account_type else None,
        balance=balance,
    )
    updated = await account_service.update_account(account_id, user, update_data)
    return updated.model_dump(mode="json")


@register_tool(
    name="delete_account",
    description="Delete a bank or cash account by its account ID.",
    category="accounts",
)
async def delete_account(account_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Delete an account."""
    user = await resolve_user(user_id)
    await account_service.delete_account(account_id, user)
    return {"message": f"Account '{account_id}' deleted successfully."}
