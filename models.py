from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal


# ============================================================
# Shared Config
# ============================================================


class ORMModel(BaseModel):
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None,
            datetime: lambda v: v.isoformat() if v is not None else None,
            date: lambda v: v.isoformat() if v is not None else None,
        }


# ============================================================
# Job Schemas
# ============================================================


class JobBase(ORMModel):
    job_code: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = "Hyderabad, India"
    type: Optional[str] = "full-time"
    experience_level: Optional[str] = None
    num_openings: Optional[int] = 1
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    education_requirement: Optional[str] = None
    minimum_academic_score: Optional[str] = None
    required_certifications: Optional[List[str]] = None
    tools_technologies: Optional[List[str]] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    key_deliverables: Optional[str] = None
    reporting_to: Optional[str] = None
    keywords: Optional[List[str]] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    salary_range_text: Optional[str] = None
    benefits: Optional[str] = None
    status: Optional[str] = "open"
    priority: Optional[str] = "medium"
    hiring_manager: Optional[str] = None
    posted_by: Optional[int] = None
    application_deadline: Optional[date] = None


class JobCreate(JobBase):
    title: str


class JobUpdate(JobBase):
    pass


class JobResponse(JobBase):
    id: int
    posted_at: Optional[datetime] = None


# ============================================================
# Application Schemas (PUBLIC submission; candidate_id OPTIONAL)
# ============================================================


class ApplicationBase(ORMModel):
    job_id: Optional[int] = None
    candidate_id: Optional[int] = None  # OPTIONAL for public applications
    
    # A. Personal Information
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    linkedin_profile: Optional[str] = None
    portfolio_github: Optional[str] = None
    resume_path: Optional[str] = None

    # B. Education
    highest_qualification: Optional[str] = None
    specialization: Optional[str] = None
    university_college: Optional[str] = None
    year_of_graduation: Optional[int] = None
    academic_score: Optional[str] = None

    # C. Experience
    total_experience: Optional[float] = 0.0
    current_company: Optional[str] = None
    previous_companies: Optional[List[str]] = None
    current_role: Optional[str] = None
    key_responsibilities: Optional[str] = None
    achievements: Optional[str] = None
    notice_period: Optional[str] = None
    current_ctc: Optional[Decimal] = None
    expected_ctc: Optional[Decimal] = None

    # D. Skills & Projects
    technical_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    project_technologies: Optional[List[str]] = None
    resume_parsed_skills: Optional[List[str]] = None

    # E. Other
    employment_type_preference: Optional[str] = None
    availability_date: Optional[date] = None
    references: Optional[str] = None
    additional_comments: Optional[str] = None
    cover_letter: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    job_id: int
    full_name: str
    email: EmailStr
    phone_number: str
    # candidate_id is optional


class ApplicationUpdate(ApplicationBase):
    pass


class ApplicationResponse(ApplicationBase):
    id: int
    resume_keywords: Optional[List[str]] = None
    resume_score: Optional[Decimal] = None
    skills_match_score: Optional[Decimal] = None
    experience_match_score: Optional[Decimal] = None
    education_match_score: Optional[Decimal] = None
    certification_match_score: Optional[Decimal] = None
    keywords_match_score: Optional[Decimal] = None
    cat_theta: Optional[Decimal] = None
    cat_percentile: Optional[Decimal] = None
    cat_completed: bool = False
    video_hr_submitted: bool = False
    current_stage: str = "applied"
    applied_at: datetime
    updated_at: Optional[datetime] = None
    cat_exam_key: Optional[str] = None
    cat_exam_email_sent: bool = False
    cat_exam_email_sent_at: Optional[datetime] = None
    hr_video_exam_key: Optional[str] = None
    hr_video_exam_email_sent: bool = False
    hr_video_exam_email_sent_at: Optional[datetime] = None
    hr_exam_completed: bool = False
    assignment_exam_key: Optional[str] = None
    assignment_exam_email_sent: bool = False
    assignment_exam_email_sent_at: Optional[datetime] = None
    section1_completed: bool = False
    section2_completed: bool = False
    section3_completed: bool = False
    section1_theta: Optional[float] = None
    section1_percentile: Optional[float] = None
    section2_theta: Optional[float] = None
    section2_percentile: Optional[float] = None
    section3_theta: Optional[float] = None
    section3_percentile: Optional[float] = None
    assignment_completed: bool = False


