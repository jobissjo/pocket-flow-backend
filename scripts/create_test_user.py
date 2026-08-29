import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import init_db
from app.core.security import get_password_hash
from app.models.user import User
from pymongo import AsyncMongoClient


async def create_test_user():
    print(f"Connecting to database: {settings.DATABASE_NAME}...")
    client = AsyncMongoClient(settings.MONGODB_URL)
    await init_db(client)

    test_email = "test@example.com"
    test_password = "Password123!"

    existing_user = await User.find_one(User.email == test_email)
    if existing_user:
        print(f"User '{test_email}' already exists. Updating password and ensuring active status...")
        existing_user.hashed_password = get_password_hash(test_password)
        existing_user.is_active = True
        existing_user.otp = None
        existing_user.otp_expires_at = None
        await existing_user.save()
        print("Updated existing user successfully.")
    else:
        new_user = User(
            email=test_email,
            full_name="Test User",
            mobile="9876543210",
            hashed_password=get_password_hash(test_password),
            is_active=True,
        )
        await new_user.insert()
        print(f"Created new active test user: {test_email}")

    print("\n" + "=" * 40)
    print("TEST LOGIN CREDENTIALS:")
    print(f"Email:    {test_email}")
    print(f"Password: {test_password}")
    print("=" * 40 + "\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(create_test_user())
