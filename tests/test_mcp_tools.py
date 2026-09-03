import pytest
from httpx import AsyncClient

from app.models.user import User
from app.mcp.context import user_context
from app.mcp.registry import (
    execute_tool,
    get_all_tools,
    get_openai_tools,
    get_tool_schemas,
    tool_registry,
)
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


@pytest.fixture
async def test_user(client: AsyncClient, auth_headers: dict) -> User:
    user = await User.find_one(User.email == "testuser@example.com")
    assert user is not None
    return user


@pytest.mark.asyncio
async def test_registry_and_schemas():
    """Verify registry population and schema generation."""
    tools = get_all_tools()
    assert len(tools) >= 30

    openai_tools = get_openai_tools()
    assert len(openai_tools) == len(tools)
    for tool in openai_tools:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]

    schemas = get_tool_schemas()
    assert "create_transaction" in schemas
    assert "list_accounts" in schemas
    assert "get_dashboard_summary" in schemas


@pytest.mark.asyncio
async def test_account_tools(test_user: User):
    """Test accounts operations."""
    uid = str(test_user.id)

    # 1. Create account
    created = await create_account(
        name="Axis Savings",
        bank_name="Axis Bank",
        account_number="1234567890",
        account_type="savings",
        balance=10000.0,
        user_id=uid,
    )
    assert created["name"] == "Axis Savings"
    assert created["balance"] == 10000.0
    acc_id = created["id"]

    # 2. Get account
    fetched = await get_account(acc_id, user_id=uid)
    assert fetched["id"] == acc_id
    assert fetched["bank_name"] == "Axis Bank"

    # 3. List accounts
    acc_list = await list_accounts(user_id=uid)
    assert len(acc_list) == 1
    assert acc_list[0]["id"] == acc_id

    # 4. Update account
    updated = await update_account(
        acc_id, name="Axis Main Account", balance=12500.0, user_id=uid
    )
    assert updated["name"] == "Axis Main Account"
    assert updated["balance"] == 12500.0

    # 5. Delete account
    del_res = await delete_account(acc_id, user_id=uid)
    assert "deleted successfully" in del_res["message"]

    remaining = await list_accounts(user_id=uid)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_category_tools(test_user: User):
    """Test category operations."""
    uid = str(test_user.id)

    # 1. List default categories
    cats = await list_categories(user_id=uid)
    assert len(cats) > 0  # system categories seeded

    # 2. Create custom category
    created = await create_category(
        name="Crypto Investment",
        type="expense",
        icon="bitcoin",
        user_id=uid,
    )
    cat_id = created["id"]
    assert created["name"] == "Crypto Investment"

    # 3. Get category
    fetched = await get_category(cat_id, user_id=uid)
    assert fetched["name"] == "Crypto Investment"

    # 4. Update category
    updated = await update_category(cat_id, name="Digital Assets", user_id=uid)
    assert updated["name"] == "Digital Assets"

    # 5. Delete category
    del_res = await delete_category(cat_id, user_id=uid)
    assert "deleted successfully" in del_res["message"]


@pytest.mark.asyncio
async def test_credit_card_tools(test_user: User):
    """Test credit card operations."""
    uid = str(test_user.id)

    # 1. Create credit card
    created = await create_credit_card(
        card_name="Millennia",
        provider="HDFC",
        last_four="4321",
        credit_limit=100000.0,
        outstanding_amount=5000.0,
        billing_date=15,
        payment_due_date=5,
        user_id=uid,
    )
    card_id = created["id"]
    assert created["card_name"] == "Millennia"
    assert created["available_limit"] == 95000.0

    # 2. Get credit card
    fetched = await get_credit_card(card_id, user_id=uid)
    assert fetched["provider"] == "HDFC"

    # 3. List credit cards
    cards = await list_credit_cards(user_id=uid)
    assert len(cards) == 1

    # 4. Update credit card
    updated = await update_credit_card(card_id, outstanding_amount=7000.0, user_id=uid)
    assert updated["outstanding_amount"] == 7000.0
    assert updated["available_limit"] == 93000.0

    # 5. Delete credit card
    del_res = await delete_credit_card(card_id, user_id=uid)
    assert "deleted successfully" in del_res["message"]


