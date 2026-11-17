import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..core.config import settings, BACKEND_DIR

router = APIRouter(prefix="/system", tags=["System"])

class SystemConfig(BaseModel):
    groq_configured: bool
    groq_model: str
    resend_configured: bool
    resend_from_email: str
    resend_from_name: str
    embedding_model: str

class UpdateConfigRequest(BaseModel):
    groq_api_key: Optional[str] = None
    resend_api_key: Optional[str] = None
    resend_from_email: Optional[str] = None

@router.get("/config", response_model=SystemConfig)
def get_system_config():
    return SystemConfig(
        groq_configured=bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key"),
        groq_model=settings.GROQ_MODEL,
        resend_configured=bool(settings.RESEND_API_KEY and settings.RESEND_API_KEY != "your_resend_api_key"),
        resend_from_email=settings.RESEND_FROM_EMAIL,
        resend_from_name=settings.RESEND_FROM_NAME,
        embedding_model=settings.NAME_EMBEDDING_MODEL
    )

@router.post("/config")
def update_system_config(req: UpdateConfigRequest):
    env_file = BACKEND_DIR / ".env"
    existing_lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
            
    updates = {}
    if req.groq_api_key is not None:
        updates["GROQ_API_KEY"] = req.groq_api_key.strip()
    if req.resend_api_key is not None:
        updates["RESEND_API_KEY"] = req.resend_api_key.strip()
    if req.resend_from_email is not None:
        updates["RESEND_FROM_EMAIL"] = req.resend_from_email.strip()

    new_lines = []
    found_keys = set()
    for line in existing_lines:
        matched = False
        for k, v in updates.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                found_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in found_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    settings.reload()
    return {"message": "Configuration updated successfully", "config": get_system_config()}
