from fastapi import APIRouter, HTTPException
from typing import List
from ..services.faculty_service import faculty_service
from ..models.schemas import FacultyMember

router = APIRouter(prefix="", tags=["Faculty"])

@router.get("/faculties", response_model=List[FacultyMember])
def get_faculties():
    """Retrieve full faculty directory."""
    return faculty_service.get_all_faculties()

@router.get("/faculties/{faculty_id}", response_model=FacultyMember)
def get_faculty(faculty_id: str):
    """Retrieve individual faculty details by ID."""
    faculty = faculty_service.get_faculty_by_id(faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty
