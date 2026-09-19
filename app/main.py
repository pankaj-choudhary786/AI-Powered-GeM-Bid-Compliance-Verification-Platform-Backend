# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base
from app.api.routes import auth, tenders, submissions

# Import models so SQLAlchemy knows they exist and can build the tables
from app.db import models

# 1. Create the database tables in SQLite (tender_platform.db)
# Note: In a production environment, Alembic handles this. For local dev, this is fail-safe.
Base.metadata.create_all(bind=engine)

# 2. Initialize the FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for SIH PS 26100 - Tender Compliance Verification Platform",
    docs_url="/docs",      # Swagger UI accessible here
    redoc_url="/redoc"     # ReDoc accessible here
)

# 3. Configure CORS (Cross-Origin Resource Sharing)
# Safely split the comma-separated string from .env into a Python list
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allows all headers (Authorization, Content-Type, etc.)
)

# 4. Phase 2 Base Route (Health Check)
@app.get("/api/health", tags=["System Health"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "connected"
    }

# (In Phase 3 and 4, we will register our auth, tender, and officer routers down here)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(tenders.router, prefix="/api/tenders", tags=["Tenders"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["Submissions"])