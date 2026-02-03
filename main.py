from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from app.api.v1 import user_controller, execution_controller, pool_controller
from app.ui import ui_controller, ui_settings
from core.database import Base, db
from core.settings import get_settings
import logging

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="An Orchestration & User Pool Management for Certa Test Automation",
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user_controller.router, prefix="/api/v1")
app.include_router(execution_controller.router, prefix="/api/v1")
app.include_router(pool_controller.router, prefix="/api/v1")
# UI routes (HTMX + Jinja2)
app.include_router(ui_controller.router)
app.include_router(ui_settings.router)

# Templates
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Database: {settings.database_url.split('@')[1]}")
    Base.metadata.create_all(bind=db.engine)
    logger.info("Database tables created")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


from fastapi.responses import RedirectResponse


@app.get("/")
def root():
    # Redirect to the UI homepage
    return RedirectResponse(url='/ui')