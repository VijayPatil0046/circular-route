import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.circulars import router as circulars_router
from .api.faculty import router as faculty_router
from .api.system import router as system_router
from .services.storage_service import storage_service
from .services.faculty_service import faculty_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("circularroute")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered institutional circular processing and automated faculty email notification application.",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(circulars_router, prefix="/api")
app.include_router(faculty_router, prefix="/api")
app.include_router(system_router, prefix="/api")

@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing CircularRoute backend services...")
    storage_service.circulars_dir.mkdir(parents=True, exist_ok=True)
    faculty_members = faculty_service.get_all_faculties()
    logger.info(f"Loaded {len(faculty_members)} faculty members into directory cache.")
