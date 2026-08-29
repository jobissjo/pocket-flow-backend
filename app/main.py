import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.core.database import init_db
from app.routes import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB and Beanie
    logger.info("Initializing MongoDB and Beanie ODM...")
    client: AsyncMongoClient = AsyncMongoClient(settings.MONGODB_URL)
    await init_db(client)
    app.state.db_client = client
    logger.info("Application startup completed.")
    yield
    # Shutdown: Close database connection
    logger.info("Closing MongoDB connection...")
    if hasattr(app.state, "db_client"):
        app.state.db_client.close()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-ready REST API for the Personal Financial Manager application, built with FastAPI, Beanie ODM, and MongoDB.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.encoders import jsonable_encoder


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Invalid input")
        error_messages.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "detail": error_messages[0] if error_messages else "Validation error",
            "errors": errors,
        }),
    )


# Health & Info Endpoints
@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENVIRONMENT,
    }


# Include all API routes
app.include_router(api_router, prefix=settings.API_V1_STR)
