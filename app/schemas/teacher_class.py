from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ClassCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Name of the class (e.g. Physics Grade 10 - Sec A)")
    description: Optional[str] = Field(None, max_length=1000, description="Optional class syllabus overview or description")
    subject_id: int = Field(..., description="ID of the syllabus subject linked to this class")


class ClassUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    enrollment_code: str
    teacher_id: int
    subject_id: int
    subject_name: Optional[str] = None
    is_active: bool
    enrolled_count: int = 0
    created_at: datetime
    updated_at: datetime


class EnrollStudentRequest(BaseModel):
    enrollment_code: Optional[str] = Field(None, description="Alphanumeric class enrollment code")
    student_email: Optional[str] = Field(None, description="Student email to directly invite/enroll (for teacher)")
    student_id: Optional[int] = Field(None, description="Student ID to enroll (for teacher)")


class EnrolledStudentItem(BaseModel):
    enrollment_id: int
    student_id: int
    student_name: str
    student_email: str
    enrolled_at: datetime
    is_active: bool
    overall_mastery: Optional[float] = None
    questions_attempted: int = 0
    accuracy_rate: Optional[float] = None


class StudentClassResponse(BaseModel):
    enrollment_id: int
    class_id: int
    class_name: str
    teacher_name: str
    subject_id: int
    subject_name: str
    enrolled_at: datetime
    is_active: bool


class ClassListResponse(BaseModel):
    total: int
    items: List[ClassResponse]
