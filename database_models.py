from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, TIMESTAMP, ForeignKey, Enum, JSON, DECIMAL, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum


Base = declarative_base()


# ============================================================
# ENUMS
# ============================================================


class JobType(str, enum.Enum):
    full_time = "full-time"
    part_time = "part-time"
    contract = "contract"
    internship = "internship"


class JobStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    draft = "draft"


class ApplicationStage(str, enum.Enum):
    applied = "applied"
    screening = "screening"
    aptitude = "aptitude"
    video_hr = "video_hr"
    final_interview = "final_interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"


class ExperienceLevel(str, enum.Enum):
    fresher = "fresher"
    one_to_three = "1-3 years"
    three_to_six = "3-6 years"
    six_plus = "6+ years"


class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class Priority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class UserRole(str, enum.Enum):
    candidate = "candidate"
    hr = "hr"
    admin = "admin"
    recruiter = "recruiter"
    hiring_manager = "hiring_manager"


# ============================================================
# USER TABLE (Updated for HR access requirements)
# ============================================================


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.candidate, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Additional fields for HR users (full access to application)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)

    # Relationships
    applications = relationship("Application", back_populates="candidate", foreign_keys="Application.candidate_id")
    posted_jobs = relationship("Job", back_populates="posted_by_user", foreign_keys="Job.posted_by")
    created_video_questions = relationship("VideoQuestion", back_populates="created_by_user", foreign_keys="VideoQuestion.created_by")
    video_reviews = relationship("VideoResponse", back_populates="hr_reviewer", foreign_keys="VideoResponse.hr_reviewed_by")


# ============================================================
# ENHANCED JOB TABLE (Updated ForeignKey for posted_by)
# ============================================================


class Job(Base):
    __tablename__ = "jobs"

    # Basic Info
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_code = Column(String(50), unique=True, index=True, nullable=True)
    title = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    location = Column(String(255), default="Hyderabad, India")
    type = Column(String(20), default="full-time")
    experience_level = Column(String(20), nullable=True)
    num_openings = Column(Integer, default=1)

    # Job Requirements
    required_skills = Column(JSON, nullable=True)  # ["Python", "React", "SQL"]
    preferred_skills = Column(JSON, nullable=True)  # ["AWS", "Docker"]
    education_requirement = Column(String(255), nullable=True)  # "B.Tech / MCA"
    minimum_academic_score = Column(String(50), nullable=True)  # "60%" or "6.0 CGPA"
    required_certifications = Column(JSON, nullable=True)  # ["AWS Certified"]
    tools_technologies = Column(JSON, nullable=True)  # ["Git", "Docker", "AWS"]

    # Job Description
    description = Column(Text, nullable=True)  # Job summary
    responsibilities = Column(Text, nullable=True)  # Detailed responsibilities
    key_deliverables = Column(Text, nullable=True)
    reporting_to = Column(String(100), nullable=True)
    keywords = Column(JSON, nullable=True)  # For matching algorithm

    # Compensation & Details
    salary_min = Column(DECIMAL(10, 2), nullable=True)
    salary_max = Column(DECIMAL(10, 2), nullable=True)
    salary_range_text = Column(String(100), nullable=True)  # "₹4-6 LPA"
    benefits = Column(Text, nullable=True)

    # Posting Details
    status = Column(String(20), default="open")
    priority = Column(String(20), default="medium")
    hiring_manager = Column(String(100), nullable=True)
    posted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    posted_at = Column(TIMESTAMP, server_default=func.now())
    application_deadline = Column(Date, nullable=True)

    # Relationships
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    job_video_questions = relationship("JobVideoQuestion", back_populates="job", cascade="all, delete-orphan")
    posted_by_user = relationship("User", back_populates="posted_jobs", foreign_keys=[posted_by])


