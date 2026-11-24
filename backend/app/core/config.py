import os
from pathlib import Path
from dotenv import load_dotenv

# Base backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")

class Settings:
    PROJECT_NAME: str = "CircularRoute"
    API_PREFIX: str = "/api"
    
    # LLM Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    
    # Embedding Settings
    NAME_EMBEDDING_MODEL: str = os.getenv("NAME_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    QDRANT_URL: str = os.getenv("QDRANT_URL") or os.getenv("qdrant_endpoint", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY") or os.getenv("qdrant_api_key", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "faculty")
    FACULTY_SEARCH_TOP_K: int = int(os.getenv("FACULTY_SEARCH_TOP_K", "5"))
    
    # Resend Settings
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "notifications@circularroute.aclclouds.online")
    RESEND_FROM_NAME: str = os.getenv("RESEND_FROM_NAME", "CircularRoute")
    
    # Paths
    BASE_DIR: Path = BACKEND_DIR
    CIRCULARS_DIR: Path = BACKEND_DIR / "circulars"
    FACULTY_FILE: Path = BACKEND_DIR / "faculty.json"
    
    # Limits
    MAX_FILE_SIZE_MB: int = 25
    SUPPORTED_EXTENSIONS: list[str] = [".pdf", ".png", ".jpg", ".jpeg", ".webp"]

    def reload(self):
        load_dotenv(BACKEND_DIR / ".env", override=True)
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
        self.RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
        self.RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "notifications@circularroute.aclclouds.online")
        self.RESEND_FROM_NAME = os.getenv("RESEND_FROM_NAME", "CircularRoute")
        self.QDRANT_URL = os.getenv("QDRANT_URL") or os.getenv("qdrant_endpoint", "")
        self.QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or os.getenv("qdrant_api_key", "")
        self.QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "faculty")
        self.FACULTY_SEARCH_TOP_K = int(os.getenv("FACULTY_SEARCH_TOP_K", "5"))

settings = Settings()

# Ensure directories exist
settings.CIRCULARS_DIR.mkdir(parents=True, exist_ok=True)
