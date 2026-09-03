from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai_chat import ChatRequest, ChatResponse
from app.services.ai_chat import ai_chat_service

router = APIRouter(prefix="/ai", tags=["AI Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with PocketFlow AI Financial Assistant",
    description="Conversational personal financial assistant that can check balances, record transactions, manage EMIs, analyze spending, and ask clarifying questions if inputs are incomplete.",
)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    return await ai_chat_service.chat(user=current_user, request=request)
