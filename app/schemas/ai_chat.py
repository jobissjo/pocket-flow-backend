from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="Message author role")
    content: str = Field(..., description="Text content of the message")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Current user input text")
    history: Optional[List[ChatMessage]] = Field(
        default_factory=list,
        description="Previous conversation turns for context memory",
    )


class ToolExecutionRecord(BaseModel):
    tool_name: str = Field(..., description="Name of the executed MCP tool")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Any] = Field(None, description="Result payload if succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant's text response")
    tool_executions: List[ToolExecutionRecord] = Field(
        default_factory=list,
        description="List of tools called and executed during this turn",
    )
    provider: str = Field(..., description="AI provider that processed the request")
    model: str = Field(..., description="Model identifier used for generation")
