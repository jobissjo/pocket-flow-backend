# Personal Financial Manager Backend

A production-ready, modular, and asynchronous backend for the **Personal Financial Manager** application built with **FastAPI**, **Beanie ODM**, **MongoDB**, **Pydantic v2**, and **Python 3.12**.

---

## 🏛 Architecture & Layer Responsibilities

The codebase follows a strict 4-tier separation of concerns:

```text
app/
├── main.py                     # Application entry point, lifespan, middleware & routes
├── core/
│   ├── config.py               # Pydantic Settings & environment variable loader
│   ├── database.py             # Motor async client, Beanie ODM init, default categories
│   ├── dependencies.py         # Authenticated user JWT dependency (get_current_user)
│   └── security.py             # Bcrypt password hashing, JWT tokens, and OTP generation
│
├── models/                     # Beanie ODM MongoDB Document Models
│   ├── user.py                 # User document
│   ├── account.py              # Bank/Cash Account document
│   ├── credit_card.py          # Credit Card document
│   ├── category.py             # System & custom categories
│   ├── transaction.py          # Income & Expense transactions
│   └── emi.py                  # EMI payment tracker
│
├── schemas/                    # Pydantic validation & serialization schemas
│   ├── auth.py                 # Auth, OTP, login, password recovery schemas
│   ├── user.py                 # Profile schemas
│   ├── account.py              # Account schemas (with number masking)
│   ├── credit_card.py          # Credit card schemas (with available limit)
│   ├── category.py             # Category schemas
│   ├── transaction.py          # Transaction schemas & filter parameters
│   ├── emi.py                  # EMI schemas & mark-paid response
│   ├── dashboard.py            # Summary, time-series, and breakdown analytics
│   └── common.py               # Pagination & generic response schemas
│
├── repositories/               # Pure MongoDB / Beanie async queries scoped to user_id
│   ├── base.py                 # Generic CRUD repository
│   ├── user.py                 # User repository
│   ├── account.py              # Account repository
│   ├── credit_card.py          # Credit Card repository
│   ├── category.py             # Category repository
│   ├── transaction.py          # Transaction repository (filtering, aggregation)
│   └── emi.py                  # EMI repository
│
├── services/                   # Business logic, multi-repo orchestration, balance rules
│   ├── auth.py                 # Registration, OTP verification, JWT login
│   ├── user.py                 # Profile & cascading deletion
│   ├── account.py              # Account management
│   ├── credit_card.py          # Credit card operations & limit calculation
│   ├── category.py             # Category permissions & system protection
│   ├── transaction.py          # Transaction lifecycle & automatic account/card balance adjustments
│   ├── emi.py                  # EMI schedule calculation & atomic mark-paid
│   └── dashboard.py            # Financial summary & chart analytics aggregation
│
└── routes/                     # FastAPI APIRouters (HTTP handling, validation, dependencies)
    ├── auth.py                 # /api/auth
    ├── users.py                # /api/users
    ├── accounts.py             # /api/accounts
    ├── credit_cards.py         # /api/credit-cards
    ├── categories.py           # /api/categories
    ├── transactions.py         # /api/transactions
    ├── emi.py                  # /api/emi
    └── dashboard.py            # /api/dashboard
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- MongoDB instance running locally (e.g. `mongodb://localhost:27017`) or a MongoDB Atlas URI

### 2. Setup Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (cmd/PowerShell):
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and customize as needed:
```bash
cp .env.example .env
```

Key environment variables:
```env
PROJECT_NAME="Personal Financial Manager"
API_V1_STR="/api"
MONGODB_URL="mongodb://localhost:27017"
DATABASE_NAME="pocket_flow_db"
JWT_SECRET_KEY="your-secure-secret-key"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
OTP_EXPIRE_MINUTES=10
CORS_ORIGINS="http://localhost:3000,http://localhost:5173,http://localhost:8000"
```

### 4. Running the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser for the interactive Swagger OpenAPI documentation.

---

## 🧪 Running Automated Tests
```bash
pytest -v
```

---

## 📡 API Reference Overview

### 🔐 Authentication (`/api/auth`)
- `POST /api/auth/register` — Register user & receive verification OTP
- `POST /api/auth/verify-otp` — Verify OTP, activate account & obtain JWT
- `POST /api/auth/login` — Login with credentials & obtain JWT
- `POST /api/auth/resend-otp` — Resend verification OTP
- `POST /api/auth/forgot-password` — Request password reset OTP
- `POST /api/auth/reset-password` — Reset password using OTP
- `GET  /api/auth/me` — Retrieve current user profile

### 👤 Users (`/api/users`)
- `GET    /api/users/me` — Get profile details
- `PATCH  /api/users/me` — Update full name / mobile
- `DELETE /api/users/me` — Delete account and user data

### 🏦 Accounts (`/api/accounts`)
- `POST   /api/accounts` — Create bank, cash, salary, or savings account
- `GET    /api/accounts` — List user accounts (with masked account numbers)
- `GET    /api/accounts/{account_id}` — Get single account
- `PATCH  /api/accounts/{account_id}` — Update account
- `DELETE /api/accounts/{account_id}` — Delete account

### 💳 Credit Cards (`/api/credit-cards`)
- `POST   /api/credit-cards` — Add credit card with limit and billing cycle
- `GET    /api/credit-cards` — List credit cards (includes computed `available_limit`)
- `GET    /api/credit-cards/{card_id}` — Get credit card details
- `PATCH  /api/credit-cards/{card_id}` — Update credit card
- `DELETE /api/credit-cards/{card_id}` — Delete credit card

### 🏷 Categories (`/api/categories`)
- `POST   /api/categories` — Create custom category
- `GET    /api/categories` — List system & custom categories (optional `?type=income|expense`)
- `GET    /api/categories/{category_id}` — Get category
- `PATCH  /api/categories/{category_id}` — Update custom category (system categories protected)
- `DELETE /api/categories/{category_id}` — Delete custom category (system categories protected)

### 💸 Transactions (`/api/transactions`)
- `POST   /api/transactions` — Create income/expense (automatically updates bank balance or credit card outstanding)
- `GET    /api/transactions` — Paginated transactions with rich filters:
  - `page`, `limit`, `search`, `type`, `category`, `account`, `credit_card`, `start_date`, `end_date`, `min_amount`, `max_amount`, `sort_by`, `sort_order`
- `GET    /api/transactions/{transaction_id}` — Get transaction details
- `PATCH  /api/transactions/{transaction_id}` — Update transaction (recalculates balances)
- `DELETE /api/transactions/{transaction_id}` — Delete transaction (reverses financial effects)

### 📅 EMI Tracker (`/api/emi`)
- `POST   /api/emi` — Create EMI plan
- `GET    /api/emi` — List EMIs with computed `remaining_installments` and `next_payment_date`
- `GET    /api/emi/{emi_id}` — Get EMI details
- `PATCH  /api/emi/{emi_id}` — Update EMI
- `DELETE /api/emi/{emi_id}` — Delete EMI
- `POST   /api/emi/{emi_id}/mark-paid` — Mark next installment paid (adjusts account/card balance and updates status to completed when done)

### 📊 Dashboard Analytics (`/api/dashboard`)
- `GET /api/dashboard/summary` — Total balance, total income, total expenses, credit card outstanding, net savings, savings percentage
- `GET /api/dashboard/analytics` — Income vs Expense monthly time series, and category-wise income & expense breakdowns
- `GET /api/dashboard/recent-transactions` — Quick view of latest transactions
- `GET /api/dashboard/upcoming-emi` — Active EMIs sorted by upcoming payment due date