# ============================================================
# Resume Upload / Parsing
# ============================================================


class FileUploadResponse(ORMModel):
    filename: str
    path: Optional[str] = None
    size_bytes: Optional[int] = None


class ResumeParseResponse(ORMModel):
    filename: str
    parsed_data: Dict[str, Any]
    extracted_skills: List[str]
    extracted_keywords: List[str]
    education: Optional[str] = None
    experience_years: Optional[float] = 0.0
    certifications: Optional[List[str]] = None


# ============================================================
# CAT Items
# ============================================================


class CATItemSchema(ORMModel):
    id: int
    question: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct: str
    a: float = 1.0
    b: float = 0.0
    c: float = 0.25
    used_count: int = 0
    correct_count: int = 0
    created_at: Optional[datetime] = None


# ============================================================
# Video Questions & Responses
# ============================================================


class VideoQuestionCreate(ORMModel):
    question_text: str
    duration_seconds: Optional[int] = 120
    created_by: int
    is_active: Optional[bool] = True


class VideoQuestionUpdate(ORMModel):
    question_text: Optional[str] = None
    duration_seconds: Optional[int] = None
    is_active: Optional[bool] = None


class VideoQuestionResponse(ORMModel):
    id: int
    question_text: str
    duration_seconds: int
    created_by: int
    created_at: Optional[datetime] = None
    is_active: bool = True


class JobVideoQuestionCreate(ORMModel):
    job_id: int
    video_question_id: int
    display_order: Optional[int] = 0


class JobVideoQuestionUpdate(ORMModel):
    display_order: Optional[int] = None


class JobVideoQuestionResponse(ORMModel):
    id: int
    job_id: int
    video_question_id: int
    display_order: int


# ============================================================
# Video Response Schemas - UPDATED with AI Scoring
# ============================================================


class VideoResponseCreate(ORMModel):
    """Create video response - AI will evaluate"""
    application_id: int
    job_video_question_id: int
    video_path: str
    duration_seconds: Optional[int] = None
    user_answer_text: Optional[str] = None  # Transcription (if available)


class VideoResponseUpdate(ORMModel):
    """Update video response - For HR final scoring"""
    hr_score: Optional[float] = None  # 0-10
    hr_feedback: Optional[str] = None
    hr_reviewed_by: Optional[int] = None


class VideoResponseBulkUpdateItem(VideoResponseUpdate):
    """Schema for bulk update item"""
    response_id: int
    


class VideoResponseDetail(ORMModel):
    """Detailed video response with all scores"""
    id: int
    application_id: int
    job_video_question_id: int
    video_path: str
    duration_seconds: Optional[int] = None
    
    # Question & Answer
    question_text: Optional[str] = None
    user_answer_text: Optional[str] = None
    
    # AI Scoring
    ai_score: Optional[float] = None
    ai_feedback: Optional[str] = None
    ai_evaluated_at: Optional[datetime] = None
    ai_evaluated: bool = False
    
    # HR Scoring
    hr_score: Optional[float] = None
    hr_feedback: Optional[str] = None
    hr_reviewed_by: Optional[int] = None
    hr_reviewed_at: Optional[datetime] = None
    hr_reviewed: bool = False
    
    # Final Score
    final_score: Optional[float] = None
    
    # Timestamps
    submitted_at: Optional[datetime] = None
    reviewed: bool = False


# ============================================================
# Exam Validation & Status Update
# ============================================================


class ExamValidation(ORMModel):
    username: Optional[str] = None
    key: str


