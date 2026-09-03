"""
Domain-specific MCP tools for PocketFlow operations.
Separated into individual modules:
- accounts: list, get, create, update, delete
- transactions: list, get, create, update, delete
- categories: list, get, create, update, delete
- credit_cards: list, get, create, update, delete
- emis: list, get, create, update, delete, mark_paid
- dashboard: get_dashboard_summary, get_financial_analytics, get_recent_transactions, get_upcoming_emis
- user: get_user_profile, update_user_profile
"""

from app.mcp.tools.accounts import (
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)
from app.mcp.tools.categories import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)
from app.mcp.tools.credit_cards import (
    create_credit_card,
    delete_credit_card,
    get_credit_card,
    list_credit_cards,
    update_credit_card,
)
from app.mcp.tools.dashboard import (
    get_dashboard_summary,
    get_financial_analytics,
    get_recent_transactions,
    get_upcoming_emis,
)
from app.mcp.tools.emis import (
    create_emi,
    delete_emi,
    get_emi,
    list_emis,
    mark_emi_paid,
    update_emi,
)
from app.mcp.tools.transactions import (
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    update_transaction,
)
from app.mcp.tools.user import (
    get_user_profile,
    update_user_profile,
)

__all__ = [
    # Accounts
    "list_accounts",
    "get_account",
    "create_account",
    "update_account",
    "delete_account",
    # Transactions
    "list_transactions",
    "get_transaction",
    "create_transaction",
    "update_transaction",
    "delete_transaction",
    # Categories
    "list_categories",
    "get_category",
    "create_category",
    "update_category",
    "delete_category",
    # Credit Cards
    "list_credit_cards",
    "get_credit_card",
    "create_credit_card",
    "update_credit_card",
    "delete_credit_card",
    # EMIs
    "list_emis",
    "get_emi",
    "create_emi",
    "update_emi",
    "delete_emi",
    "mark_emi_paid",
    # Dashboard & Analytics
    "get_dashboard_summary",
    "get_financial_analytics",
    "get_recent_transactions",
    "get_upcoming_emis",
    # User Profile
    "get_user_profile",
    "update_user_profile",
]
