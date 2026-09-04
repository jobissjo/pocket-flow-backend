from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.accounts import router as accounts_router
from app.routes.credit_cards import router as credit_cards_router
from app.routes.categories import router as categories_router
from app.routes.transactions import router as transactions_router
from app.routes.emi import router as emi_router
from app.routes.dashboard import router as dashboard_router
from app.routes.ai_chat import router as ai_chat_router
from app.routes.monthly_plan import router as monthly_plan_router
from app.transaction_import import transaction_import_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(accounts_router)
api_router.include_router(credit_cards_router)
api_router.include_router(categories_router)
api_router.include_router(transactions_router)
api_router.include_router(emi_router)
api_router.include_router(dashboard_router)
api_router.include_router(ai_chat_router)
api_router.include_router(monthly_plan_router)
api_router.include_router(transaction_import_router)

__all__ = ["api_router"]
