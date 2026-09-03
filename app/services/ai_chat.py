import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.mcp.registry import execute_tool, get_openai_tools
from app.models.user import User
from app.schemas.ai_chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ToolExecutionRecord,
)

logger = logging.getLogger("pocketflow.ai_chat")


class AIChatService:
    def _build_system_prompt(self, user: User) -> str:
        current_time_str = datetime.now().strftime("%Y-%m-%d %A, %H:%M")
        return f"""You are PocketFlow AI, an intelligent, friendly, and reliable personal finance assistant for PocketFlow.
You assist the user in managing their personal finances, including bank accounts, credit cards, income, expenses, EMIs/loans, and financial analytics.

### Current Context:
- User Name: {user.full_name or 'Valued User'}
- User Email: {user.email}
- Current Date & Time: {current_time_str}

### Critical Guidelines:
1. **Clarify Missing Information (Crucial)**:
   - If the user asks to perform an action (such as adding an expense/income, creating a bank account, setting up an EMI, or updating something) but has NOT provided all essential details (e.g. missing amount, category, account/card, or description), DO NOT guess, DO NOT invent fake data, and DO NOT call tools with placeholder values.
   - Instead, ask a polite, direct, and clear clarifying question to collect the missing details before proceeding.
   - Example: If the user says "Add an expense for lunch", reply: "How much did lunch cost, and which bank account or credit card did you pay with?"

2. **Simple, Unconfusing Answers**:
   - Keep your responses direct, helpful, and free of technical jargon.
   - Never expose raw MongoDB IDs, JSON schemas, internal error stacktraces, or database terminology to the user.
   - Present amounts formatted clearly (e.g. ₹500 or $500 depending on context).

3. **Confirm Actions Clearly**:
   - Whenever an operation is executed via tools (e.g. transaction created, balance updated, EMI installment marked as paid), confirm it clearly with relevant details (e.g., "Added an expense of ₹450 for Lunch. Your HDFC account balance is now ₹12,550.").

4. **Financial Inquiries & Insights**:
   - When asked about total balances, recent transactions, spending breakdowns, or upcoming bills, use the appropriate tools (`get_dashboard_summary`, `list_accounts`, `list_credit_cards`, `get_financial_analytics`, `get_upcoming_emis`) to fetch accurate live data and summarize it concisely for the user.
"""

    def get_chat_model(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Tuple[BaseChatModel, str, str]:
        """
        Initializes and returns the LangChain chat model based on provider and model settings.
        Returns: (model_instance, active_provider, active_model_name)
        """
        active_provider = (provider or settings.AI_PROVIDER).lower()

        if active_provider == "groq":
            if not settings.GROQ_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Groq AI is selected, but GROQ_API_KEY is not configured in environment settings.",
                )
            target_model = model_name or settings.GROQ_MODEL
            llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model=target_model,
                temperature=0.1,
            )
            return llm, "groq", target_model

        elif active_provider == "openrouter":
            if not settings.OPENROUTER_API_KEY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenRouter AI is selected, but OPENROUTER_API_KEY is not configured in environment settings.",
                )
            target_model = model_name or settings.OPENROUTER_MODEL
            llm = ChatOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                model=target_model,
                temperature=0.1,
                default_headers={
                    "HTTP-Referer": "https://pocketflow.app",
                    "X-Title": "PocketFlow Personal Finance",
                },
            )
            return llm, "openrouter", target_model

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported AI provider: '{active_provider}'. Supported providers are 'groq' and 'openrouter'.",
            )

    async def chat(self, user: User, request: ChatRequest) -> ChatResponse:
        """
        Processes a user chat message with conversation history, performs tool calling
        via LangChain against registered PocketFlow MCP tools, and returns the response.
        """
        llm, active_provider, active_model = self.get_chat_model(
            provider=request.provider,
            model_name=request.model,
        )

        # 1. Prepare system message and history
        messages: List[BaseMessage] = [
            SystemMessage(content=self._build_system_prompt(user))
        ]

        if request.history:
            for turn in request.history:
                if turn.role == "user":
                    messages.append(HumanMessage(content=turn.content))
                elif turn.role == "assistant":
                    messages.append(AIMessage(content=turn.content))
                elif turn.role == "system":
                    messages.append(SystemMessage(content=turn.content))

        # Add current user prompt
        messages.append(HumanMessage(content=request.message))

        # 2. Bind tools
        tools_definitions = get_openai_tools()
        llm_with_tools = llm.bind_tools(tools_definitions)

        tool_executions: List[ToolExecutionRecord] = []
        max_tool_iterations = 5

        for _ in range(max_tool_iterations):
            try:
                response = await llm_with_tools.ainvoke(messages)
            except Exception as e:
                logger.error("LLM invocation error: %s", str(e), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Error communicating with AI provider ({active_provider}): {str(e)}",
                )

            messages.append(response)

            # Check if model called any tools
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                # No more tools called, final answer reached
                break

            # Execute all tool calls
            for tc in tool_calls:
                tool_name = tc.get("name")
                tool_args = tc.get("args") or {}
                tool_id = tc.get("id") or f"call_{tool_name}"

                logger.info(
                    "Executing tool '%s' for user '%s' with args %s",
                    tool_name,
                    user.id,
                    tool_args,
                )

                exec_result = await execute_tool(
                    name=tool_name,
                    arguments=tool_args,
                    user_id=str(user.id),
                )

                tool_executions.append(
                    ToolExecutionRecord(
                        tool_name=tool_name,
                        arguments=tool_args,
                        success=exec_result.get("success", False),
                        result=exec_result.get("data"),
                        error=exec_result.get("error"),
                    )
                )

                # Feed execution result back to the model as ToolMessage
                tool_content = json.dumps(exec_result, default=str)
                messages.append(ToolMessage(content=tool_content, tool_call_id=tool_id))

        # Extract final response text
        final_content = response.content
        if isinstance(final_content, list):
            reply_text = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in final_content
            )
        else:
            reply_text = str(final_content or "")

        return ChatResponse(
            reply=reply_text.strip(),
            tool_executions=tool_executions,
            provider=active_provider,
            model=active_model,
        )


ai_chat_service = AIChatService()