@pytest.mark.asyncio
async def test_transactions_and_financial_effects(test_user: User):
    """Test transaction creation, filtering, and balance side effects."""
    uid = str(test_user.id)

    # Setup bank account and category
    acc = await create_account(
        name="Salary Acct",
        bank_name="ICICI",
        account_number="9988776655",
        balance=5000.0,
        user_id=uid,
    )
    acc_id = acc["id"]

    cat = await create_category(name="Groceries", type="expense", user_id=uid)
    cat_id = cat["id"]

    # 1. Create expense transaction
    tx = await create_transaction(
        title="Weekly Veggies",
        amount=1200.0,
        type="expense",
        category_id=cat_id,
        account_id=acc_id,
        notes="From supermarket",
        user_id=uid,
    )
    tx_id = tx["id"]
    assert tx["title"] == "Weekly Veggies"
    assert tx["amount"] == 1200.0

    # Verify balance was deducted: 5000 - 1200 = 3800
    acc_check = await get_account(acc_id, user_id=uid)
    assert acc_check["balance"] == 3800.0

    # 2. List transactions
    tx_list = await list_transactions(search="Veggies", user_id=uid)
    assert tx_list["total"] == 1
    assert tx_list["items"][0]["id"] == tx_id

    # 3. Update transaction amount to 1500
    updated_tx = await update_transaction(tx_id, amount=1500.0, user_id=uid)
    assert updated_tx["amount"] == 1500.0

    # Verify balance adjusted: 5000 - 1500 = 3500
    acc_check2 = await get_account(acc_id, user_id=uid)
    assert acc_check2["balance"] == 3500.0

    # 4. Delete transaction -> reverts balance to 5000
    del_res = await delete_transaction(tx_id, user_id=uid)
    assert "deleted successfully" in del_res["message"]

    acc_check3 = await get_account(acc_id, user_id=uid)
    assert acc_check3["balance"] == 5000.0


@pytest.mark.asyncio
async def test_emi_tools(test_user: User):
    """Test EMI tools including mark paid."""
    uid = str(test_user.id)

    acc = await create_account(
        name="EMI Savings",
        bank_name="SBI",
        account_number="5544332211",
        balance=20000.0,
        user_id=uid,
    )
    acc_id = acc["id"]

    # 1. Create EMI
    emi = await create_emi(
        name="MacBook Pro",
        total_amount=120000.0,
        monthly_emi_amount=10000.0,
        total_installments=12,
        paid_installments=0,
        account_id=acc_id,
        due_day=10,
        user_id=uid,
    )
    emi_id = emi["id"]
    assert emi["name"] == "MacBook Pro"
    assert emi["remaining_installments"] == 12

    # 2. Mark paid
    mark_res = await mark_emi_paid(emi_id, user_id=uid)
    assert "Installment 1 of 12 marked as paid" in mark_res["message"]
    assert mark_res["emi"]["paid_installments"] == 1
    assert mark_res["emi"]["remaining_installments"] == 11

    # Verify account balance deducted: 20000 - 10000 = 10000
    acc_after = await get_account(acc_id, user_id=uid)
    assert acc_after["balance"] == 10000.0

    # 3. List EMIs
    emis = await list_emis(status="active", user_id=uid)
    assert len(emis) == 1

    # 4. Delete EMI
    del_res = await delete_emi(emi_id, user_id=uid)
    assert "deleted successfully" in del_res["message"]


@pytest.mark.asyncio
async def test_dashboard_and_user_tools(test_user: User):
    """Test dashboard KPIs, analytics, and user profile tools."""
    uid = str(test_user.id)

    # 1. User profile
    profile = await get_user_profile(user_id=uid)
    assert profile["email"] == "testuser@example.com"
    assert profile["full_name"] == "Test User"

    updated_prof = await update_user_profile(full_name="Updated Name", user_id=uid)
    assert updated_prof["full_name"] == "Updated Name"

    # 2. Dashboard summary
    summary = await get_dashboard_summary(user_id=uid)
    assert "total_balance" in summary
    assert "net_savings" in summary

    # 3. Analytics
    analytics = await get_financial_analytics(user_id=uid)
    assert "income_vs_expense" in analytics
    assert "expense_breakdown" in analytics

    # 4. Recent & Upcoming
    recent = await get_recent_transactions(limit=5, user_id=uid)
    assert isinstance(recent, list)

    upcoming = await get_upcoming_emis(limit=5, user_id=uid)
    assert isinstance(upcoming, list)


@pytest.mark.asyncio
async def test_execute_tool_dispatcher(test_user: User):
    """Test dynamic tool execution through the dispatcher as an AI chat agent would."""
    uid = str(test_user.id)

    # Test successful tool execution
    res = await execute_tool(
        name="create_account",
        arguments={
            "name": "Dispatcher Account",
            "bank_name": "Kotak",
            "account_number": "1122334455",
            "balance": 7500.0,
        },
        user_id=uid,
    )
    assert res["success"] is True
    assert res["data"]["name"] == "Dispatcher Account"
    acc_id = res["data"]["id"]

    # Test tool listing accounts
    res_list = await execute_tool("list_accounts", {}, user_id=uid)
    assert res_list["success"] is True
    assert any(a["id"] == acc_id for a in res_list["data"])

    # Test non-existent tool
    err_res = await execute_tool("non_existent_tool", {}, user_id=uid)
    assert err_res["success"] is False
    assert "not found" in err_res["error"]