class ExamValidationResponse(ORMModel):
    valid: bool
    application_id: Optional[int] = None
    candidate_name: Optional[str] = None
    job_title: Optional[str] = None
    message: Optional[str] = None


class StatusUpdateRequest(ORMModel):
    current_stage: str
    send_email: bool = True
    custom_message: Optional[str] = None


# ============================================================
# CAT Exam Schemas
# ============================================================


class CATExamStart(ORMModel):
    """Request to start CAT exam"""
    email: EmailStr
    cat_exam_key: str


class CATExamStartResponse(ORMModel):
    """Response when starting CAT exam"""
    session_id: int
    application_id: int
    candidate_name: str
    job_title: str
    current_theta: float = 0.0
    items_remaining: int


class CATItemRequest(ORMModel):
    """Request for next CAT item"""
    session_id: int


class CATItemResponse(ORMModel):
    """Response containing next CAT item"""
    item_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    item_number: int
    total_items_so_far: int
    should_continue: bool


class CATAnswerSubmit(ORMModel):
    """Submit answer to CAT item"""
    session_id: int
    item_id: int
    selected_option: str  # A, B, C, or D
    response_time_seconds: Optional[int] = None


class CATAnswerResponse(ORMModel):
    """Response after submitting answer"""
    is_correct: bool
    current_theta: float
    current_se: float
    items_completed: int
    should_continue: bool


class CATExamComplete(ORMModel):
    """Complete CAT exam"""
    session_id: int


class CATExamResults(ORMModel):
    """Final CAT exam results"""
    session_id: int
    theta: float
    se: float
    percentile: float
    num_items: int
    num_correct: int
    accuracy: float
    ability_level: str
    completed_at: datetime


# ============================================================
# HR Video Exam Schemas (Similar to CAT)
# ============================================================


class HRVideoExamStart(ORMModel):
    """Request to start HR Video exam"""
    email: EmailStr
    hr_video_exam_key: str


class HRVideoExamStartResponse(ORMModel):
    """Response when starting HR Video exam"""
    session_id: int
    application_id: int
    candidate_name: str
    job_title: str
    total_questions: int
    questions_remaining: int


class HRVideoQuestionRequest(ORMModel):
    """Request for next HR video question"""
    session_id: int


class HRVideoQuestionResponse(ORMModel):
    """Response containing next HR video question"""
    question_id: int
    question_text: str
    duration_seconds: int
    question_number: int
    total_questions: int
    should_continue: bool


class HRVideoAnswerSubmit(ORMModel):
    """Submit video answer to HR question"""
    session_id: int
    question_id: int
    video_path: str
    duration_seconds: Optional[int] = None
    user_answer_text: Optional[str] = None  # Transcription


class HRVideoAnswerResponse(ORMModel):
    """Response after submitting video answer"""
    response_id: int
    question_id: int
    ai_score: Optional[float] = None
    ai_feedback: Optional[str] = None
    ai_evaluated: bool = False
    questions_completed: int
    should_continue: bool


class HRVideoExamComplete(ORMModel):
    """Complete HR Video exam"""
    session_id: int


class HRVideoExamResults(ORMModel):
    """Final HR Video exam results"""
    session_id: int
    total_questions: int
    total_responses: int
    average_ai_score: float
    min_score: float
    max_score: float
    pending_hr_review: int
    completed_at: datetime


# ============================================================
# Candidate Schemas (for internal use)
# ============================================================


