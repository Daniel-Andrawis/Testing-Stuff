import uuid
from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Column, String, Boolean, Integer, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship

from app.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, default="")
    education = Column(SQLiteJSON, default=dict)
    certifications = Column(SQLiteJSON, default=list)
    skills = Column(SQLiteJSON, default=list)
    experience_keywords = Column(SQLiteJSON, default=list)
    work_history = Column(SQLiteJSON, default=list)  # [{title, company, duration, description}]
    years_experience = Column(Integer, default=0)
    languages = Column(SQLiteJSON, default=list)
    clearance_eligible = Column(Boolean, default=False)
    target_companies = Column(SQLiteJSON, default=list)
    original_resume_filename = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)
    external_id = Column(String, default="")
    title = Column(String, nullable=False)
    organization = Column(String, default="")
    department = Column(String, default="")
    location = Column(String, default="")
    salary_min = Column(String, default="N/A")
    salary_max = Column(String, default="N/A")
    grade = Column(String, default="N/A")
    description = Column(Text, default="")
    qualifications = Column(Text, default="")
    url = Column(String, unique=True, nullable=False)
    open_date = Column(String, default="N/A")
    close_date = Column(String, default="N/A")
    fetched_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    total_score = Column(Float, nullable=False)
    breakdown = Column(SQLiteJSON, default=dict)
    matched_skills = Column(SQLiteJSON, default=list)
    matched_keywords = Column(SQLiteJSON, default=list)
    computed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job"),
    )
