from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient
from langchain_core.messages import AIMessage

from app.core.config import settings
from app.models.account import Account
from app.models.user import User


@pytest.fixture
async def test_user(client: AsyncClient, auth_headers: dict) -> User:
    user = await User.find_one(User.email == "testuser@example.com")
    assert user is not None
    return user


@pytest.mark.asyncio
async def test_ai_chat_missing_api_key(client: AsyncClient, auth_headers: dict):
    """When API keys are not configured, endpoint returns 400 Bad Request with guidance."""
    with patch.object(settings, "GROQ_API_KEY", ""):
        response = await client.post(
            "/api/ai/chat",
            headers=auth_headers,
            json={"message": "Hello, what is my balance?", "provider": "groq"},
        )
        assert response.status_code == 400
        assert "GROQ_API_KEY is not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ai_chat_unsupported_provider(client: AsyncClient, auth_headers: dict):
    """Unsupported provider returns 422 or 400 validation error."""
    response = await client.post(
        "/api/ai/chat",
        headers=auth_headers,
        json={"message": "Hello", "provider": "unsupported_provider"},
    )
    assert response.status_code == 422  # Pydantic Literal validation error


@pytest.mark.asyncio
async def test_ai_chat_direct_conversation(client: AsyncClient, auth_headers: dict):
    """Test conversational response without tool execution."""
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm

    # LLM returns a conversational reply without calling tools
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(
            content="Hello! I am your PocketFlow assistant. How can I assist you with your finances today?"
        )
    )

    with patch("app.services.ai_chat.ai_chat_service.get_chat_model") as mock_get_model:
        mock_get_model.return_value = (mock_llm, "groq", "llama-3.3-70b-versatile")

        response = await client.post(
            "/api/ai/chat",
            headers=auth_headers,
            json={
                "message": "Hi there!",
                "history": [],
                "provider": "groq",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "PocketFlow assistant" in data["reply"]
        assert len(data["tool_executions"]) == 0
        assert data["provider"] == "groq"
        assert data["model"] == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_ai_chat_proactive_clarification(client: AsyncClient, auth_headers: dict):
    """
    When user provides incomplete information (e.g. 'Add an expense'),
    the assistant responds with a polite clarifying question rather than calling tools.
    """
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm

    # Mock response where model asks for details
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(
            content="I'd be happy to record that expense! Could you please share how much it cost, what it was for, and which account or credit card you used?"
        )
    )

    with patch("app.services.ai_chat.ai_chat_service.get_chat_model") as mock_get_model:
        mock_get_model.return_value = (mock_llm, "groq", "llama-3.3-70b-versatile")

        response = await client.post(
            "/api/ai/chat",
            headers=auth_headers,
            json={"message": "I spent some money today on groceries", "provider": "groq"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "how much it cost" in data["reply"]
        assert len(data["tool_executions"]) == 0


@pytest.mark.asyncio
async def test_ai_chat_tool_calling_execution(
    client: AsyncClient, auth_headers: dict, test_user: User
):
    """
    Test full tool calling loop: model issues a tool call (create_account),
    tool executes against the database, and model returns confirmation.
    """
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm

    # Turn 1: LLM calls create_account tool
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "create_account",
                "args": {
                    "name": "HDFC Savings",
                    "bank_name": "HDFC Bank",
                    "account_number": "9876543210",
                    "account_type": "savings",
                    "balance": 25000.0,
                },
                "id": "call_acc_1",
            }
        ],
    )

    # Turn 2: LLM receives ToolMessage and confirms creation to user
    final_reply_msg = AIMessage(
        content="I have created your HDFC Savings account with an initial balance of ₹25,000."
    )

    mock_llm.ainvoke = AsyncMock(side_effect=[tool_call_msg, final_reply_msg])

    with patch("app.services.ai_chat.ai_chat_service.get_chat_model") as mock_get_model:
        mock_get_model.return_value = (mock_llm, "groq", "llama-3.3-70b-versatile")

        response = await client.post(
            "/api/ai/chat",
            headers=auth_headers,
            json={
                "message": "Create a new savings account for HDFC Bank with 25000 balance and account number 9876543210",
                "provider": "groq",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "created your HDFC Savings account" in data["reply"]
        assert len(data["tool_executions"]) == 1

        exec_record = data["tool_executions"][0]
        assert exec_record["tool_name"] == "create_account"
        assert exec_record["success"] is True
        assert exec_record["result"]["name"] == "HDFC Savings"
        assert exec_record["result"]["balance"] == 25000.0

        # Verify account was indeed persisted to database
        saved_account = await Account.find_one(
            Account.user_id == test_user.id, Account.name == "HDFC Savings"
        )
        assert saved_account is not None
        assert saved_account.balance == 25000.0


@pytest.mark.asyncio
async def test_ai_chat_openrouter_provider_selection(
    client: AsyncClient, auth_headers: dict
):
    """Test using OpenRouter provider."""
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content="Response from OpenRouter Claude model.")
    )

    with patch("app.services.ai_chat.ai_chat_service.get_chat_model") as mock_get_model:
        mock_get_model.return_value = (
            mock_llm,
            "openrouter",
            "anthropic/claude-3.5-sonnet",
        )

        response = await client.post(
            "/api/ai/chat",
            headers=auth_headers,
            json={
                "message": "Give me financial advice",
                "provider": "openrouter",
                "model": "anthropic/claude-3.5-sonnet",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openrouter"
        assert data["model"] == "anthropic/claude-3.5-sonnet"
        assert "Response from OpenRouter" in data["reply"]
