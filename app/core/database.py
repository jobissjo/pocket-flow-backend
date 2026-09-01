import logging
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.models.user import User
from app.models.account import Account
from app.models.credit_card import CreditCard
from app.models.category import Category, CategoryType
from app.models.transaction import Transaction
from app.models.emi import EMI
from app.models.transaction_import import TransactionImport

logger = logging.getLogger(__name__)

# Default system categories to seed
DEFAULT_SYSTEM_CATEGORIES = [
    # Expense categories
    {"name": "Food & Dining", "type": CategoryType.EXPENSE, "icon": "utensils", "is_system": True},
    {"name": "Shopping", "type": CategoryType.EXPENSE, "icon": "shopping-bag", "is_system": True},
    {"name": "Housing & Rent", "type": CategoryType.EXPENSE, "icon": "home", "is_system": True},
    {"name": "Transportation", "type": CategoryType.EXPENSE, "icon": "car", "is_system": True},
    {"name": "Utilities & Bills", "type": CategoryType.EXPENSE, "icon": "zap", "is_system": True},
    {"name": "Entertainment", "type": CategoryType.EXPENSE, "icon": "film", "is_system": True},
    {"name": "Health & Medical", "type": CategoryType.EXPENSE, "icon": "activity", "is_system": True},
    {"name": "Education", "type": CategoryType.EXPENSE, "icon": "book-open", "is_system": True},
    {"name": "EMI & Loans", "type": CategoryType.EXPENSE, "icon": "credit-card", "is_system": True},
    {"name": "Personal Care", "type": CategoryType.EXPENSE, "icon": "smile", "is_system": True},
    {"name": "Groceries", "type": CategoryType.EXPENSE, "icon": "shopping-cart", "is_system": True},
    {"name": "Travel", "type": CategoryType.EXPENSE, "icon": "plane", "is_system": True},
    {"name": "Other Expense", "type": CategoryType.EXPENSE, "icon": "more-horizontal", "is_system": True},
    # Income categories
    {"name": "Salary", "type": CategoryType.INCOME, "icon": "briefcase", "is_system": True},
    {"name": "Freelance", "type": CategoryType.INCOME, "icon": "laptop", "is_system": True},
    {"name": "Investment Returns", "type": CategoryType.INCOME, "icon": "trending-up", "is_system": True},
    {"name": "Rental Income", "type": CategoryType.INCOME, "icon": "key", "is_system": True},
    {"name": "Gifts & Grants", "type": CategoryType.INCOME, "icon": "gift", "is_system": True},
    {"name": "Other Income", "type": CategoryType.INCOME, "icon": "dollar-sign", "is_system": True},
]


async def seed_system_categories() -> None:
    """Seed initial system categories if they do not exist."""
    try:
        count = await Category.find(Category.is_system == True).count()
        if count == 0:
            categories_to_insert = [
                Category(**cat) for cat in DEFAULT_SYSTEM_CATEGORIES
            ]
            await Category.insert_many(categories_to_insert)
            logger.info("Successfully seeded default system categories.")
    except Exception as e:
        logger.error(f"Error seeding system categories: {e}")


async def init_db(client: AsyncMongoClient = None) -> AsyncMongoClient:
    """Initialize MongoDB connection and Beanie ODM."""
    if client is None:
        client = AsyncMongoClient(settings.MONGODB_URL)

    database = client[settings.DATABASE_NAME]

    await init_beanie(
        database=database,
        document_models=[
            User,
            Account,
            CreditCard,
            Category,
            Transaction,
            EMI,
            TransactionImport,
        ],
    )
    logger.info(f"Connected to MongoDB database: '{settings.DATABASE_NAME}' and initialized Beanie.")

    # Seed default system categories
    await seed_system_categories()

    return client
