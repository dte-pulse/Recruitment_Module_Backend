
"""
AI Recruitment System - Complete Main API
Implements public applications, HR controls, exam invite via Gmail SSL, and exam validation.
All credentials hard-coded — NO .env required.
"""
from __future__ import annotations
from cat_engine import CATEngine, CATItem as CATItemClass, CATResponse
from models import (
    CATExamStart, CATExamStartResponse, CATItemRequest, CATItemResponse,
    CATAnswerSubmit, CATAnswerResponse, CATExamComplete, CATExamResults
)
import os
import shutil
import requests
import mimetypes
import re
from io import BytesIO
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Response, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from s3_service import S3Service
import pandas as pd
import auth
# Local imports
from database import SessionLocal, engine
from send_recruitment_email import send_recruitment_email
import database_models
from models import (
    JobCreate,
    JobUpdate,
    JobResponse,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    StatusUpdateRequest,
    ResumeParseResponse,
    CATItemSchema,
    VideoQuestionCreate,
    VideoQuestionUpdate,
    VideoQuestionResponse,
    JobVideoQuestionCreate,
    JobVideoQuestionUpdate,
    JobVideoQuestionResponse,
    VideoResponseCreate,
    VideoResponseUpdate,
    VideoResponseDetail,
    VideoResponseBulkUpdateItem,
    ExamValidation,
    ExamValidationResponse,
)
from scoring_service import ScoringService
from resume_parser import ResumeParser
from dotenv import load_dotenv
import boto3
import google.generativeai as genai
import os
# ============================================================
# Email Service (Hard-coded Gmail SSL - Port 465)
# ============================================================
load_dotenv()
# Configure Gemini (add this after load_dotenv())
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
s3_service = S3Service()

class EmailService:
    """Send exam invitations and status updates via Gmail SMTP SSL."""
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    FROM_EMAIL = os.getenv("FROM_EMAIL")
    FROM_NAME = "PulsePharma"
    EXAM_URL = os.getenv("EXAM_URL", "http://localhost:3000/exam/login")
    @staticmethod
    def send_exam_invitation(
        to_email: str,
        candidate_name: str,
        exam_key: str,
        job_title: str,
        exam_url: str | None = None,
    ) -> bool:
        """Send exam invitation email with credentials via SSL."""
        try:
            url = exam_url or EmailService.EXAM_URL
            subject = f"Exam Invitation – {job_title} | {EmailService.FROM_NAME}"
            html_body = f"""\
            <html>
              <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; line-height: 1.7; max-width: 650px; margin: 0 auto; background-color: #f5f7fa; padding: 20px;">
                <div style="background: white; border-radius: 8px; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                  <div style="text-align: center; margin-bottom: 30px; border-bottom: 3px solid #3498db; padding-bottom: 20px;">
                    <h1 style="color: #3498db; margin: 0; font-size: 28px;">{EmailService.FROM_NAME}</h1>
                    <p style="color: #7f8c8d; margin: 5px 0 0 0;">First Round Exam Invitation</p>
                  </div>
                  <h2 style="color: #2c3e50; font-size: 22px;">Hello {candidate_name},</h2>
                  <p style="font-size: 16px; margin: 0 0 20px 0;">
                    Thank you for applying to <strong>{job_title}</strong>. You're invited to our <strong>First Round Exam</strong>!
                  </p>
                  <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; padding: 25px; border-radius: 8px; margin: 25px 0;">
                    <h3 style="margin-top: 0; font-size: 18px;">📋 Exam Details</h3>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                      <li style="margin: 10px 0;"><strong>🔗 Platform:</strong> <a href="{url}" style="color: #ecf0f1; text-decoration: underline;">{url}</a></li>
                      <li style="margin: 10px 0;"><strong>⏱️ Duration:</strong> 90 minutes</li>
                      <li style="margin: 10px 0;"><strong>💻 Format:</strong> Online MCQ + Technical Questions</li>
                    </ul>
                  </div>
                                    <div style="margin: 25px 0;">
                                        <h3 style="color: #2c3e50; font-size: 16px; margin-top: 0;">🔐 Your Access Key</h3>
                                        <div style="background: #ecf0f1; padding: 12px; border-radius: 6px; font-family: 'Courier New', monospace; font-size: 18px; text-align: center;"><strong>{exam_key}</strong></div>
                    <p style="font-size: 12px; color: #e74c3c;">⚠️ Keep these credentials confidential. Do not share them with anyone.</p>
                  </div>
                  <div style="background: #ecf0f1; padding: 20px; border-left: 4px solid #3498db; border-radius: 4px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">📝 Important Instructions</h3>
                    <ol style="margin: 0; padding-left: 20px;">
                      <li>Log in 10 minutes before the exam starts.</li>
                      <li>Use a laptop/desktop with a stable internet connection.</li>
                      <li>Ensure good lighting and a quiet environment.</li>
                      <li>Have a valid photo ID ready for verification.</li>
                      <li>This is a proctored exam. Any malpractice will lead to disqualification.</li>
                    </ol>
                  </div>
                  <div style="text-align: center; margin: 30px 0;">
                    <a href="{url}" style="display: inline-block; background: #3498db; color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">Open Exam Portal</a>
                  </div>
                  <p style="font-size: 15px; color: #2c3e50; margin: 20px 0 0 0;">
                    We wish you the very best! If you have any questions, feel free to reach out.
                  </p>
                  <p style="font-size: 15px; color: #2c3e50; margin: 0;">Best regards,</p>
                  <hr style="border: 0; border-top: 2px solid #ecf0f1; margin: 30px 0;">
                  <div style="font-size: 13px; color: #7f8c8d; text-align: center;">
                    <p style="margin: 8px 0;"><strong>{EmailService.FROM_NAME}</strong></p>
                    <p style="margin: 4px 0;">Talent Acquisition Team</p>
                    <p style="margin: 4px 0;"><a href="mailto:{EmailService.FROM_EMAIL}" style="color: #3498db; text-decoration: none;">{EmailService.FROM_EMAIL}</a></p>
                    <p style="margin: 4px 0;">© 2025 {EmailService.FROM_NAME}. All rights reserved.</p>
                  </div>
                </div>
              </body>
            </html>
            """
            text_body = f"""
            Hello {candidate_name},
            Thank you for applying to {job_title}. You're invited to our First Round Exam!
            Exam Details:
            Platform: {url}
            Duration: 90 minutes
            Format: Online MCQ + Technical Questions
            Your Access Key:
            Access Key: {exam_key}
            Important: Keep these credentials confidential. Do not share them with anyone.
            Instructions:
            1. Log in 10 minutes before the exam starts.
            2. Use a laptop/desktop with a stable internet.
            3. Ensure good lighting and quiet environment.
            4. Have a valid photo ID ready for verification.
            5. This is a proctored exam. Any malpractice leads to disqualification.
            We wish you the very best!
            Best regards,
            {EmailService.FROM_NAME}
            """
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{EmailService.FROM_NAME} <{EmailService.FROM_EMAIL}>"
            msg["To"] = to_email
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP_SSL(EmailService.SMTP_HOST, EmailService.SMTP_PORT) as server:
                server.login(EmailService.SMTP_USER, EmailService.SMTP_PASSWORD)
                server.send_message(msg)
            print(f"✓ Exam invitation sent to {candidate_name} ({to_email})")
            return True
        except Exception as e:
            print(f"✗ Failed to send exam invitation to {to_email}: {e}")
            return False
    @staticmethod
    def send_status_update_email(
        to_email: str,
        candidate_name: str,
        job_title: str,
        new_status: str,
        message_content: Optional[str] = None,
    ) -> bool:
        try:
            templates = {
                "screening": {
                    "subject": f"Your application is under review – {job_title}",
                    "body": f"We are currently reviewing your profile. We'll reach out soon!",
                },
                "aptitude": {
                    "subject": f"Exam Invitation – {job_title} | {EmailService.FROM_NAME}",
                    "body": f"You're invited to the aptitude test round. Login details have been shared.",
                },
                "video_hr": {
                    "subject": f"Video Interview Scheduled – {job_title}",
                    "body": f"Congratulations! You've been shortlisted for the video interview. Please record your responses.",
                },
                "final_interview": {
                    "subject": f"Final Interview Invitation – {job_title}",
                    "body": f"Great news! You're in the final round. Our team will contact you to schedule.",
                },
                "offer": {
                    "subject": f"Job Offer Extended – {job_title} 🎉",
                    "body": f"Congratulations {candidate_name}! We are excited to extend an offer. Details attached.",
                },
                "hired": {
                    "subject": f"Welcome to {EmailService.FROM_NAME}! 🎊",
                    "body": f"Welcome aboard, {candidate_name}! HR will share onboarding details soon.",
                },
                "rejected": {
                    "subject": f"Application Update – {job_title}",
                    "body": "Thank you for your interest. We've decided to move forward with other candidates. We’ll keep your profile for future roles.",
                },
            }
            tmpl = templates.get(new_status, templates["screening"])
            subject = tmpl["subject"]
            default_msg = message_content or tmpl["body"]
            html_body = f"""
            <html><body style="font-family: Arial; padding: 20px; background: #f9f9f9;">
            <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50;">Application Update</h2>
                <p>Hello <strong>{candidate_name}</strong>,</p>
                <p>Your application for <strong>{job_title}</strong> has been updated to:</p>
                <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center; font-size: 18px; font-weight: bold; color: #1976d2;">
                {new_status.replace('_', ' ').title()}
                </div>
                <p style="margin-top: 20px;">{default_msg}</p>
                <hr style="margin: 30px 0;">
                <p style="color: #7f8c8d; font-size: 12px;">© 2025 {EmailService.FROM_NAME}. All rights reserved.</p>
            </div>
            </body></html>
            """
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{EmailService.FROM_NAME} <{EmailService.FROM_EMAIL}>"
            msg["To"] = to_email
            msg.attach(MIMEText(default_msg, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP_SSL(EmailService.SMTP_HOST, EmailService.SMTP_PORT) as server:
                server.login(EmailService.SMTP_USER, EmailService.SMTP_PASSWORD)
                server.send_message(msg)
            print(f"Email sent: {new_status} → {to_email}")
            return True
        except Exception as e:
            print(f"Email failed: {e}")
            return False
def generate_exam_credentials(application_id: int, full_name: str) -> str:
    """Generate a unique 8-character exam access key.
    NOTE: We intentionally do NOT generate or store a username. The system
    will validate candidates using the access key only.
    """
    key = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8))
    return key