# ============================================================
# ENHANCED CANDIDATE/APPLICATION TABLE (Updated ForeignKey)
# ============================================================


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # FK to users table

    # A. Personal Information
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    linkedin_profile = Column(String(500), nullable=True)
    portfolio_github = Column(String(500), nullable=True)
    resume_path = Column(String(500), nullable=True)

    # B. Education Details
    highest_qualification = Column(String(100), nullable=True)  # B.Tech, B.Sc, MBA
    specialization = Column(String(255), nullable=True)  # Computer Science
    university_college = Column(String(255), nullable=True)
    year_of_graduation = Column(Integer, nullable=True)
    academic_score = Column(String(50), nullable=True)  # "8.2 CGPA" or "75%"

    # C. Work Experience
    total_experience = Column(Float, default=0.0)  # In years
    current_company = Column(String(255), nullable=True)
    previous_companies = Column(JSON, nullable=True)  # Array of company names
    current_role = Column(String(255), nullable=True)
    key_responsibilities = Column(Text, nullable=True)
    achievements = Column(Text, nullable=True)
    notice_period = Column(String(50), nullable=True)  # "30 days"
    current_ctc = Column(DECIMAL(10, 2), nullable=True)
    expected_ctc = Column(DECIMAL(10, 2), nullable=True)

    # D. Skills & Projects
    technical_skills = Column(JSON, nullable=True)  # ["Java", "React", "SQL"]
    soft_skills = Column(JSON, nullable=True)  # ["Communication", "Leadership"]
    certifications = Column(JSON, nullable=True)  # ["AWS Certified Developer"]
    projects = Column(JSON, nullable=True)  # Array of project objects
    project_technologies = Column(JSON, nullable=True)  # ["Node.js", "MySQL"]
    resume_parsed_skills = Column(JSON, nullable=True)  # Auto-extracted skills

    # E. Other Information
    employment_type_preference = Column(String(50), nullable=True)  # "Full-time" / "Internship"
    availability_date = Column(Date, nullable=True)
    references = Column(Text, nullable=True)
    additional_comments = Column(Text, nullable=True)
    cover_letter = Column(Text, nullable=True)

    # Scoring & Matching
    resume_keywords = Column(JSON, nullable=True)
    resume_score = Column(DECIMAL(5, 2), nullable=True)  # Overall match score (0-100)
    skills_match_score = Column(DECIMAL(5, 2), nullable=True)  # 40% weight
    experience_match_score = Column(DECIMAL(5, 2), nullable=True)  # 25% weight
    education_match_score = Column(DECIMAL(5, 2), nullable=True)  # 15% weight
    certification_match_score = Column(DECIMAL(5, 2), nullable=True)  # 10% weight
    keywords_match_score = Column(DECIMAL(5, 2), nullable=True)  # 10% weight

    # Assessment Stages
    cat_theta = Column(DECIMAL(5, 2), nullable=True)
    cat_percentile = Column(DECIMAL(5, 2), nullable=True)
    cat_completed = Column(Boolean, default=False)
    video_hr_submitted = Column(Boolean, default=False)
    current_stage = Column(String(50), default="applied")

    # Timestamps
    applied_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # CAT Exam fields
    cat_exam_key = Column(String(50), nullable=True)
    cat_exam_email_sent = Column(Boolean, default=False)
    cat_exam_email_sent_at = Column(TIMESTAMP, nullable=True)

    # HR Video Interview fields
    hr_video_exam_key = Column(String(50), nullable=True)
    hr_video_exam_email_sent = Column(Boolean, default=False)
    hr_video_exam_email_sent_at = Column(TIMESTAMP, nullable=True)
    hr_exam_completed = Column(Boolean, default=False)

    # Relationships
    job = relationship("Job", back_populates="applications")
    candidate = relationship("User", back_populates="applications", foreign_keys=[candidate_id])
    video_responses = relationship("VideoResponse", back_populates="application", cascade="all, delete-orphan")
    cat_sessions = relationship("CATSession", back_populates="application", cascade="all, delete-orphan")


# ============================================================
# CAT ITEM TABLE
# ============================================================


class CATItem(Base):
    __tablename__ = "cat_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question = Column(Text, nullable=False)
    option_a = Column(Text, nullable=True)
    option_b = Column(Text, nullable=True)
    option_c = Column(Text, nullable=True)
    option_d = Column(Text, nullable=True)
    correct = Column(String(1), nullable=False)  # A, B, C, or D
    a = Column(Float, default=1.0)
    b = Column(Float, default=0.0)
    c = Column(Float, default=0.25)
    used_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    responses = relationship("CATItemResponse", back_populates="item", cascade="all, delete-orphan")


# ============================================================
# VIDEO QUESTION TABLE
# ============================================================


class VideoQuestion(Base):
    __tablename__ = "video_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    duration_seconds = Column(Integer, default=120)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    job_video_questions = relationship("JobVideoQuestion", back_populates="video_question", cascade="all, delete-orphan")
    created_by_user = relationship("User", back_populates="created_video_questions", foreign_keys=[created_by])


# ============================================================
# JOB VIDEO QUESTION JUNCTION TABLE
# ============================================================


class JobVideoQuestion(Base):
    __tablename__ = "job_video_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    video_question_id = Column(Integer, ForeignKey("video_questions.id"), nullable=False)
    display_order = Column(Integer, default=0)

    # Relationships
    job = relationship("Job", back_populates="job_video_questions")
    video_question = relationship("VideoQuestion", back_populates="job_video_questions")
    video_responses = relationship("VideoResponse", back_populates="job_video_question", cascade="all, delete-orphan")


