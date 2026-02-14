# AI Recruitment System - Backend

This is the backend API for the AI Recruitment System, built with FastAPI. It handles job management, candidate applications, automated scoring, CAT (Computerized Adaptive Testing) exams, and video interviews.

## Features

- **Job Management**: Create, update, list, and delete job postings.
- **Application Workflow**: Public submission of applications with resume parsing and automated scoring.
- **CAT Exam Engine**: Computerized Adaptive Testing system for candidate evaluation.
- **Video Interviews**: Automated video interview question assignment and response tracking.
- **Email Service**: Automated email notifications for exam invitations and application status updates via Gmail SSL.
- **HR Dashboard Support**: Endpoints for HR controls and bulk application status updates.

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy with SQLite (default)
- **Email**: smtplib (SSL)
- **AI/ML**: Google Gemini API (for scoring/parsing)
- **File Storage**: AWS S3 (via Boto3)
- **Authentication**: JWT (Jose)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Recruitment_Module_Backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root directory and add the following:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   FROM_EMAIL=your_email@gmail.com
   EXAM_URL=http://localhost:3000/exam/login
   ADMIN_EMAIL=admin@pulsepharma.com
   ADMIN_PASSWORD=pavan@123
   AWS_ACCESS_KEY_ID=your_aws_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   AWS_REGION=your_aws_region
   S3_BUCKET_NAME=your_bucket_name
   ```

## Running the Application

Start the FastAPI server:
```bash
python main.py
```
The backend will run on `http://0.0.0.0:8001`.

## API Documentation

Once the server is running, you can access the interactive API docs:
- Swagger UI: `http://localhost:8001/docs`
- Redoc: `http://localhost:8001/redoc`