# ============================================================
# FastAPI Setup
# ============================================================
app = FastAPI(
    title="AI Recruitment System - API",
    description="Recruitment workflow with Jobs, Public Applications, CAT, Video Interviews, Scoring, HR controls",
    version="4.0",
)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://pulse-recruitment.netlify.app","http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)
# Create tables and upload directories
database_models.Base.metadata.create_all(bind=engine)
UPLOAD_DIR = Path("uploads")
RESUME_DIR = UPLOAD_DIR / "resumes"
VIDEO_DIR = UPLOAD_DIR / "videos"
for d in [UPLOAD_DIR, RESUME_DIR, VIDEO_DIR]:
    d.mkdir(exist_ok=True)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def init_db():
    db = SessionLocal()
    try:
        if db.query(database_models.CATItem).count() == 0:
            cat_items = [
                {
                    "question": "If all cats are mammals and some mammals are pets, what can you conclude?",
                    "options": ["All pets are cats", "Some pets are cats", "No pets are cats", "All mammals are cats"],
                    "correct": 1,
                    "a": 0.5,
                    "b": 0.92,
                    "c": 0.3,
                },
                {
                    "question": "What comes next: 2, 4, 8, 16, ...?",
                    "options": ["32", "24", "18", "20"],
                    "correct": 0,
                    "a": 0.5,
                    "b": 2.31,
                    "c": 0.3,
                },
            ]
            for item in cat_items:
                correct_letter = chr(65 + item["correct"])
                db.add(
                    database_models.CATItem(
                        question=item["question"],
                        option_a=item["options"][0],
                        option_b=item["options"][1],
                        option_c=item["options"][2],
                        option_d=item["options"][3],
                        correct=correct_letter,
                        a=item["a"],
                        b=item["b"],
                        c=item["c"],
                    )
                )
            db.commit()
        if db.query(database_models.VideoQuestion).count() == 0:
            for q in [("Tell us about yourself.", 120), ("Why PulsePharma?", 90)]:
                db.add(
                    database_models.VideoQuestion(
                        question_text=q[0],
                        duration_seconds=q[1],
                        created_by=1,
                        is_active=True,
                    )
                )
            db.commit()
            # FIXED: Link VideoQuestions to sample Job (ID=1)
            video_qs = db.query(database_models.VideoQuestion).all()
            for i, vq in enumerate(video_qs):
                db.add(
                    database_models.JobVideoQuestion(
                        job_id=1,  # Sample job ID
                        video_question_id=vq.id,
                        display_order=i + 1
                    )
                )
            db.commit()
        if db.query(database_models.Job).count() == 0:
            db.add(
                database_models.Job(
                    job_code="SE001",
                    title="Senior Software Engineer",
                    department="Engineering",
                    location="Hyderabad, India",
                    type="full-time",
                    experience_level="3-5 years",
                    num_openings=2,
                    required_skills=["Python", "FastAPI", "React"],
                    status="open",
                    priority="high",
                )
            )
            db.commit()
    except Exception as e:
        print(f"DB init error: {e}")
        db.rollback()
    finally:
        db.close()
init_db()

# ============================================================
# AUTHENTICATION ENDPOINTS (SIMPLIFIED - NO DATABASE)
# ============================================================
@app.post("/auth/login", response_model=auth.Token)
async def login(email: str = Form(...), password: str = Form(...), response: Response = None):
    """
    Simplified Admin Login Endpoint
    Validates email and password against .env credentials.
    Returns JWT token with role='hr' and sets 7-day cookie.
    
    Credentials from .env:
    - ADMIN_EMAIL = admin@pulsepharma.com
    - ADMIN_PASSWORD = pavan@123
    """
    
    # Verify credentials against .env
    if not auth.verify_admin_credentials(email, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"✅ Admin login successful: {email}")
    
    # Create JWT token (24 hours)
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": email, "role": "hr"},
        expires_delta=access_token_expires
    )
    
    expires_in_seconds = auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    # Build response
    token_response = {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "hr",
        "email": email,
        "expires_in": expires_in_seconds
    }
    
    # Set cookies (7 days)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/",
        secure=False,  # Change to True in production with HTTPS
        httponly=True,
        samesite="lax"
    )
    
    response.set_cookie(
        key="user_role",
        value="hr",
        max_age=7 * 24 * 60 * 60,
        path="/",
        secure=False,
        httponly=False,
        samesite="lax"
    )
    
    response.set_cookie(
        key="user_email",
        value=email,
        max_age=7 * 24 * 60 * 60,
        path="/",
        secure=False,
        httponly=False,
        samesite="lax"
    )
    
    print(f"🍪 Cookies set: token, role, email (7 days)")
    
    return token_response


@app.post("/auth/logout")
async def logout(response: Response) -> dict:
    """Logout endpoint - Clears all auth cookies"""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="user_role", path="/")
    response.delete_cookie(key="user_email", path="/")
    
    print(f"✓ Admin logged out - cookies cleared")
    
    return {
        "message": "Logged out successfully",
        "status": "success"
    }


@app.get("/auth/me")
async def get_current_user(token_data: auth.TokenData = Depends(auth.get_current_admin)) -> dict:
    """Get current admin user info from JWT token"""
    return {
        "email": token_data.email,
        "role": token_data.role,
        "authenticated": True
    }


@app.get("/auth/verify")
async def verify_token(token_data: auth.TokenData = Depends(auth.get_current_admin)) -> dict:
    """Verify if JWT token is still valid"""
    return {
        "valid": True,
        "email": token_data.email,
        "role": token_data.role
    }


# ============================================================
# Root Endpoint
# ============================================================
@app.get("/")
def root():
    return {
        "message": "AI Recruitment System API v4.0",
        "email_service": "Gmail SSL (465) - hard-coded",
        "status": "operational",
        "features": ["Jobs", "Public Applications", "CAT Exam", "Video Interview", "Resume Parsing", "HR Dashboard"],
    }
# ============================================================
# Jobs Endpoints
# ============================================================