# ============================================================
# VIDEO RESPONSE TABLE - UPDATED WITH AI SCORING
# ============================================================


class VideoResponse(Base):
    __tablename__ = "video_responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    job_video_question_id = Column(Integer, ForeignKey("job_video_questions.id"), nullable=False)

    # Video Details
    video_path = Column(String(500), nullable=False)
    duration_seconds = Column(Integer, nullable=True)

    # Question & User Response
    question_text = Column(Text, nullable=True)  # Store question for context
    user_answer_text = Column(Text, nullable=True)  # Transcription of user's response

    # AI Scoring (Automatic)
    ai_score = Column(DECIMAL(5, 2), nullable=True)  # 0-10 scale
    ai_feedback = Column(Text, nullable=True)  # Detailed AI feedback
    ai_evaluated_at = Column(TIMESTAMP, nullable=True)
    ai_evaluated = Column(Boolean, default=False)

    # HR/Admin Final Scoring (Manual Override)
    hr_score = Column(DECIMAL(5, 2), nullable=True)  # 0-10 scale
    hr_feedback = Column(Text, nullable=True)  # HR comments
    hr_reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin/HR user ID
    hr_reviewed_at = Column(TIMESTAMP, nullable=True)
    hr_reviewed = Column(Boolean, default=False)

    # Final Score (Determined by HR or AI if not reviewed)
    final_score = Column(DECIMAL(5, 2), nullable=True)  # 0-10 scale

    # Status Tracking
    submitted_at = Column(TIMESTAMP, server_default=func.now())
    reviewed = Column(Boolean, default=False)  # Keep for backward compatibility

    # Relationships
    application = relationship("Application", back_populates="video_responses")
    job_video_question = relationship("JobVideoQuestion", back_populates="video_responses")
    hr_reviewer = relationship("User", back_populates="video_reviews", foreign_keys=[hr_reviewed_by])


# ============================================================
# CAT SESSION TABLE
# ============================================================


class CATSession(Base):
    __tablename__ = "cat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)

    # Session Timing
    started_at = Column(TIMESTAMP, server_default=func.now())
    completed_at = Column(TIMESTAMP, nullable=True)

    # Current State During Test
    current_theta = Column(Float, default=0.0)
    current_se = Column(Float, nullable=True)
    num_items_administered = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Final Results
    final_theta = Column(Float, nullable=True)
    final_se = Column(Float, nullable=True)
    final_percentile = Column(Float, nullable=True)
    num_correct = Column(Integer, nullable=True)
    accuracy = Column(Float, nullable=True)

    # Relationships
    application = relationship("Application", back_populates="cat_sessions")
    responses = relationship("CATItemResponse", back_populates="session", cascade="all, delete-orphan")


# ============================================================
# CAT ITEM RESPONSE TABLE
# ============================================================


class CATItemResponse(Base):
    __tablename__ = "cat_item_responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("cat_sessions.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("cat_items.id"), nullable=False)

    # Response Details
    selected_option = Column(String(1), nullable=False)  # A, B, C, or D
    is_correct = Column(Boolean, nullable=False)
    response_time_seconds = Column(Integer, nullable=True)

    # Theta Updates
    theta_before = Column(Float, nullable=False)
    theta_after = Column(Float, nullable=False)
    se_after = Column(Float, nullable=False)

    # Timestamp
    responded_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    session = relationship("CATSession", back_populates="responses")
    item = relationship("CATItem", back_populates="responses")


# ============================================================
# HR VIDEO SESSION TABLE (Similar to CAT)
# ============================================================


class HRVideoSession(Base):
    __tablename__ = "hr_video_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    # Session Timing
    started_at = Column(TIMESTAMP, server_default=func.now())
    completed_at = Column(TIMESTAMP, nullable=True)

    # Session State
    is_active = Column(Boolean, default=True)
    total_questions = Column(Integer, nullable=True)
    questions_answered = Column(Integer, default=0)

    # Results Summary
    average_ai_score = Column(Float, nullable=True)
    min_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    pending_hr_review = Column(Integer, default=0)

    # Relationships
    # HR Video responses are directly linked via VideoResponse.application_id


# ============================================================
# AUDIT LOG TABLE (Optional - for tracking changes)
# ============================================================


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)  # "created_application", "submitted_video", etc.
    entity_type = Column(String(100), nullable=False)  # "Application", "VideoResponse", "CATSession"
    entity_id = Column(Integer, nullable=False)
    old_values = Column(JSON, nullable=True)  # Previous values
    new_values = Column(JSON, nullable=True)  # New values
    created_at = Column(TIMESTAMP, server_default=func.now())
