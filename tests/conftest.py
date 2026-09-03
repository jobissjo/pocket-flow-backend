import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from beanie import init_beanie
from mongomock.database import Database
from mongomock_motor import AsyncMongoMockClient

from mongomock_motor import AsyncMongoMockCollection

# Patch mongomock.database.Database.list_collection_names for newer Beanie/PyMongo kwargs
_orig_list_collection_names = Database.list_collection_names

def _patched_list_collection_names(self, *args, **kwargs):
    kwargs.pop("authorizedCollections", None)
    kwargs.pop("nameOnly", None)
    return _orig_list_collection_names(self, *args, **kwargs)

Database.list_collection_names = _patched_list_collection_names

_orig_aggregate = AsyncMongoMockCollection.aggregate

async def _patched_aggregate(self, *args, **kwargs):
    res = _orig_aggregate(self, *args, **kwargs)
    return res

AsyncMongoMockCollection.aggregate = _patched_aggregate

from app.core.database import DEFAULT_SYSTEM_CATEGORIES
from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.emi import EMI
from app.models.transaction import Transaction
from app.models.transaction_import import TransactionImport
from app.models.user import User
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


from app.core.config import settings


@pytest_asyncio.fixture(scope="function", autouse=True)
async def init_mock_db():
    """Initialize mock MongoDB and Beanie ODM for clean testing."""
    # Ensure real email sending is disabled during tests to prevent delivery failures
    orig_smtp = settings.SMTP_ENABLED
    settings.SMTP_ENABLED = False

    client = AsyncMongoMockClient()
    db = client["test_pocket_flow_db"]
    
    await init_beanie(
        database=db,
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

    # Seed system categories
    system_cats = [Category(**cat) for cat in DEFAULT_SYSTEM_CATEGORIES]
    await Category.insert_many(system_cats)

    yield db

    # Clean collections after each test
    await User.delete_all()
    await Account.delete_all()
    await CreditCard.delete_all()
    await Category.delete_all()
    await Transaction.delete_all()
    await EMI.delete_all()
    await TransactionImport.delete_all()
    settings.SMTP_ENABLED = orig_smtp


@pytest_asyncio.fixture(scope="function")
async def client():
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client: AsyncClient):
    """Register and verify a test user, returning authorization headers."""
    # 1. Register
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "testuser@example.com",
            "mobile": "9876543210",
            "full_name": "Test User",
            "password": "Password123!",
        },
    )
    assert reg_resp.status_code == 201
    otp = reg_resp.json().get("otp_preview")

    # 2. Verify OTP
    ver_resp = await client.post(
        "/api/auth/verify-otp",
        json={
            "email": "testuser@example.com",
            "otp": otp,
        },
    )
    assert ver_resp.status_code == 200
    token = ver_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def second_auth_headers(client: AsyncClient):
    """Register and verify a second test user for cross-user isolation tests."""
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "seconduser@example.com",
            "mobile": "9876543211",
            "full_name": "Second User",
            "password": "Password123!",
        },
    )
    assert reg_resp.status_code == 201
    otp = reg_resp.json().get("otp_preview")

    ver_resp = await client.post(
        "/api/auth/verify-otp",
        json={
            "email": "seconduser@example.com",
            "otp": otp,
        },
    )
    assert ver_resp.status_code == 200
    token = ver_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