@app.get("/jobs", response_model=List[JobResponse])
def get_jobs(
    status: Optional[str] = None,
    experience_level: Optional[str] = None,
    department: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    query = db.query(database_models.Job)
    if status:
        query = query.filter(database_models.Job.status == status)
    if experience_level:
        query = query.filter(database_models.Job.experience_level == experience_level)
    if department:
        query = query.filter(database_models.Job.department == department)
    return query.order_by(desc(database_models.Job.posted_at)).offset(skip).limit(limit).all()
@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(database_models.Job).filter(database_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
@app.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(job: JobCreate, db: Session = Depends(get_db), ):
    if not job.job_code:
        prefix = job.department[:2].upper() if job.department else "JB"
        count = db.query(database_models.Job).count() + 1
        job.job_code = f"{prefix}{count:04d}"
    db_job = database_models.Job(**job.model_dump())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job
@app.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int, 
    job: JobUpdate, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    db_job = db.query(database_models.Job).filter(database_models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    for k, v in job.model_dump(exclude_unset=True).items():
        setattr(db_job, k, v)
    db.commit()
    db.refresh(db_job)
    return db_job
@app.delete("/jobs/{job_id}")
def delete_job(
    job_id: int, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    db_job = db.query(database_models.Job).filter(database_models.Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(db_job)
    db.commit()
    return {"message": "Job deleted successfully"}


@app.put("/applications/bulk-status-simple", response_model=List[ApplicationResponse])
def bulk_update_status_simple(
    app_ids: List[int],
    new_status: str,
    send_email: bool = True,                    # Optional: disable email if needed
    custom_message: Optional[str] = None,       # For custom notes in non-exam stages
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Bulk update application status with:
    - Auto-generated exam keys (Aptitude & Video HR)
    - Professional HTML email with Footer.jpg
    - Key stored in DB and sent securely to candidate
    """
    updated = []
    failed = []
    current_time = datetime.now()

    new_stage = new_status.strip().lower()

    for app_id in app_ids:
        try:
            app = db.query(database_models.Application).filter(
                database_models.Application.id == app_id
            ).first()

            if not app:
                print(f"Application {app_id} not found, skipping...")
                failed.append({"app_id": app_id, "error": "Not found"})
                continue

            old_stage = app.current_stage
            job = db.query(database_models.Job).filter(database_models.Job.id == app.job_id).first()
            job_title = job.title if job else "Position"

            # === MAIN LOGIC: Generate Key + Update Stage + Send Email ===
            exam_key = None
            email_sent_successfully = False

            # ——— Aptitude Stage ———
            if new_stage == "aptitude" and old_stage != "aptitude":
                exam_key = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8))
                app.cat_exam_key = exam_key
                app.current_stage = "aptitude"
                app.cat_exam_email_sent = False  # Will be set to True only if email succeeds

                if send_email and app.email:
                    success = send_recruitment_email(
                        candidate_name=app.full_name,
                        candidate_email=app.email.strip(),
                        stage="aptitude",
                        key=exam_key,
                        job_title=job_title,
                        exam_url="https://pulsehrapp.netlify.app/exam/login"
                    )
                    if success:
                        app.cat_exam_email_sent = True
                        app.cat_exam_email_sent_at = current_time
                        email_sent_successfully = True

                print(f"Generated CAT Key → {exam_key} | Email: {'Sent' if email_sent_successfully else 'Failed/Skipped'}")

            # ——— Video HR Stage ———
            elif new_stage == "video hr" and old_stage != "video hr":
                exam_key = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(8))
                app.hr_video_exam_key = exam_key
                app.current_stage = "video hr"
                app.hr_video_exam_email_sent = False

                if send_email and app.email:
                    success = send_recruitment_email(
                        candidate_name=app.full_name,
                        candidate_email=app.email.strip(),
                        stage="video_hr",
                        key=exam_key,
                        job_title=job_title,
                        exam_url="https://pulsehrapp.netlify.app/hr-video-exam"
                    )
                    if success:
                        app.hr_video_exam_email_sent = True
                        app.hr_video_exam_email_sent_at = current_time
                        email_sent_successfully = True

                print(f"Generated Video HR Key → {exam_key} | Email: {'Sent' if email_sent_successfully else 'Failed/Skipped'}")

            # ——— Other Stages (Applied, Final Interview, Hired, Rejected) ———
            else:
                app.current_stage = new_stage
                if send_email and app.email:
                    send_recruitment_email(
                        candidate_name=app.full_name,
                        candidate_email=app.email.strip(),
                        stage=new_stage,
                        job_title=job_title,
                        custom_message=custom_message
                    )

            # === Save Changes ===
            db.commit()
            db.refresh(app)
            updated.append(app)

            print(f"Updated App {app_id} → {new_stage.upper()} | Candidate: {app.full_name}")

        except Exception as e:
            print(f"Error processing app {app_id}: {str(e)}")
            failed.append({"app_id": app_id, "error": str(e)})
            db.rollback()

    # === Final Summary ===
    print("\n" + "="*60)
    print("BULK STATUS UPDATE COMPLETED")
    print("="*60)
    print(f"Successfully Updated: {len(updated)}")
    print(f"Failed/Skipped: {len(failed)}")
    if failed:
        print("Failed IDs:", [f["app_id"] for f in failed])
    print("="*60 + "\n")

    return updated

@app.get("/jobs/{job_id}/applications", response_model=List[ApplicationResponse])
def get_job_applications(
    job_id: int,
    min_score: Optional[float] = None,
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    job = db.query(database_models.Job).filter(database_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    query = db.query(database_models.Application).filter(database_models.Application.job_id == job_id)
    if min_score:
        query = query.filter(database_models.Application.resume_score >= min_score)
    return query.order_by(desc(database_models.Application.resume_score)).all()
# ============================================================
# Applications Endpoints
# ============================================================
@app.get("/applications", response_model=List[ApplicationResponse])
def get_applications(
    job_id: Optional[int] = None,
    stage: Optional[str] = None,
    min_score: Optional[float] = None,
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    query = db.query(database_models.Application)
    if job_id:
        query = query.filter(database_models.Application.job_id == job_id)
    if stage:
        query = query.filter(database_models.Application.current_stage == stage)
    if min_score:
        query = query.filter(database_models.Application.resume_score >= min_score)
    return query.order_by(desc(database_models.Application.applied_at)).offset(skip).limit(limit).all()
@app.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    application = db.query(database_models.Application).filter(
        database_models.Application.id == application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application

@app.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(application: ApplicationCreate, db: Session = Depends(get_db)):
    """Public application submission (no candidate_id required)."""
    job = db.query(database_models.Job).filter(
        database_models.Job.id == application.job_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db_application = database_models.Application(**application.model_dump())
    candidate_data = {
        "technical_skills": application.technical_skills or [],
        "total_experience": application.total_experience or 0.0,
        "highest_qualification": application.highest_qualification or "",
        "academic_score": application.academic_score or "",
        "certifications": application.certifications or [],
        "resume_keywords": [],
    }
    job_data = {
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "experience_level": job.experience_level or "",
        "education_requirement": job.education_requirement or "",
        "minimum_academic_score": job.minimum_academic_score or "",
        "required_certifications": job.required_certifications or [],
        "keywords": job.keywords or [],
    }
    if (candidate_data["technical_skills"] or
        candidate_data["highest_qualification"] or
        candidate_data["total_experience"] > 0):
        scores = ScoringService.score_application(candidate_data, job_data)
        db_application.resume_score = scores["overall_score"]
        db_application.skills_match_score = scores["skills_match_score"]
        db_application.experience_match_score = scores["experience_match_score"]
        db_application.education_match_score = scores["education_match_score"]
        db_application.certification_match_score = scores["certification_match_score"]
        db_application.keywords_match_score = scores["keywords_match_score"]
    else:
        db_application.resume_score = 0.0
        db_application.skills_match_score = 0.0
        db_application.experience_match_score = 0.0
        db_application.education_match_score = 0.0
        db_application.certification_match_score = 0.0
        db_application.keywords_match_score = 0.0
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application
@app.put("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int, 
    application: ApplicationUpdate, 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    db_application = db.query(database_models.Application).filter(
        database_models.Application.id == application_id
    ).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
    for k, v in application.model_dump(exclude_unset=True).items():
        setattr(db_application, k, v)
    db.commit()
    db.refresh(db_application)
    return db_application
@app.delete("/applications/{application_id}")
def delete_application(
    application_id: int, 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    db_application = db.query(database_models.Application).filter(
        database_models.Application.id == application_id
    ).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(db_application)
    db.commit()
    return {"message": "Application deleted successfully"}
# ============================================================
# Status Update + Exam Invitation (HR)
# ============================================================
@app.put("/applications/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: int,
    status_request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    HR updates the application stage.
    If set to 'aptitude', generate exam credentials and send email.
    """
    db_application = db.query(database_models.Application).filter(
        database_models.Application.id == application_id
    ).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
    job = db.query(database_models.Job).filter(
        database_models.Job.id == db_application.job_id
    ).first()
    old_stage = db_application.current_stage
    new_stage = status_request.current_stage
    db_application.current_stage = new_stage
    if new_stage == "aptitude" and old_stage != "aptitude":
        # Generate only an access key for CAT; do not create/store a username
        exam_key = generate_exam_credentials(db_application.id, db_application.full_name)
        db_application.cat_exam_key = exam_key
        if status_request.send_email:
            try:
                sent = EmailService.send_exam_invitation(
                    to_email=db_application.email,
                    candidate_name=db_application.full_name,
                    exam_key=exam_key,
                    job_title=job.title if job else "Position",
                    exam_url=EmailService.EXAM_URL,
                )
                if sent:
                    db_application.cat_exam_email_sent = True
                    db_application.cat_exam_email_sent_at = datetime.now()
            except Exception as e:
                print(f"Email send error: {e}")
    elif status_request.send_email and new_stage != old_stage:
        try:
            EmailService.send_status_update_email(
                to_email=db_application.email,
                candidate_name=db_application.full_name,
                job_title=job.title if job else "Position",
                new_status=new_stage,
                message_content=status_request.custom_message,
            )
        except Exception as e:
            print(f"Status email error: {e}")
    db.commit()
    db.refresh(db_application)
    return db_application
# ============================================================
# Exam Validation (Public)
# ============================================================
@app.post("/exam/validate", response_model=ExamValidationResponse)
def validate_exam_credentials(validation: ExamValidation, db: Session = Depends(get_db)):
    """Validate exam credentials for either CAT or HR video interview."""
   
    # Try to find application by either CAT or HR video exam key
    application = db.query(database_models.Application).filter(
        (database_models.Application.cat_exam_key == validation.key) |
        (database_models.Application.hr_video_exam_key == validation.key)
    ).first()
    if not application:
        return ExamValidationResponse(
            valid=False,
            message="Invalid access key. Please check your credentials.",
        )
    # Determine which type of exam by matching the key
    is_cat_exam = application.cat_exam_key == validation.key
    is_video_exam = application.hr_video_exam_key == validation.key
    # Validate based on exam type
    if is_cat_exam:
        if application.cat_completed:
            return ExamValidationResponse(
                valid=False,
                message="You have already completed the aptitude test.",
            )
        if application.current_stage != "aptitude":
            return ExamValidationResponse(
                valid=False,
                message="Your application is not currently at the aptitude test stage.",
            )
    elif is_video_exam:
        if application.video_hr_submitted:
            return ExamValidationResponse(
                valid=False,
                message="You have already completed the video interview.",
            )
        if application.current_stage != "video_hr":
            return ExamValidationResponse(
                valid=False,
                message="Your application is not currently at the video interview stage.",
            )
    job = db.query(database_models.Job).filter(
        database_models.Job.id == application.job_id
    ).first()
    return ExamValidationResponse(
        valid=True,
        application_id=application.id,
        candidate_name=application.full_name,
        job_title=job.title if job else None,
        message="Credentials validated successfully. You may proceed to the exam.",
    )
# ============================================================
# Resume Upload & Parsing (Public)
# ============================================================
@app.post("/applications/upload-resume", response_model=ResumeParseResponse)
async def upload_and_parse_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")
    file_path = RESUME_DIR / f"{datetime.now().timestamp()}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    parsed_data = ResumeParser.parse_resume(str(file_path))
    if "error" in parsed_data:
        raise HTTPException(status_code=400, detail=parsed_data["error"])
    return ResumeParseResponse(
        filename=file.filename,
        parsed_data=parsed_data,
        extracted_skills=parsed_data.get("technical_skills", []),
        extracted_keywords=parsed_data.get("resume_keywords", []),
        education=str(parsed_data.get("education", [])),
        experience_years=parsed_data.get("total_experience", 0.0),
        certifications=parsed_data.get("certifications", []),
    )
# ============================================================
# CAT Items (read-only)
# ============================================================
@app.get("/cat-items", response_model=List[CATItemSchema])
def get_cat_items(
    skip: int = 0, 
    limit: int = 1000, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    return db.query(database_models.CATItem).offset(skip).limit(limit).all()
@app.get("/cat-items/{item_id}", response_model=CATItemSchema)
def get_cat_item(
    item_id: int, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    item = db.query(database_models.CATItem).filter(database_models.CATItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="CAT item not found")
    return item
# ============================================================
# Video Questions
# ============================================================
@app.get("/video-questions", response_model=List[VideoQuestionResponse])
def get_video_questions(
    active_only: bool = True,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    query = db.query(database_models.VideoQuestion)
    if active_only:
        query = query.filter(database_models.VideoQuestion.is_active == True)
    return query.offset(skip).limit(limit).all()
@app.get("/video-questions/{question_id}", response_model=VideoQuestionResponse)
def get_video_question(
    question_id: int, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    question = db.query(database_models.VideoQuestion).filter(
        database_models.VideoQuestion.id == question_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Video question not found")
    return question
@app.post("/video-questions", response_model=VideoQuestionResponse, status_code=status.HTTP_201_CREATED)
def create_video_question(
    question: VideoQuestionCreate, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    db_question = database_models.VideoQuestion(**question.model_dump())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question
@app.put("/video-questions/{question_id}", response_model=VideoQuestionResponse)
def update_video_question(
    question_id: int,
    question: VideoQuestionUpdate,
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin),
):
    db_question = db.query(database_models.VideoQuestion).filter(
        database_models.VideoQuestion.id == question_id
    ).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Video question not found")
    for k, v in question.model_dump(exclude_unset=True).items():
        setattr(db_question, k, v)
    db.commit()
    db.refresh(db_question)
    return db_question
@app.delete("/video-questions/{question_id}")
def delete_video_question(
    question_id: int, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    db_question = db.query(database_models.VideoQuestion).filter(
        database_models.VideoQuestion.id == question_id
    ).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Video question not found")
    db_question.is_active = False
    db.commit()
    return {"message": "Video question deactivated successfully"}

@app.post("/video-questions/upload")
async def upload_video_questions(
    file: UploadFile = File(...),
    created_by: int = 1,  # Default admin user ID
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Bulk upload video questions from Excel file.
    Expected columns: question_text, duration_seconds (optional)
    Optional column: is_active (default: True)
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx, .xls)")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        # Validate required columns
        required_columns = ['question_text']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing_columns)}")
        
        # Insert items
        count = 0
        skipped = 0
        for idx, row in df.iterrows():
            # Validate question text
            question_text = str(row['question_text']).strip()
            if not question_text or question_text == 'nan':
                print(f"Skipping row {idx + 2} - empty question text")
                skipped += 1
                continue
            
            video_question = database_models.VideoQuestion(
                question_text=question_text,
                duration_seconds=int(row.get('duration_seconds', 120)),
                created_by=created_by,
                is_active=bool(row.get('is_active', True))
            )
            db.add(video_question)
            count += 1
            
        db.commit()
        
        message = f"Successfully uploaded {count} video questions"
        if skipped > 0:
            message += f" ({skipped} rows skipped due to invalid data)"
        
        return {"message": message, "uploaded": count, "skipped": skipped}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.get("/jobs/{job_id}/video-questions")
def get_job_with_questions(
    job_id: int, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Get job with assigned video questions (returns JobVideoQuestion mappings with embedded questions)
    """
    job = db.query(database_models.Job).filter(database_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_video_questions = db.query(database_models.JobVideoQuestion).filter(
        database_models.JobVideoQuestion.job_id == job_id
    ).options(joinedload(database_models.JobVideoQuestion.video_question)).all()
    
    # ✅ CORRECT: Return the full mapping objects with embedded question details
    video_questions = [
        {
            "id": jvq.id,  # JobVideoQuestion.id (mapping ID) ✅
            "job_id": jvq.job_id,
            "video_question_id": jvq.video_question_id,
            "display_order": jvq.display_order,
            "question_text": jvq.video_question.question_text,
            "duration_seconds": jvq.video_question.duration_seconds,
        }
        for jvq in job_video_questions
    ]
    return video_questions  # Return array directly (not nested in object)
@app.post("/job-video-questions", response_model=JobVideoQuestionResponse, status_code=status.HTTP_201_CREATED)
def link_video_question_to_job(
    mapping: JobVideoQuestionCreate, 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    job = db.query(database_models.Job).filter(database_models.Job.id == mapping.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    video_question = db.query(database_models.VideoQuestion).filter(
        database_models.VideoQuestion.id == mapping.video_question_id
    ).first()
    if not video_question:
        raise HTTPException(status_code=404, detail="Video question not found")
    existing = db.query(database_models.JobVideoQuestion).filter(
        database_models.JobVideoQuestion.job_id == mapping.job_id,
        database_models.JobVideoQuestion.video_question_id == mapping.video_question_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This video question is already linked to the job")
    db_mapping = database_models.JobVideoQuestion(**mapping.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping
# ============================================================
# VIDEO RESPONSES - CREATE SINGLE
# ============================================================
@app.post("/video-responses", response_model=VideoResponseDetail, status_code=status.HTTP_201_CREATED)
async def create_video_response(
    response: VideoResponseCreate, 
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Create a single video response and evaluate with AI scoring.
   
    Use this endpoint when submitting one video answer at a time.
    """
    # 1. Validate application exists
    application = db.query(database_models.Application).filter(
        database_models.Application.id == response.application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    # 2. Validate job_video_question exists
    job_video_question = db.query(database_models.JobVideoQuestion).filter(
        database_models.JobVideoQuestion.id == response.job_video_question_id
    ).options(
        joinedload(database_models.JobVideoQuestion.video_question)
    ).first()
   
    if not job_video_question:
        raise HTTPException(status_code=404, detail="Video question not found")
    # 3. Get question text
    video_question = job_video_question.video_question
    question_text = video_question.question_text if video_question else ""
    # 4. Create video response record
    db_response = database_models.VideoResponse(
        application_id=response.application_id,
        job_video_question_id=response.job_video_question_id,
        video_path=response.video_path,
        duration_seconds=response.duration_seconds,
        question_text=question_text,
        user_answer_text=response.user_answer_text,
        ai_evaluated=False
    )
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    # 5. Call AI to evaluate
    try:
        ai_score, ai_feedback = await evaluate_video_response_with_ai(
            question_text=question_text,
            user_answer=response.user_answer_text or "[No answer provided]",
            application_id=response.application_id,
            job_title=application.job.title if application.job else "Position",
            responsibilities=application.job.responsibilities if application.job else ""
        )
        # 6. Update with AI scores
        db_response.ai_score = ai_score
        db_response.ai_feedback = ai_feedback
        db_response.ai_evaluated = True
        db_response.ai_evaluated_at = datetime.now()
        db_response.final_score = ai_score
        db.commit()
        db.refresh(db_response)
        print(f"✓ AI evaluation completed for response {db_response.id}: Score {ai_score}/10")
    except Exception as e:
        print(f"⚠️ AI evaluation failed for response {db_response.id}: {str(e)}")
        db_response.ai_evaluated = False
        db.commit()
        db.refresh(db_response)
    return db_response

# ============================================================
# VIDEO RESPONSES - CREATE BATCH (MULTIPLE)
# ============================================================
@app.post("/video-responses/batch", response_model=List[VideoResponseDetail], status_code=status.HTTP_201_CREATED)
async def create_video_responses_batch(
    responses: List[VideoResponseCreate],
    db: Session = Depends(get_db)
):
    """
    Create multiple video responses in a single request.
   
    Use this endpoint when submitting all video answers at once (e.g., after interview completes).
    All responses are evaluated in parallel for faster processing.
   
    Max 20 responses per batch.
    """
   
    if not responses:
        raise HTTPException(status_code=400, detail="At least one response is required")
   
    if len(responses) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 responses per batch allowed")
   
    created = []
   
    # 1. Validate and create all response records
    for response in responses:
        # Validate application
        application = db.query(database_models.Application).filter(
            database_models.Application.id == response.application_id
        ).first()
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {response.application_id} not found"
            )
        # Validate job_video_question
        job_video_question = db.query(database_models.JobVideoQuestion).filter(
            database_models.JobVideoQuestion.id == response.job_video_question_id
        ).options(
            joinedload(database_models.JobVideoQuestion.video_question)
        ).first()
       
        if not job_video_question:
            raise HTTPException(
                status_code=404,
                detail=f"Job video question ID {response.job_video_question_id} not found (check job linking)"
            )
        # Get question text
        video_question = job_video_question.video_question
        question_text = video_question.question_text if video_question else ""
        # Create response
        db_response = database_models.VideoResponse(
            application_id=response.application_id,
            job_video_question_id=response.job_video_question_id,
            video_path=response.video_path,
            duration_seconds=response.duration_seconds,
            question_text=question_text,
            user_answer_text=response.user_answer_text,
            ai_evaluated=False
        )
        db.add(db_response)
        db.flush()
       
        created.append({
            "db_response": db_response,
            "application": application,
            "response": response
        })
    db.commit()
    for item in created:
        db.refresh(item["db_response"])
    # 2. Run AI evaluations in parallel
    import asyncio
   
    evaluation_tasks = [
        evaluate_video_response_with_ai(
            question_text=item["db_response"].question_text,
            user_answer=item["response"].user_answer_text or "[No answer provided]",
            application_id=item["db_response"].application_id,
            job_title=item["application"].job.title if item["application"].job else "Position",
            responsibilities=item["application"].job.responsibilities if item["application"].job else ""
        )
        for item in created
    ]
    ai_results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
    # 3. Update all responses with AI scores
    for idx, item in enumerate(created):
        db_response = item["db_response"]
       
        if isinstance(ai_results[idx], Exception):
            print(f"⚠️ AI evaluation failed for response {db_response.id}: {str(ai_results[idx])}")
            db_response.ai_evaluated = False
        else:
            ai_score, ai_feedback = ai_results[idx]
            db_response.ai_score = ai_score
            db_response.ai_feedback = ai_feedback
            db_response.ai_evaluated = True
            db_response.ai_evaluated_at = datetime.now()
            db_response.final_score = ai_score
            print(f"✓ AI evaluation completed for response {db_response.id}: Score {ai_score}/10")

    # 4. Update application status (Mark HR Exam as Completed)
    processed_app_ids = set()
    for item in created:
        app = item["application"]
        if app.id not in processed_app_ids:
            app.hr_exam_completed = True
            processed_app_ids.add(app.id)
            print(f"✓ Application {app.id} marked as HR exam completed")
            
    db.commit()
    # 5. Refresh and return all responses
    for item in created:
        db.refresh(item["db_response"])
    print(f"✓ Batch processing completed: {len(created)} responses evaluated")
    return [item["db_response"] for item in created]

# ============================================================
# VIDEO RESPONSES - BULK UPDATE SCORES
# ============================================================

@app.put("/video-responses/bulk-update-scores")
def bulk_update_video_scores(
    updates: List[VideoResponseBulkUpdateItem],
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Bulk update video responses with HR/Admin final scoring.
    
    This endpoint allows HR to score multiple video responses in a single batch request.
    Each item in the list should contain:
    - response_id: The video response ID to update
    - hr_score: HR score (0-10)
    - hr_feedback: Optional feedback from HR reviewer
    - hr_reviewed_by: HR reviewer user ID (int)
    
    HR score takes priority over AI score for final evaluation.
    
    Example request body:
    [
        {
            "response_id": 25,
            "hr_score": 8.5,
            "hr_feedback": "Good answer",
            "hr_reviewed_by": 1
        },
        {
            "response_id": 26,
            "hr_score": 7.0,
            "hr_feedback": "Average depth",
            "hr_reviewed_by": 1
        }
    ]
    
    Returns: Summary object with updated responses and stats
    """
    
    if not updates:
        raise HTTPException(status_code=400, detail="At least one response update is required")
    
    if len(updates) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 responses per bulk update allowed")
    
    updated_responses = []
    failed_updates = []
    
    # Track summary stats
    total_processed = 0
    total_updated = 0
    total_failed = 0
    
    for idx, update in enumerate(updates):
        try:
            # 1. Get existing response
            db_response = db.query(database_models.VideoResponse).filter(
                database_models.VideoResponse.id == update.response_id
            ).first()
            
            if not db_response:
                failed_updates.append({
                    "index": idx,
                    "response_id": update.response_id,
                    "error": "Video response not found"
                })
                total_failed += 1
                print(f"⚠️ Response {update.response_id} not found")
                continue
            
            # 2. Validate HR score range (0-10)
            if update.hr_score is not None:
                if not (0 <= update.hr_score <= 10):
                    failed_updates.append({
                        "index": idx,
                        "response_id": update.response_id,
                        "error": f"HR score {update.hr_score} must be between 0 and 10"
                    })
                    total_failed += 1
                    print(f"⚠️ Invalid score for response {update.response_id}: {update.hr_score}")
                    continue
            
            # 3. Update fields
            if update.hr_score is not None:
                db_response.hr_score = update.hr_score
                print(f"✓ HR Score set to {update.hr_score}/10 for response {update.response_id}")
            
            if update.hr_feedback is not None:
                db_response.hr_feedback = update.hr_feedback
            
            if update.hr_reviewed_by is not None:
                db_response.hr_reviewed_by = update.hr_reviewed_by
            
            # 4. Determine final score (HR priority > AI)
            if db_response.hr_score is not None:
                db_response.final_score = db_response.hr_score
                db_response.hr_reviewed = True
                db_response.reviewed = True
                db_response.hr_reviewed_at = datetime.now()
                print(f"✓ Final score set to HR score: {db_response.final_score}/10")
            elif db_response.ai_score is not None:
                db_response.final_score = db_response.ai_score
                print(f"✓ Final score using AI score: {db_response.final_score}/10")
            
            # Mark as updated
            db.add(db_response)
            updated_responses.append(db_response)
            total_updated += 1
            total_processed += 1
            
        except Exception as e:
            failed_updates.append({
                "index": idx,
                "response_id": update.response_id if hasattr(update, 'response_id') else None,
                "error": str(e)
            })
            total_failed += 1
            print(f"⚠️ Error processing update at index {idx}: {str(e)}")
            db.rollback()
            continue
    
    # Commit all successful updates at once
    if updated_responses:
        db.commit()
        for response in updated_responses:
            db.refresh(response)
    
    # Print summary
    print("\n" + "="*70)
    print("BULK VIDEO RESPONSE SCORING COMPLETED")
    print("="*70)
    print(f"Total Processed: {total_processed}")
    print(f"Successfully Updated: {total_updated}")
    print(f"Failed/Skipped: {total_failed}")
    if failed_updates:
        print("\nFailed Updates:")
        for failed in failed_updates:
            print(f"  - Response ID {failed['response_id']} (Index {failed['index']}): {failed['error']}")
    print("="*70 + "\n")
    
    return {
        "total_processed": total_processed,
        "successfully_updated": total_updated,
        "failed": total_failed,
        "updated_responses": updated_responses,
        "failed_updates": failed_updates,
        "summary": {
            "message": f"Successfully updated {total_updated} responses",
            "timestamp": datetime.now().isoformat()
        }
    }

# ============================================================

@app.put("/video-responses/{response_id}", response_model=VideoResponseDetail)
def update_video_response(
    response_id: int,
    response_update: VideoResponseUpdate,
    db: Session = Depends(get_db),
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Update video response with HR/Admin final scoring.
   
    HR score takes priority over AI score for final evaluation.
    """
    # 1. Get existing response
    db_response = db.query(database_models.VideoResponse).filter(
        database_models.VideoResponse.id == response_id
    ).first()
   
    if not db_response:
        raise HTTPException(status_code=404, detail="Video response not found")
    # 2. Validate HR score range (0-10)
    if response_update.hr_score is not None:
        if not (0 <= response_update.hr_score <= 10):
            raise HTTPException(
                status_code=400,
                detail="HR score must be between 0 and 10"
            )
    # 3. Update fields
    if response_update.hr_score is not None:
        db_response.hr_score = response_update.hr_score
        print(f"✓ HR Score set to {response_update.hr_score}/10 for response {response_id}")
   
    if response_update.hr_feedback is not None:
        db_response.hr_feedback = response_update.hr_feedback
   
    if response_update.hr_reviewed_by is not None:
        db_response.hr_reviewed_by = response_update.hr_reviewed_by
    # 4. Determine final score (HR priority > AI)
    if db_response.hr_score is not None:
        db_response.final_score = db_response.hr_score
        db_response.hr_reviewed = True
        db_response.reviewed = True
        db_response.hr_reviewed_at = datetime.now()
        print(f"✓ Final score set to HR score: {db_response.final_score}/10")
    elif db_response.ai_score is not None:
        db_response.final_score = db_response.ai_score
        print(f"✓ Final score using AI score: {db_response.final_score}/10")
    db.commit()
    db.refresh(db_response)
    print(f"✓ Video response {response_id} updated")
    return db_response
# ============================================================
# VIDEO RESPONSES - GET
# ============================================================
@app.get("/video-responses/{response_id}", response_model=VideoResponseDetail)
def get_video_response(
    response_id: int, 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """Get a single video response with all scores"""
    db_response = db.query(database_models.VideoResponse).filter(
        database_models.VideoResponse.id == response_id
    ).first()
   
    if not db_response:
        raise HTTPException(status_code=404, detail="Video response not found")
   
    return db_response
@app.get("/applications/{application_id}/video-responses", response_model=List[VideoResponseDetail])
def get_application_video_responses(
    application_id: int, 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """Get all video responses for an application"""
    application = db.query(database_models.Application).filter(
        database_models.Application.id == application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
   
    responses = db.query(database_models.VideoResponse).filter(
        database_models.VideoResponse.application_id == application_id
    ).all()
    return responses
# ============================================================
# AI EVALUATION HELPER (ASYNC)
# ============================================================
async def evaluate_video_response_with_ai(
    question_text: str,
    user_answer: str,
    application_id: int,
    job_title: str = "Position",
    responsibilities: str = "",
) -> tuple[float, str]:
    """
    Use Gemini AI to evaluate video response.
   
    Scoring Criteria (0-10):
    - Clarity & Communication (3 points)
    - Relevance & Accuracy (3 points)
    - Enthusiasm & Engagement (2 points)
    - Overall Professionalism (2 points)
   
    Returns: (score: float, feedback: str)
    """
   
    evaluation_prompt = f"""
You are an expert HR interviewer evaluating a candidate's video response for a {job_title} position.
INTERVIEW QUESTION:
"{question_text}"
CANDIDATE'S RESPONSE:
"{user_answer}"
Please evaluate the response using the following criteria (max 10 points total):
1. **Clarity & Communication (max 3 points)**
   - Is the answer clear, coherent, and well-structured?
   - Does the candidate articulate their thoughts effectively?
2. **Relevance & Accuracy (max 3 points)**
   - Does the answer directly address the question?
   - Is the information accurate and contextual?
3. **Enthusiasm & Engagement (max 2 points)**
   - Does the candidate show genuine interest?
   - Is there evidence of passion for the role/company?
4. **Professionalism & Confidence (max 2 points)**
   - Is the tone professional and respectful?
   - Does the candidate demonstrate confidence?
Please provide:
1. **SCORE**: A single number between 0-10 (e.g., 7.5)
2. **DETAILED FEEDBACK**: 2-3 sentences explaining the score
3. **KEY OBSERVATIONS**: 2-3 bullet points
Format your response EXACTLY as follows:
SCORE: [number]
FEEDBACK: [feedback text]
OBSERVATIONS: [bullet points]
"""
    try:
        # Call Gemini API
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(evaluation_prompt)
       
        # Parse response
        response_text = response.text
        print(f"AI Response:\n{response_text}\n")
       
        # Extract score
        score_line = [line for line in response_text.split('\n') if line.startswith('SCORE:')]
        if score_line:
            score_str = score_line[0].replace('SCORE:', '').strip()
            score = float(score_str)
            score = max(0, min(10, score))
        else:
            score = 5.0
       
        # Extract feedback
        feedback_line = [line for line in response_text.split('\n') if line.startswith('FEEDBACK:')]
        feedback = ""
        if feedback_line:
            feedback = feedback_line[0].replace('FEEDBACK:', '').strip()
        else:
            feedback = response_text[:500]
       
        print(f"✓ AI Score: {score}/10 | Feedback: {feedback[:80]}...")
        return score, feedback
    except Exception as e:
        print(f"✗ AI evaluation error: {str(e)}")
        return 5.0, f"AI evaluation error: {str(e)}. Manual review recommended."
# ============================================================
# HR Dashboard
# ============================================================
@app.get("/hr/dashboard")
def get_hr_dashboard(
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    total_jobs = db.query(database_models.Job).count()
    open_jobs = db.query(database_models.Job).filter(database_models.Job.status == "open").count()
    closed_jobs = db.query(database_models.Job).filter(database_models.Job.status == "closed").count()
    draft_jobs = db.query(database_models.Job).filter(database_models.Job.status == "draft").count()
    total_applications = db.query(database_models.Application).count()
    today = datetime.now().date()
    applications_today = db.query(database_models.Application).filter(
        func.date(database_models.Application.applied_at) == today
    ).count()
    week_ago = today - timedelta(days=7)
    applications_this_week = db.query(database_models.Application).filter(
        func.date(database_models.Application.applied_at) >= week_ago
    ).count()
    month_ago = today - timedelta(days=30)
    applications_this_month = db.query(database_models.Application).filter(
        func.date(database_models.Application.applied_at) >= month_ago
    ).count()
    avg_scores = db.query(
        func.avg(database_models.Application.resume_score),
        func.avg(database_models.Application.cat_theta),
        func.avg(database_models.Application.cat_percentile),
    ).first()
    avg_resume_score = float(avg_scores[0]) if avg_scores[0] else None
    avg_cat_theta = float(avg_scores[1]) if avg_scores[1] else None
    avg_cat_percentile = float(avg_scores[2]) if avg_scores[2] else None
    stages = db.query(
        database_models.Application.current_stage,
        func.count(database_models.Application.id),
    ).group_by(database_models.Application.current_stage).all()
    stages_dict = {stage: count for stage, count in stages}
    all_keywords = db.query(database_models.Application.resume_keywords).all()
    keyword_freq = {}
    for (keywords,) in all_keywords:
        if keywords:
            for k in keywords:
                keyword_freq[k] = keyword_freq.get(k, 0) + 1
    top_keywords = [k for k, v in sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]]
    applications_by_job = db.query(
        database_models.Job.id,
        database_models.Job.title,
        func.count(database_models.Application.id).label("count"),
    ).join(database_models.Application).group_by(database_models.Job.id).all()
    applications_by_job_list = [
        {"job_id": j_id, "job_title": j_title, "count": count}
        for j_id, j_title, count in applications_by_job
    ]
    return {
        "total_jobs": total_jobs,
        "open_jobs": open_jobs,
        "closed_jobs": closed_jobs,
        "draft_jobs": draft_jobs,
        "total_applications": total_applications,
        "applications_today": applications_today,
        "applications_this_week": applications_this_week,
        "applications_this_month": applications_this_month,
        "avg_resume_score": avg_resume_score,
        "avg_cat_theta": avg_cat_theta,
        "avg_cat_percentile": avg_cat_percentile,
        "stages": stages_dict,
        "top_keywords": top_keywords,
        "applications_by_job": applications_by_job_list,
    }
# ============================================================
# Stats
# ============================================================
@app.get("/stats")
def get_statistics(
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    total_jobs = db.query(database_models.Job).count()
    open_jobs = db.query(database_models.Job).filter(database_models.Job.status == "open").count()
    total_applications = db.query(database_models.Application).count()
    cat_count = db.query(database_models.CATItem).count()
    video_questions_count = db.query(database_models.VideoQuestion).filter(
        database_models.VideoQuestion.is_active == True
    ).count()
    stages = db.query(
        database_models.Application.current_stage,
        func.count(database_models.Application.id),
    ).group_by(database_models.Application.current_stage).all()
    stages_dict = {stage: count for stage, count in stages}
    return {
        "total_jobs": total_jobs,
        "open_jobs": open_jobs,
        "total_applications": total_applications,
        "total_cat_items": cat_count,
        "active_video_questions": video_questions_count,
        "applications_by_stage": stages_dict,
        "version": "4.0",
        "email_service": "Gmail SSL (465) hard-coded",
    }
# ============================================================
# CAT Exam Endpoints - ADD THESE TO YOUR EXISTING main.py
# ============================================================
@app.post("/cat/start", response_model=CATExamStartResponse)
def start_cat_exam(exam_start: CATExamStart, db: Session = Depends(get_db)):
    """
    Start or resume a CAT exam session using email + cat_exam_key.
    """
    # 1) Validate email + CAT access key
    application = (
        db.query(database_models.Application)
        .filter(
            database_models.Application.email == exam_start.email.lower(),
            database_models.Application.cat_exam_key == exam_start.cat_exam_key,
        )
        .first()
    )
    if not application:
        raise HTTPException(status_code=401, detail="Invalid email or exam key")

    # 2) Enforce stage and completion checks
    if application.cat_completed:
        raise HTTPException(status_code=400, detail="You have already completed this exam")
    if application.current_stage != "aptitude":
        raise HTTPException(
            status_code=400,
            detail="Your application is not at the aptitude test stage",
        )

    # 3) Resume or create session
    session = (
        db.query(database_models.CATSession)
        .filter(
            database_models.CATSession.application_id == application.id,
            database_models.CATSession.is_active == True,
        )
        .first()
    )
    if not session:
        session = database_models.CATSession(
            application_id=application.id,
            current_theta=0.0,           # ← FIXED
            current_se=None,
            num_items_administered=0,
            is_active=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # 4) Load job title
    job = (
        db.query(database_models.Job)
        .filter(database_models.Job.id == application.job_id)
        .first()
    )

    # 5) Return response
    items_completed = session.num_items_administered or 0
    items_remaining = max(0, 30 - items_completed)
    return CATExamStartResponse(
        session_id=session.id,
        application_id=application.id,
        candidate_name=application.full_name,
        job_title=job.title if job else "Position",
        current_theta=float(session.current_theta or 0.0),
        items_remaining=items_remaining,
    )

@app.post("/cat/next-item", response_model=CATItemResponse)
def get_next_cat_item(request: CATItemRequest, db: Session = Depends(get_db)):
    """Get next adaptive item"""
    session = db.query(database_models.CATSession).filter(
        database_models.CATSession.id == request.session_id,
        database_models.CATSession.is_active == True
    ).first()
   
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
   
    all_items = db.query(database_models.CATItem).all()
    if not all_items:
        raise HTTPException(status_code=500, detail="No items available")
   
    cat_items = [
        CATItemClass(
            id=item.id, question=item.question,
            option_a=item.option_a, option_b=item.option_b,
            option_c=item.option_c, option_d=item.option_d,
            correct=item.correct, a=item.a, b=item.b, c=item.c
        ) for item in all_items
    ]
   
    engine = CATEngine(items=cat_items, initial_theta=session.current_theta)
    engine.current_theta = session.current_theta
   
    administered = db.query(database_models.CATItemResponse).filter(
        database_models.CATItemResponse.session_id == session.id
    ).all()
    engine.administered_items = [r.item_id for r in administered]
    for resp in administered:
        engine.responses.append(CATResponse(
            item_id=resp.item_id, selected_option=resp.selected_option,
            is_correct=resp.is_correct, theta_before=resp.theta_before,
            theta_after=resp.theta_after, se_after=resp.se_after
        ))
   
    if not engine.should_continue():
        raise HTTPException(status_code=400, detail="Exam complete")
   
    next_item = engine.select_next_item()
    if not next_item:
        raise HTTPException(status_code=500, detail="No suitable item")
   
    return CATItemResponse(
        item_id=next_item.id, question=next_item.question,
        option_a=next_item.option_a, option_b=next_item.option_b,
        option_c=next_item.option_c, option_d=next_item.option_d,
        item_number=len(engine.administered_items) + 1,
        total_items_so_far=len(engine.administered_items),
        should_continue=True
    )
@app.post("/cat/submit-answer", response_model=CATAnswerResponse)
def submit_cat_answer(answer: CATAnswerSubmit, db: Session = Depends(get_db)):
    """Submit answer and update theta"""
    print(f"Processing answer submission - Session ID: {answer.session_id}, Item ID: {answer.item_id}")
   
    # Validate selected_option is A, B, C, or D
    if not answer.selected_option or answer.selected_option.upper() not in ["A", "B", "C", "D"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid selected_option. Must be one of: A, B, C, or D"
        )
    # Get session and validate
    session = db.query(database_models.CATSession).filter(
        database_models.CATSession.id == answer.session_id
    ).first()
   
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
       
    if not session.is_active:
        raise HTTPException(
            status_code=400,
            detail="Session is no longer active. The exam may have been completed or timed out."
        )
       
    # Check if we've hit the maximum questions (30)
    if session.num_items_administered >= 30:
        raise HTTPException(
            status_code=400,
            detail="Maximum number of questions (30) has been reached. Please complete the exam."
        )
   
    item = db.query(database_models.CATItem).filter(
        database_models.CATItem.id == answer.item_id
    ).first()
   
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
   
    existing = db.query(database_models.CATItemResponse).filter(
        database_models.CATItemResponse.session_id == answer.session_id,
        database_models.CATItemResponse.item_id == answer.item_id
    ).first()
   
    if existing:
        raise HTTPException(status_code=400, detail="Already answered")
   
    all_items = db.query(database_models.CATItem).all()
    cat_items = [
        CATItemClass(
            id=it.id, question=it.question,
            option_a=it.option_a, option_b=it.option_b,
            option_c=it.option_c, option_d=it.option_d,
            correct=it.correct, a=it.a, b=it.b, c=it.c
        ) for it in all_items
    ]
   
    engine = CATEngine(items=cat_items, initial_theta=session.current_theta)
    engine.current_theta = session.current_theta
   
    previous = db.query(database_models.CATItemResponse).filter(
        database_models.CATItemResponse.session_id == answer.session_id
    ).all()
    engine.administered_items = [r.item_id for r in previous]
    for resp in previous:
        engine.responses.append(CATResponse(
            item_id=resp.item_id, selected_option=resp.selected_option,
            is_correct=resp.is_correct, theta_before=resp.theta_before,
            theta_after=resp.theta_after, se_after=resp.se_after
        ))
   
    result = engine.process_response(answer.item_id, answer.selected_option)
   
    # Convert numpy values to standard Python types before creating the response object
    cat_response = database_models.CATItemResponse(
        session_id=answer.session_id,
        item_id=answer.item_id,
        selected_option=answer.selected_option.upper(),
        is_correct=bool(result["is_correct"]),
        response_time_seconds=int(answer.response_time_seconds),
        theta_before=float(session.current_theta) if session.current_theta is not None else None,
        theta_after=float(result["theta"]) if result["theta"] is not None else None,
        se_after=float(result["se"]) if result["se"] is not None else None
    )
    db.add(cat_response)
   
    # Convert numpy values to standard Python floats
    session.current_theta = float(result["theta"]) if result["theta"] is not None else None
    session.current_se = float(result["se"]) if result["se"] is not None else None
    session.num_items_administered = int(result["num_items"])
   
    item.used_count += 1
    if result["is_correct"]:
        item.correct_count += 1
   
    db.commit()
    db.refresh(session)
   
    return CATAnswerResponse(
        is_correct=result["is_correct"], current_theta=result["theta"],
        current_se=result["se"], items_completed=result["num_items"],
        should_continue=engine.should_continue()
    )
@app.post("/cat/complete", response_model=CATExamResults)
def complete_cat_exam(complete: CATExamComplete, db: Session = Depends(get_db)):
    """Complete exam and calculate final results"""
    session = db.query(database_models.CATSession).filter(
        database_models.CATSession.id == complete.session_id,
        database_models.CATSession.is_active == True
    ).first()
   
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
   
    all_items = db.query(database_models.CATItem).all()
    cat_items = [
        CATItemClass(
            id=it.id, question=it.question,
            option_a=it.option_a, option_b=it.option_b,
            option_c=it.option_c, option_d=it.option_d,
            correct=it.correct, a=it.a, b=it.b, c=it.c
        ) for it in all_items
    ]
   
    engine = CATEngine(items=cat_items, initial_theta=session.current_theta)
    engine.current_theta = session.current_theta
   
    responses = db.query(database_models.CATItemResponse).filter(
        database_models.CATItemResponse.session_id == session.id
    ).all()
    engine.administered_items = [r.item_id for r in responses]
    for resp in responses:
        engine.responses.append(CATResponse(
            item_id=resp.item_id, selected_option=resp.selected_option,
            is_correct=resp.is_correct, theta_before=resp.theta_before,
            theta_after=resp.theta_after, se_after=resp.se_after
        ))
   
    results = engine.get_final_results()
   
    session.completed_at = datetime.now()
    session.is_active = False
    session.final_theta = float(results["theta"]) if results["theta"] is not None else None
    session.final_se = float(results["se"]) if results["se"] is not None else None
    session.final_percentile = float(results["percentile"]) if results["percentile"] is not None else None
    session.num_correct = int(results["num_correct"]) if results["num_correct"] is not None else 0
    session.accuracy = float(results["accuracy"]) if results["accuracy"] is not None else 0.0
    application = db.query(database_models.Application).filter(
        database_models.Application.id == session.application_id
    ).first()
   
    if application:
        # Convert NumPy values to standard Python types
        application.cat_theta = float(results["theta"]) if results["theta"] is not None else None
        application.cat_percentile = float(results["percentile"]) if results["percentile"] is not None else None
        application.cat_completed = True

    try:
        CATEngine.recalibrate_item_bank(db, min_users=1)
        print("✓ Item bank recalibrated successfully")
    except Exception as e:
        print(f"⚠️ Recalibration warning: {e}")    
   
    db.commit()
   
    return CATExamResults(
        session_id=session.id, theta=results["theta"],
        se=results["se"], percentile=results["percentile"],
        num_items=results["num_items"], num_correct=results["num_correct"],
        accuracy=results["accuracy"], ability_level=results["ability_level"],
        completed_at=session.completed_at
    )
@app.get("/cat/session/{session_id}/status")
def get_cat_session_status(
    session_id: int, 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """Get session status"""
    session = db.query(database_models.CATSession).filter(
        database_models.CATSession.id == session_id
    ).first()
   
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
   
    return {
        "session_id": session.id, "is_active": session.is_active,
        "current_theta": session.current_theta,
        "current_se": session.current_se,
        "num_items_administered": session.num_items_administered,
        "started_at": session.started_at,
        "completed_at": session.completed_at
    }

@app.post("/cat/upload-questions")
async def upload_cat_questions(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Bulk upload CAT questions from Excel file.
    Expected columns: question, option_a, option_b, option_c, option_d, correct
    The 'correct' column accepts: A/B/C/D OR option_a/option_b/option_c/option_d
    Optional columns: a, b, c (IRT parameters)
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx, .xls)")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        # Validate required columns
        required_columns = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing_columns)}")
        
        # Insert items
        count = 0
        skipped = 0
        for idx, row in df.iterrows():
            # Validate and normalize correct answer format
            correct_raw = str(row['correct']).strip().lower()
            
            # Handle both formats: "A"/"B"/"C"/"D" and "option_a"/"option_b"/"option_c"/"option_d"
            if correct_raw in ['a', 'b', 'c', 'd']:
                correct = correct_raw.upper()
            elif correct_raw == 'option_a':
                correct = 'A'
            elif correct_raw == 'option_b':
                correct = 'B'
            elif correct_raw == 'option_c':
                correct = 'C'
            elif correct_raw == 'option_d':
                correct = 'D'
            else:
                # Skip invalid rows
                print(f"Skipping row {idx + 2} - invalid correct value: '{correct_raw}'")
                skipped += 1
                continue
            
            cat_item = database_models.CATItem(
                question=str(row['question']),
                option_a=str(row['option_a']),
                option_b=str(row['option_b']),
                option_c=str(row['option_c']),
                option_d=str(row['option_d']),
                correct=correct,
                a=float(row.get('a', 1.0)),
                b=float(row.get('b', 0.0)),
                c=float(row.get('c', 0.25)),
                used_count=0,
                correct_count=0
            )
            db.add(cat_item)
            count += 1
            
        db.commit()
        
        message = f"Successfully uploaded {count} questions"
        if skipped > 0:
            message += f" ({skipped} rows skipped due to invalid data)"
        
        return {"message": message, "uploaded": count, "skipped": skipped}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

# ============================================================
# CAT Items Management Endpoints (POST, PUT, DELETE)
# ============================================================

@app.post("/cat-items", response_model=CATItemSchema, status_code=status.HTTP_201_CREATED)
def create_cat_item(
    question: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct: str,
    a: float = 1.0,
    b: float = 0.0,
    c: float = 0.25,
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Create a new CAT question item.
    
    Parameters:
    - question: The question text
    - option_a: First option
    - option_b: Second option
    - option_c: Third option
    - option_d: Fourth option
    - correct: Correct answer (A, B, C, or D)
    - a: IRT discrimination parameter (default: 1.0)
    - b: IRT difficulty parameter (default: 0.0)
    - c: IRT guessing parameter (default: 0.25)
    """
    # Validate correct answer format
    correct_upper = correct.strip().upper()
    if correct_upper not in ['A', 'B', 'C', 'D']:
        raise HTTPException(
            status_code=400,
            detail="Correct answer must be one of: A, B, C, or D"
        )
    
    # Create new CAT item
    cat_item = database_models.CATItem(
        question=question.strip(),
        option_a=option_a.strip(),
        option_b=option_b.strip(),
        option_c=option_c.strip(),
        option_d=option_d.strip(),
        correct=correct_upper,
        a=a,
        b=b,
        c=c,
        used_count=0,
        correct_count=0
    )
    
    db.add(cat_item)
    db.commit()
    db.refresh(cat_item)
    
    print(f"✓ Created CAT item ID {cat_item.id}: {question[:50]}...")
    return cat_item


@app.put("/cat-items/{item_id}", response_model=CATItemSchema)
def update_cat_item(
    item_id: int,
    question: Optional[str] = None,
    option_a: Optional[str] = None,
    option_b: Optional[str] = None,
    option_c: Optional[str] = None,
    option_d: Optional[str] = None,
    correct: Optional[str] = None,
    a: Optional[float] = None,
    b: Optional[float] = None,
    c: Optional[float] = None,
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Update an existing CAT question item.
    
    Only provided fields will be updated. All parameters are optional.
    """
    # Get existing item
    cat_item = db.query(database_models.CATItem).filter(
        database_models.CATItem.id == item_id
    ).first()
    
    if not cat_item:
        raise HTTPException(status_code=404, detail="CAT item not found")
    
    # Check if item has been used in active sessions
    active_responses = db.query(database_models.CATItemResponse).filter(
        database_models.CATItemResponse.item_id == item_id
    ).count()
    
    if active_responses > 0:
        print(f"⚠️ Warning: Updating CAT item {item_id} which has {active_responses} existing responses")
    
    # Update fields if provided
    if question is not None:
        cat_item.question = question.strip()
    
    if option_a is not None:
        cat_item.option_a = option_a.strip()
    
    if option_b is not None:
        cat_item.option_b = option_b.strip()
    
    if option_c is not None:
        cat_item.option_c = option_c.strip()
    
    if option_d is not None:
        cat_item.option_d = option_d.strip()
    
    if correct is not None:
        correct_upper = correct.strip().upper()
        if correct_upper not in ['A', 'B', 'C', 'D']:
            raise HTTPException(
                status_code=400,
                detail="Correct answer must be one of: A, B, C, or D"
            )
        cat_item.correct = correct_upper
    
    if a is not None:
        cat_item.a = a
    
    if b is not None:
        cat_item.b = b
    
    if c is not None:
        cat_item.c = c
    
    db.commit()
    db.refresh(cat_item)
    
    print(f"✓ Updated CAT item ID {item_id}")
    return cat_item


@app.delete("/cat-items/{item_id}")
def delete_cat_item(
    item_id: int, 
    db: Session = Depends(get_db), 
    token: auth.TokenData = Depends(auth.get_current_admin)
):
    """
    Delete a CAT question item.
    
    Note: This will fail if the item has been used in any exam sessions
    due to foreign key constraints. Consider soft deletion for production.
    """
    # Get existing item
    cat_item = db.query(database_models.CATItem).filter(
        database_models.CATItem.id == item_id
    ).first()
    
    if not cat_item:
        raise HTTPException(status_code=404, detail="CAT item not found")
    
    # Check if item has been used in any sessions
    existing_responses = db.query(database_models.CATItemResponse).filter(
        database_models.CATItemResponse.item_id == item_id
    ).count()
    
    if existing_responses > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete CAT item. It has been used in {existing_responses} exam responses. "
                   f"Consider deactivating or archiving instead."
        )
    
    # Delete the item
    db.delete(cat_item)
    db.commit()
    
    print(f"✓ Deleted CAT item ID {item_id}")
    return {
        "message": "CAT item deleted successfully",
        "item_id": item_id,
        "question": cat_item.question[:50] + "..." if len(cat_item.question) > 50 else cat_item.question
    }


# ============================================================
# AWS S3 File Upload Endpoint – FIXED FOR 2025 (No ACLs!)
# ============================================================
@app.post("/upload-to-s3")
async def upload_to_s3_endpoint(file: UploadFile = File(...)):
    result = await s3_service.upload_file(file)
    return {
        "message": "Uploaded successfully",
        "key": result["key"],
        "filename": result["filename"]
    }


@app.get("/s3/get-url")
def get_file_url_endpoint(key: str):
    url = s3_service.get_presigned_url(key)
    return {"url": url}


# ============================================================
# Gemini Chat Model Endpoint (Public - for AI responses in recruitment flow)
# ============================================================
@app.post("/gemini/chat/")
def chat_with_gemini(
    request_text: str,
    model_name: str = "gemini-2.5-flash", # Default model; can be overridden
):
    """
    Send text to Gemini model and get response.
    Useful for AI-generated feedback, interview questions, etc.
    """
    if not request_text or len(request_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Request text cannot be empty")
   
    try:
        # Configure model
        model = genai.GenerativeModel(model_name)
       
        # Generate response (simple chat; extend for history if needed)
        response = model.generate_content(request_text)
       
        # Extract text response
        generated_text = response.text
       
        print(f"✓ Gemini response generated for: {request_text[:50]}...")
        return {
            "request_text": request_text,
            "response_text": generated_text,
            "model_used": model_name,
            "safety_ratings": [
                {"category": rating.category.name, "probability": rating.probability.name}
                for rating in response.prompt_feedback.safety_ratings
            ] if response.prompt_feedback else [],
        }
   
    except Exception as e:
        print(f"✗ Gemini API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat generation failed: {str(e)}")
 
@app.put("/start-exam/{email}/{hr_video_exam_key}")
def start_exam(email: str, hr_video_exam_key: str, db: Session = Depends(get_db)):
    # 1) Validate email + HR video exam key against Application table
    application = (
        db.query(database_models.Application)
        .filter(
            database_models.Application.email == email.lower(),
            database_models.Application.hr_video_exam_key == hr_video_exam_key
        )
        .first()
    )
    if application.hr_exam_completed:
        raise HTTPException(status_code=403, detail="Exam already completed")
    if not application:
        raise HTTPException(status_code=401, detail="Invalid email or exam key")
    # 3) Fetch job details
    job = db.query(database_models.Job).filter(database_models.Job.id == application.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # 4) Fetch related HR video questions (JobVideoQuestion with embedded VideoQuestion)
    job_video_questions = db.query(database_models.JobVideoQuestion).filter(
        database_models.JobVideoQuestion.job_id == application.job_id
    ).options(joinedload(database_models.JobVideoQuestion.video_question)).all()
    if not job_video_questions:
        raise HTTPException(status_code=404, detail="No video questions linked to this job")
    # FIXED: Return JobVideoQuestion.id as 'id', with question details
    video_questions = [
        {
            "id": jvq.id,  # Now correct: job_video_question_id
            "question_text": jvq.video_question.question_text,
            "duration_seconds": jvq.video_question.duration_seconds,
        }
        for jvq in job_video_questions
    ]
    # 5) (Optional) Mark exam as started
    # application.hr_exam_started = True
    # application.hr_exam_started_at = datetime.now()
    # db.commit()
    # 6) Return exam details
    return {
        "job_id": job.id,
        "job_title": job.title,
        "video_questions": video_questions,
        "application_id": application.id
    }

# Helper function to download resume from URL
def download_file_from_url(url: str) -> Optional[bytes]:
    """Download file from various URL types (Google Drive, GCS, Direct,intershalla)"""
    print(f"📥 Downloading from: {url[:60]}...")
    
    # Convert Google Drive URLs
    if 'drive.google.com' in url:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            file_id = match.group(1)
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            print(f"  → Converted to direct download URL")
    
    # Convert Google Docs URLs
    elif 'docs.google.com/document' in url:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            doc_id = match.group(1)
            url = f"https://docs.google.com/document/d/{doc_id}/export?format=pdf"
            print(f"  → Converted to PDF export URL")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        content = response.content
        
        # Check if we got HTML instead of file
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html'):
            print(f"✗ Received HTML instead of file. Check URL permissions.")
            return None
        
        print(f"✓ Downloaded {len(content)} bytes")
        return content
        
    except Exception as e:
        print(f"✗ Download error: {e}")
        return None


# Helper function to format job data for Gemini
def format_job_for_scoring(job: database_models.Job) -> str:
    """Format job data into text for Gemini scoring"""
    
    return f"""
JOB POSTING: {job.title}
Job Code: {job.job_code}
Department: {job.department}
Location: {job.location}
Type: {job.type.upper()}
Experience Level: {job.experience_level.upper()}

{'='*60}
REQUIRED SKILLS:
{'='*60}
{', '.join(job.required_skills or [])}

PREFERRED SKILLS:
{', '.join(job.preferred_skills or [])}

{'='*60}
EDUCATION REQUIREMENTS:
{'='*60}
{job.education_requirement or 'Not specified'}
Minimum Academic Score: {job.minimum_academic_score or 'Not specified'}

{'='*60}
JOB DESCRIPTION:
{'='*60}
{job.description or 'Not provided'}

RESPONSIBILITIES:
{job.responsibilities or 'Not provided'}

KEYWORDS: {', '.join(job.keywords or [])}
"""


def score_resume_with_gemini_text(resume_text: str, job_description: str) -> dict:
    """
    Score resume using Gemini text-based model with 5 scoring dimensions.
    Uses the existing chat_with_gemini function.
    
    Returns: dict with all 5 scores and analysis
    """
    
    print(f"🤖 Scoring resume with Gemini...")
    
    prompt = f"""You are an expert HR recruiter. Analyze this resume against the job description and provide detailed scoring.


{job_description}


{'='*80}
RESUME CONTENT:
{'='*80}
{resume_text}


{'='*80}
SCORING INSTRUCTIONS:
{'='*80}


Please analyze the resume and provide:


1. **RESUME SCORE**: Overall fit score from 0-100
2. **SKILLS MATCH SCORE**: Percentage (0-100) of how many required skills are present
3. **EXPERIENCE MATCH SCORE**: Percentage (0-100) based on years of experience and relevance
4. **EDUCATION MATCH SCORE**: Percentage (0-100) based on degree and educational background
5. **CERTIFICATION MATCH SCORE**: Percentage (0-100) based on relevant certifications/credentials
6. **KEY STRENGTHS**: 3-5 relevant strengths
7. **GAPS/WEAKNESSES**: 2-3 areas of concern
8. **RECOMMENDATION**: Proceed (Yes/No/Maybe)


Format your response EXACTLY like this:


OVERALL_SCORE: [number between 0-100]
SKILLS_MATCH: [number between 0-100]
EXPERIENCE_MATCH: [number between 0-100]
EDUCATION_MATCH: [number between 0-100]
CERTIFICATION_MATCH: [number between 0-100]


STRENGTHS:
- [Strength 1]
- [Strength 2]
- [Strength 3]


WEAKNESSES:
- [Weakness 1]
- [Weakness 2]


RECOMMENDATION: [Yes/No/Maybe]


DETAILED ANALYSIS:
[Your detailed analysis here]
"""
    
    try:
        # Use existing chat_with_gemini function
        result = chat_with_gemini(
            request_text=prompt,
            model_name="gemini-2.5-flash"
        )
        
        response_text = result["response_text"]
        
        # Parse all 5 scores from response
        scores = {
            "overall_score": 50,
            "skills_match_score": 0,
            "experience_match_score": 0,
            "education_match_score": 0,
            "certification_match_score": 0
        }
        
        # Extract OVERALL_SCORE
        overall_match = re.search(r'OVERALL_SCORE:\s*(\d+)', response_text, re.IGNORECASE)
        if overall_match:
            scores["overall_score"] = max(0, min(100, int(overall_match.group(1))))
        
        # Extract SKILLS_MATCH
        skills_match = re.search(r'SKILLS_MATCH:\s*(\d+)', response_text, re.IGNORECASE)
        if skills_match:
            scores["skills_match_score"] = max(0, min(100, int(skills_match.group(1))))
        
        # Extract EXPERIENCE_MATCH
        exp_match = re.search(r'EXPERIENCE_MATCH:\s*(\d+)', response_text, re.IGNORECASE)
        if exp_match:
            scores["experience_match_score"] = max(0, min(100, int(exp_match.group(1))))
        
        # Extract EDUCATION_MATCH
        edu_match = re.search(r'EDUCATION_MATCH:\s*(\d+)', response_text, re.IGNORECASE)
        if edu_match:
            scores["education_match_score"] = max(0, min(100, int(edu_match.group(1))))
        
        # Extract CERTIFICATION_MATCH
        cert_match = re.search(r'CERTIFICATION_MATCH:\s*(\d+)', response_text, re.IGNORECASE)
        if cert_match:
            scores["certification_match_score"] = max(0, min(100, int(cert_match.group(1))))
        
        print(f"✓ Resume scored:")
        print(f"  - Overall: {scores['overall_score']}/100")
        print(f"  - Skills Match: {scores['skills_match_score']}%")
        print(f"  - Experience Match: {scores['experience_match_score']}%")
        print(f"  - Education Match: {scores['education_match_score']}%")
        print(f"  - Certification Match: {scores['certification_match_score']}%")
        
        return {
            "overall_score": scores["overall_score"],
            "skills_match_score": scores["skills_match_score"],
            "experience_match_score": scores["experience_match_score"],
            "education_match_score": scores["education_match_score"],
            "certification_match_score": scores["certification_match_score"],
            "analysis": response_text,
            "model_used": result["model_used"]
        }
        
    except Exception as e:
        print(f"✗ Gemini scoring error: {e}")
        return {
            "overall_score": 0,
            "skills_match_score": 0,
            "experience_match_score": 0,
            "education_match_score": 0,
            "certification_match_score": 0,
            "analysis": f"Error during scoring: {str(e)}",
            "model_used": "error"
        }

@app.post("/applications/bulk-upload")
async def bulk_upload_applications(
    file: UploadFile = File(...),
    job_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Bulk upload applications from Excel with resume scoring.
    
    Expected Excel columns:
    - full_name (required)
    - email (required)
    - phone_number (required)
    - resume_url (required) - Google Drive/Docs/GCS/Direct URLs
    - linkedin_profile (optional)
    - portfolio_github (optional)
    - specialization (optional)
    
    Process for each row:
    1. Download resume from URL
    2. Upload to AWS S3 (gets S3 key)
    3. Extract text from resume
    4. Score with Gemini against job description (gets all 5 scores)
    5. Create application with all scores and S3 key
    
    Returns: Summary with successful/failed uploads
    """
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls)")
    
    # Validate and get job
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id is required")
    
    job = db.query(database_models.Job).filter(database_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    print(f"\n{'='*80}")
    print(f"📋 BULK APPLICATION UPLOAD STARTED")
    print(f"{'='*80}")
    print(f"Job ID: {job_id}")
    print(f"Job Title: {job.title}")
    print(f"Job Code: {job.job_code}")
    print(f"File: {file.filename}")
    print(f"{'='*80}\n")
    
    # Format job description for Gemini
    job_description = format_job_for_scoring(job)
    
    try:
        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        print(f"Total rows in Excel: {len(df)}")
        print(f"Columns: {list(df.columns)}\n")
        
        # Validate required columns
        required_columns = ['full_name', 'email', 'phone_number', 'resume_url']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        successful_uploads = []
        failed_uploads = []
        
        total_rows = len(df)
        
        # Process each row
        for idx, row in df.iterrows():
            candidate_num = idx + 1
            print(f"\n{'─'*80}")
            print(f"[{candidate_num}/{total_rows}] Processing: {row['full_name']}")
            print(f"{'─'*80}")
            
            try:
                # Validate required fields
                if pd.isna(row['full_name']) or not str(row['full_name']).strip():
                    raise ValueError("Full name is empty")
                
                if pd.isna(row['email']) or '@' not in str(row['email']):
                    raise ValueError("Invalid email address")
                
                if pd.isna(row['resume_url']) or not str(row['resume_url']).strip():
                    raise ValueError("Resume URL is empty")
                
                resume_url = str(row['resume_url']).strip()
                full_name = str(row['full_name']).strip()
                
                # Generate safe filename
                safe_name = full_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                timestamp = int(datetime.now().timestamp())
                resume_filename = f"{safe_name}_resume_{timestamp}.pdf"
                
                # ===== STEP 1: Download Resume =====
                print(f"[1/5] Downloading resume...")
                resume_content = download_file_from_url(resume_url)
                
                if not resume_content:
                    raise ValueError("Failed to download resume from URL")
                
                if len(resume_content) < 100:
                    raise ValueError("Downloaded file is too small (likely error)")
                
                # ===== STEP 2: Upload to AWS S3 =====
                print(f"[2/5] Uploading to AWS S3...")
                
                import tempfile
                import os
                temp_path = f"/tmp/{resume_filename}"
                
                with open(temp_path, 'wb') as temp_file:
                    temp_file.write(resume_content)
                
                # Upload using your existing S3 service
                with open(temp_path, 'rb') as temp_file:
                    upload_file = UploadFile(filename=resume_filename, file=temp_file)
                    s3_result = await s3_service.upload_file(upload_file)
                
                s3_key = s3_result["key"]
                s3_filename = s3_result["filename"]
                
                print(f"  ✓ Uploaded to S3")
                print(f"  ✓ S3 Key: {s3_key}")
                
                # ===== STEP 3: Extract Text from Resume =====
                print(f"[3/5] Extracting text from resume...")
                
                # Parse text from the temp file BEFORE deleting it
                parsed_resume = ResumeParser.parse_resume(temp_path)
                extracted_text = parsed_resume.get("raw_text", "") or ""
                
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                resume_text = f"""
Resume for: {full_name}
Email: {row['email']}
Phone: {row['phone_number']}
LinkedIn: {row.get('linkedin_profile', 'Not provided')}
Portfolio/GitHub: {row.get('portfolio_github', 'Not provided')}
Specialization: {row.get('specialization', 'Not provided')}

RESUME CONTENT:
{extracted_text[:50000]} 

[Note: Full resume stored in S3 at {s3_key}]
"""
                
                # ===== STEP 4: Score with Gemini (ALL 5 SCORES) =====
                print(f"[4/5] Scoring with Gemini AI...")
                
                scoring_result = score_resume_with_gemini_text(
                    resume_text=resume_text,
                    job_description=job_description
                )
                
                # Extract all 5 scores
                overall_score = scoring_result["overall_score"]
                skills_match_score = scoring_result["skills_match_score"]
                experience_match_score = scoring_result["experience_match_score"]
                education_match_score = scoring_result["education_match_score"]
                certification_match_score = scoring_result["certification_match_score"]
                ai_analysis = scoring_result["analysis"]
                
                print(f"  ✓ All scores retrieved:")
                print(f"    - Overall: {overall_score}/100")
                print(f"    - Skills: {skills_match_score}%")
                print(f"    - Experience: {experience_match_score}%")
                print(f"    - Education: {education_match_score}%")
                print(f"    - Certifications: {certification_match_score}%")
                
                # ===== STEP 5: Create Application in DB =====
                print(f"[5/5] Creating application in database...")
                
                db_application = database_models.Application(
                    job_id=job_id,
                    full_name=full_name,
                    email=str(row['email']).strip().lower(),
                    phone_number=str(row['phone_number']).strip(),
                    linkedin_profile=str(row.get('linkedin_profile', '')).strip() or None,
                    portfolio_github=str(row.get('portfolio_github', '')).strip() or None,
                    resume_path=s3_key,  # Store S3 key
                    specialization=str(row.get('specialization', '')).strip() or None,
                    resume_score=float(overall_score),                      # Overall score
                    skills_match_score=float(skills_match_score),           # Skills match ✅
                    experience_match_score=float(experience_match_score),   # Experience match ✅
                    education_match_score=float(education_match_score),     # Education match ✅
                    certification_match_score=float(certification_match_score),  # Certification match ✅
                    current_stage="applied"
                )
                
                db.add(db_application)
                db.flush()  # Get ID without full commit
                
                print(f"  ✓ Application created (ID: {db_application.id})")
                print(f"  ✓ Resume Score: {overall_score}/100")
                print(f"  ✓ S3 Path: {s3_key}")
                
                successful_uploads.append({
                    "row": candidate_num,
                    "name": full_name,
                    "email": row['email'],
                    "application_id": db_application.id,
                    "resume_score": overall_score,
                    "skills_match_score": skills_match_score,
                    "experience_match_score": experience_match_score,
                    "education_match_score": education_match_score,
                    "certification_match_score": certification_match_score,
                    "s3_key": s3_key,
                    "s3_filename": s3_filename
                })
                
            except Exception as e:
                print(f"  ✗ Failed: {str(e)}")
                failed_uploads.append({
                    "row": candidate_num,
                    "name": row.get('full_name', 'Unknown'),
                    "email": row.get('email', 'Unknown'),
                    "error": str(e)
                })
                db.rollback()
                continue
        
        # Commit all successful applications at once
        if successful_uploads:
            db.commit()
            print(f"\n✓ Committed {len(successful_uploads)} applications to database")
        
        # Calculate average scores ✅
        if successful_uploads:
            avg_overall = sum(u["resume_score"] for u in successful_uploads) / len(successful_uploads)
            avg_skills = sum(u["skills_match_score"] for u in successful_uploads) / len(successful_uploads)
            avg_exp = sum(u["experience_match_score"] for u in successful_uploads) / len(successful_uploads)
            avg_edu = sum(u["education_match_score"] for u in successful_uploads) / len(successful_uploads)
            avg_cert = sum(u["certification_match_score"] for u in successful_uploads) / len(successful_uploads)
            
            print(f"\nAverage Scores (for successful uploads):")
            print(f"  - Overall: {avg_overall:.1f}/100")
            print(f"  - Skills: {avg_skills:.1f}%")
            print(f"  - Experience: {avg_exp:.1f}%")
            print(f"  - Education: {avg_edu:.1f}%")
            print(f"  - Certifications: {avg_cert:.1f}%")
        
        # Print final summary
        print(f"\n{'='*80}")
        print(f"BULK UPLOAD COMPLETED")
        print(f"{'='*80}")
        print(f"Total Rows: {total_rows}")
        print(f"✓ Successful: {len(successful_uploads)}")
        print(f"✗ Failed: {len(failed_uploads)}")
        
        if failed_uploads:
            print(f"\nFailed Uploads:")
            for fail in failed_uploads[:5]:  # Show first 5
                print(f"  - Row {fail['row']}: {fail['name']} - {fail['error']}")
        
        print(f"{'='*80}\n")
        
        return {
            "message": f"Processed {total_rows} applications",
            "total": total_rows,
            "successful": len(successful_uploads),
            "failed": len(failed_uploads),
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "job": {
                "id": job.id,
                "title": job.title,
                "code": job.job_code
            }
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        print(f"\n{'='*80}")
        print(f"✗ CRITICAL ERROR")
        print(f"{'='*80}")
        print(error_detail)
        print(f"{'='*80}\n")
        raise HTTPException(status_code=500, detail=str(e))

# Run Server
# ============================================================

# ============================================================
# JOB VIDEO QUESTIONS - CRUD
# ============================================================

@app.get("/job-video-questions/{mapping_id}", response_model=JobVideoQuestionResponse)
def get_job_video_question(mapping_id: int, db: Session = Depends(get_db)):
    mapping = db.query(database_models.JobVideoQuestion).filter(
        database_models.JobVideoQuestion.id == mapping_id
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Job video question mapping not found")
    return mapping


@app.put("/job-video-questions/{mapping_id}", response_model=JobVideoQuestionResponse)
def update_job_video_question(
    mapping_id: int,
    mapping_update: JobVideoQuestionUpdate,
    db: Session = Depends(get_db)
):
    db_mapping = db.query(database_models.JobVideoQuestion).filter(
        database_models.JobVideoQuestion.id == mapping_id
    ).first()
    if not db_mapping:
        raise HTTPException(status_code=404, detail="Job video question mapping not found")
    
    if mapping_update.display_order is not None:
        db_mapping.display_order = mapping_update.display_order
        
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


@app.delete("/job-video-questions/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_video_question(mapping_id: int, db: Session = Depends(get_db)):
    db_mapping = db.query(database_models.JobVideoQuestion).filter(
        database_models.JobVideoQuestion.id == mapping_id
    ).first()
    if not db_mapping:
        raise HTTPException(status_code=404, detail="Job video question mapping not found")
        
    db.delete(db_mapping)
    db.commit()
    return None


@app.get("/job-video-questions", response_model=List[JobVideoQuestionResponse])
def list_job_video_questions(
    job_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(database_models.JobVideoQuestion)
    if job_id:
        query = query.filter(database_models.JobVideoQuestion.job_id == job_id)
    return query.all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
