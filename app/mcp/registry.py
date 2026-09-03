import inspect
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, get_args, get_origin
from fastapi import HTTPException
from pydantic import BaseModel

from app.mcp.context import user_context


def _python_type_to_json_schema(py_type: Any) -> dict:
    """Converts a Python type annotation to JSON schema property definition."""
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is None:
        if py_type is str:
            return {"type": "string"}
        elif py_type is int:
            return {"type": "integer"}
        elif py_type is float:
            return {"type": "number"}
        elif py_type is bool:
            return {"type": "boolean"}
        elif isinstance(py_type, type) and issubclass(py_type, Enum):
            return {
                "type": "string",
                "enum": [e.value for e in py_type],
                "description": f"Allowed values: {[e.value for e in py_type]}",
            }
        elif isinstance(py_type, type) and issubclass(py_type, BaseModel):
            return py_type.model_json_schema()
        else:
            return {"type": "string"}

    # Handle Optional[T] / Union[T, None]
    if origin is type(Optional[int]) or (hasattr(origin, "__name__") and origin.__name__ == "Union"):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            schema = _python_type_to_json_schema(non_none[0])
            schema["nullable"] = True
            return schema

    # Handle List[T]
    if origin is list or origin is List:
        item_type = args[0] if args else str
        return {
            "type": "array",
            "items": _python_type_to_json_schema(item_type),
        }

    return {"type": "string"}


def _build_parameters_schema(func: Callable) -> dict:
    """Extracts JSON Schema parameters definition from function signature."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    
    properties = {}
    required = []

    for name, param in sig.parameters.items():
        # Exclude internal/reserved parameters if any
        annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
        prop_schema = _python_type_to_json_schema(annotation)

        # Infer description from docstring if available (simple heuristic)
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            if param.default is not None:
                prop_schema["default"] = param.default

        properties[name] = prop_schema

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _to_json_friendly(val: Any) -> Any:
    """Converts Pydantic models or datetimes into JSON-serializable primitives."""
    if isinstance(val, BaseModel):
        return val.model_dump(mode="json")
    elif isinstance(val, list):
        return [_to_json_friendly(item) for item in val]
    elif isinstance(val, dict):
        return {k: _to_json_friendly(v) for k, v in val.items()}
    return val


@dataclass
class RegisteredTool:
    name: str
    description: str
    category: str
    func: Callable
    parameters_schema: dict = field(default_factory=dict)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "general",
    ):
        """Decorator to register a tool in the registry."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or inspect.getdoc(func) or f"Execute {tool_name}"
            schema = _build_parameters_schema(func)

            registered = RegisteredTool(
                name=tool_name,
                description=tool_desc.strip(),
                category=category,
                func=func,
                parameters_schema=schema,
            )
            self._tools[tool_name] = registered
            return func

        return decorator

    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[RegisteredTool]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def get_openai_tools(self, category: Optional[str] = None) -> List[dict]:
        """Returns tool definitions formatted for OpenAI / generic function calling."""
        tools = self.list_tools(category)
        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters_schema,
                },
            })
        return openai_tools

    def get_anthropic_tools(self, category: Optional[str] = None) -> List[dict]:
        """Returns tool definitions formatted for Anthropic Claude function calling."""
        tools = self.list_tools(category)
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters_schema,
            }
            for t in tools
        ]

    def get_tool_schemas(self) -> Dict[str, dict]:
        """Returns a mapping of tool name to schema."""
        return {
            t.name: {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        }

    async def execute_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a registered tool by name with arguments.
        Handles context setting, exceptions, and serializes response.
        """
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' not found. Available tools: {list(self._tools.keys())}",
            }

        args = arguments.copy() if arguments else {}

        # If user_id is passed and function has user_id param but not passed in args, inject it
        sig = inspect.signature(tool.func)
        if "user_id" in sig.parameters and "user_id" not in args and user_id:
            args["user_id"] = user_id

        try:
            # If user_id is provided, also set the contextvar for inner services
            if user_id:
                with user_context(user_id):
                    res = await tool.func(**args)
            else:
                res = await tool.func(**args)

            return {
                "success": True,
                "data": _to_json_friendly(res),
            }
        except HTTPException as he:
            return {
                "success": False,
                "error": he.detail,
                "status_code": he.status_code,
            }
        except ValueError as ve:
            return {
                "success": False,
                "error": str(ve),
            }
        except Exception as ex:
            return {
                "success": False,
                "error": f"Internal execution error: {str(ex)}",
            }


tool_registry = ToolRegistry()
register_tool = tool_registry.register
execute_tool = tool_registry.execute_tool
get_all_tools = tool_registry.list_tools
get_openai_tools = tool_registry.get_openai_tools
get_tool_schemas = tool_registry.get_tool_schemas