class CandidateBase(ORMModel):
    full_name: str
    email: EmailStr
    phone_number: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    linkedin_profile: Optional[str] = None
    portfolio_github: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(ORMModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    linkedin_profile: Optional[str] = None
    portfolio_github: Optional[str] = None


class CandidateResponse(CandidateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================
# Admin/HR Schemas
# ============================================================


class AdminBase(ORMModel):
    full_name: str
    email: EmailStr
    role: Optional[str] = "hr"  # hr, admin, recruiter, hiring_manager


class AdminCreate(AdminBase):
    password: str


class AdminUpdate(ORMModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None


class AdminResponse(AdminBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================
# Reporting & Analytics Schemas
# ============================================================


class ApplicationStageStats(ORMModel):
    """Statistics for application stages"""
    stage: str
    count: int
    percentage: float


class JobApplicationStats(ORMModel):
    """Overall statistics for a job"""
    job_id: int
    job_title: str
    total_applications: int
    by_stage: List[ApplicationStageStats]
    average_resume_score: Optional[float] = None
    average_cat_score: Optional[float] = None
    average_video_score: Optional[float] = None


class CandidateRankingResponse(ORMModel):
    """Candidate ranking for a job"""
    application_id: int
    candidate_name: str
    job_title: str
    final_score: float
    resume_score: Optional[float] = None
    cat_score: Optional[float] = None
    video_score: Optional[float] = None
    current_stage: str
    applied_at: datetime
    rank: int


# ============================================================
# Batch Video Response Schema (for sending multiple at once)
# ============================================================


class VideoResponseBatchRequest(ORMModel):
    """Batch request for multiple video responses"""
    responses: List[VideoResponseCreate] = Field(..., min_items=1, max_items=20)


class VideoResponseBatchResponse(ORMModel):
    """Batch response with all video responses"""
    total_submitted: int
    total_evaluated: int
    average_score: float
    responses: List[VideoResponseDetail]


# ============================================================
# Section Item Schemas (shared across sections 1-3)
# ============================================================


class SectionItemSchema(ORMModel):
    id: int
    question: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct: str
    a: Optional[float] = 1.0
    b: Optional[float] = 0.0
    c: Optional[float] = 0.25
    used_count: Optional[int] = 0
    correct_count: Optional[int] = 0
    created_at: Optional[datetime] = None


class SectionItemCreate(ORMModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct: str
    a: float = 1.0
    b: float = 0.0
    c: float = 0.25


class SectionItemUpdate(ORMModel):
    question: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct: Optional[str] = None
    a: Optional[float] = None
    b: Optional[float] = None
    c: Optional[float] = None


# ============================================================
# Assignment Exam Schemas
# ============================================================


class AssignmentExamStart(ORMModel):
    email: EmailStr
    assignment_exam_key: str


class AssignmentStartResponse(ORMModel):
    application_id: int
    candidate_name: str
    job_title: str
    section1_session_id: int
    section2_session_id: int
    section3_session_id: int
    section1_completed: bool = False
    section2_completed: bool = False
    section3_completed: bool = False


class AssignmentSectionNextItemResponse(ORMModel):
    item_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    item_number: int
    total_items_so_far: int
    should_continue: bool


class AssignmentAnswerSubmit(ORMModel):
    session_id: int
    item_id: int
    selected_option: str
    response_time_seconds: Optional[int] = None
    face_violations: Optional[int] = 0
    tab_switch_violations: Optional[int] = 0


class AssignmentAnswerResponse(ORMModel):
    is_correct: bool
    current_theta: float
    current_se: float
    items_completed: int
    should_continue: bool


class AssignmentSectionComplete(ORMModel):
    session_id: int
    face_violations: Optional[int] = 0
    tab_violations: Optional[int] = 0


class AssignmentSectionResults(ORMModel):
    session_id: int
    section: int
    theta: float
    se: float
    percentile: float
    num_items: int
    num_correct: int
    accuracy: float
    ability_level: str
    completed_at: Optional[datetime] = None


class AssignmentFinalResults(ORMModel):
    application_id: int
    candidate_name: str
    job_title: str
    section1: Optional[AssignmentSectionResults] = None
    section2: Optional[AssignmentSectionResults] = None
    section3: Optional[AssignmentSectionResults] = None
    overall_theta: Optional[float] = None
    overall_percentile: Optional[float] = None
