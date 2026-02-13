import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta



import os
from dotenv import load_dotenv

load_dotenv()

# =============================
# CONFIGURATION
# =============================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
EMAIL_ADDRESS = os.getenv("SMTP_USER")
EMAIL_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_NAME = "Pulse Pharmaceuticals Private Limited"
FOOTER_IMAGE_PATH = "Footer.jpg"        # Place this file in your project root
FOOTER_CID = "footer_image"
EXAM_URL = os.getenv("EXAM_URL", "http://localhost:3000/exam/login")



def send_recruitment_email(
    candidate_name: str,
    candidate_email: str,
    stage: str,
    key: Optional[str] = None,
    job_title: str = "Position",
    exam_url: str = EXAM_URL,
    custom_message: Optional[str] = None
) -> bool:
    """
    Send professional recruitment email with embedded footer image.
    Used by bulk-status-simple endpoint.
    """
    stage = stage.lower().strip()
    
    # Compute deadline = today + 2 days
    deadline_date = (datetime.today() + timedelta(days=2)).strftime("%d %B %Y")
    
    subject = ""
    html_body = ""



    # =============================
    # STAGE-SPECIFIC TEMPLATES
    # =============================



    if stage == "aptitude":
        subject = f"First Round Exam Invitation – {job_title} | {FROM_NAME}"
        html_body = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; line-height: 1.8; max-width: 680px; margin: auto; background:#f8fafc; padding:20px;">
            <div style="background:white; border-radius:16px; padding:45px; box-shadow:0 10px 30px rgba(0,0,0,0.08);">
              <div style="text-align:center; padding-bottom:20px; border-bottom:4px solid #3498db;">
                <h1 style="color:#3498db; margin:0; font-size:32px;">{FROM_NAME}</h1>
                <p style="color:#7f8c8d; margin:8px 0 0;">First Round Assessment</p>
              </div>



              <h2 style="color:#2c3e50; margin-top:30px;">Hello {candidate_name},</h2>
              <p>Congratulations! You have been shortlisted for the <strong>First Round Exam</strong> for <strong>{job_title}</strong>.</p>



              <div style="background:linear-gradient(135deg, #3498db, #2980b9); color:white; padding:28px; border-radius:12px; margin:30px 0;">
                <h3 style="margin:0 0 15px 0; font-size:20px;">Exam Details</h3>
                <ul style="margin:0; padding-left:22px; font-size:16px;">
                  <li><strong>Platform:</strong> <a href="{exam_url}" style="color:#fff; text-decoration:underline;">Click here to login</a></li>
                  <li><strong>Date & Time:</strong> Tomorrow, 10:00 AM - 6:00 PM</li>
                  <li><strong>Duration:</strong> 30 minutes</li>
                  <li><strong>Format:</strong> Aptitude Question</li>
                </ul>
              </div>



              <div style="background:#f0f8ff; padding:25px; border-radius:12px; text-align:center; border:2px dashed #3498db; word-wrap: break-word; overflow-wrap: break-word;">
                <p style="margin:0 0 15px; font-size:18px; color:#2c3e50;"><strong>Your Access Key</strong></p>
                <div style="background:white; display:inline-block; padding:16px 24px; border-radius:10px; 
                     font-family:'Courier New', monospace; font-size:20px; letter-spacing:3px; 
                     border:3px solid #3498db; color:#2c3e50; max-width:100%; word-break: break-all; word-wrap: break-word;">
                  <strong>{key}</strong>
                </div>
                <p style="margin:15px 0 0; font-size:13px; color:#e74c3c;">
                  Keep this key confidential • Do not share with anyone
                </p>
              </div>



              <div style="background:#fff8e1; padding:20px; border-left:5px solid #f39c12; margin:25px 0; border-radius:8px;">
                <h4 style="margin:0 0 12px 0; color:#e67e22;">Important Instructions</h4>
                <ol style="margin:0; padding-left:20px; color:#2c3e50;">
                  <li>Join 5 minutes before start time</li>
                  <li>Use laptop/desktop with stable internet</li>
                  <li>This is a <strong>proctored exam</strong> — webcam required</li>
                </ol>
              </div>



              <div style="text-align:center; margin:35px 0;">
                <a href="{exam_url}" style="background:#3498db; color:white; padding:16px 48px; text-decoration:none; 
                     border-radius:50px; font-weight:bold; font-size:18px; display:inline-block;">
                  Open Exam Portal
                </a>
              </div>



              <p style="color:#7f8c8d; font-size:14px;">Best of luck! You've got this!</p>



              <img src="cid:{FOOTER_CID}" alt="PulsePharma" style="max-width:100%; height:auto; margin-top:40px; border-radius:12px;">
            </div>
          </body>
        </html>
        """



    elif stage == "video_hr":
        subject = f"Video Interview Invitation – {job_title} | {FROM_NAME}"
        html_body = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #2c3e50; line-height: 1.8; max-width: 680px; margin: auto; background:#f8fafc; padding:20px;">
            <div style="background:white; border-radius:16px; padding:45px; box-shadow:0 10px 30px rgba(0,0,0,0.08);">
              <h2 style="color:#27ae60; text-align:center; font-size:28px;">Congratulations {candidate_name.split()[0]}!</h2>
              <p style="text-align:center; font-size:17px;">
                You have successfully cleared the aptitude round and are now invited to complete the
                <strong>Video HR Interview</strong>.
              </p>

              <div style="background:#27ae60; color:white; padding:25px; border-radius:12px; margin:30px 0;">
                <p style="margin:0 0 8px 0; font-size:18px;"><strong>Access Key</strong></p>
                <div style="background:rgba(255,255,255,0.2); padding:12px; border-radius:8px; text-align:center; font-family:monospace; font-size:20px; letter-spacing:3px; word-break: break-all;">
                  {key}
                </div>
                <p style="margin:15px 0 0; font-size:14px;">
                  Please do not share this key with anyone. It is unique to your profile.
                </p>
              </div>

              <div style="background:#f0f8ff; padding:20px; border-radius:10px; border-left:5px solid #3498db; margin-bottom:25px;">
                <h3 style="margin-top:0; color:#2c3e50;">Video Interview Timeline</h3>
                <ul style="margin:0; padding-left:20px; color:#2c3e50;">
                  <li>You may complete the Video HR Interview at any time convenient to you.</li>
                  <li><strong>Deadline to complete the interview: {deadline_date}</strong>.</li>
                  <li>After this date, the interview link may no longer be accessible.</li>
                </ul>
              </div>

              <p><strong>Login here:</strong> <a href="{exam_url}">{exam_url}</a></p>
              <p>You will be asked to record video responses to a few HR questions. Please ensure you complete all questions in one sitting.</p>

              <div style="background:#e8f5e8; padding:20px; border-radius:10px; border-left:5px solid #27ae60;">
                <p style="margin:0;">
                  <strong>Tips for a good recording:</strong> Use good lighting, a quiet environment, and maintain professional attire and body language.
                </p>
              </div>

              <img src="cid:{FOOTER_CID}" style="max-width:100%; height:auto; margin-top:40px; border-radius:12px;">
            </div>
          </body>
        </html>
        """



    elif stage == "applied":
        subject = f"Application Received – Thank You, {candidate_name.split()[0]}!"
        html_body = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="font-family: Arial; max-width: 650px; margin: auto; padding: 20px; background: #f9f9f9;">
            <div style="background: white; padding: 40px; border-radius: 12px; text-align: center;">
              <h2>Thank You for Applying!</h2>
              <p>Hello <strong>{candidate_name}</strong>,</p>
              <p>We have successfully received your application for <strong>{job_title}</strong>.</p>
              <p>Our team is reviewing your profile and you'll hear from us soon.</p>
              <p>Stay excited — great opportunities await!</p>
              <img src="cid:{FOOTER_CID}" style="max-width:100%; margin-top:40px; border-radius:12px;">
            </div>
          </body>
        </html>
        """


    elif stage in ["final_interview", "final interview"]:
        subject = "Final Round Interview"
        html_body = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="font-family: Arial, sans-serif; padding: 30px; background:#f0f8ff;">
            <div style="max-width:650px; margin:auto; background:white; padding:40px; border-radius:14px;">
              
              <h2 style="color:#2c3e50; margin-top:0;">Dear {candidate_name},</h2>

              <p>
                Thank you for your continued interest in the opportunity with us.
              </p>

              <p>
                We are pleased to inform you that the <strong>final round of interviews</strong> 
                will be held on <strong>Monday, January 5 at 10:00 AM</strong>.
              </p>

              <p>
                During this round, you will be given a 
                <strong>case study focused on AI agents</strong>, which you will be expected to 
                review and discuss with the panel.
              </p>

              <p>
                Please go through the AI Agents roadmap using the resource below:
              </p>
              <p style="margin:6px 0;">
                <a href="https://roadmap.sh/ai-agents">
                Click here for AI Agents Resource</a>
              </p>

              <h3 style="margin-top:25px; color:#2c3e50;">Venue & Location</h3>
              <p style="margin:6px 0;">
                <strong>Pulse Pharmaceuticals Private Limited, Hyderabad</strong>
              </p>
              <p style="margin:6px 0;">
                📍 <a href="https://maps.app.goo.gl/gos7279BCfCc1zLX9?g_st=aw">
                Click here for the location</a>
              </p>

              <p style="margin-top:25px;">
                Kindly reply to confirm your availability for the final round. 
                If you have any questions, feel free to reach out.
              </p>

              <p style="margin-top:20px;">
                We look forward to meeting you.
              </p>

              <p style="margin-top:20px;">
                Best regards,<br>
                Talent Acquisition Team<br>
                {FROM_NAME}
              </p>

              <img src="cid:{FOOTER_CID}" alt="Footer" 
                   style="max-width:100%; margin-top:35px; border-radius:12px;">
            </div>
          </body>
        </html>
        """


    elif stage == "hired":
        subject = f"Welcome to {FROM_NAME}! Offer Extended"
        html_body = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="font-family:Arial; background:#e8f5e8; padding:20px;">
            <div style="max-width:650px; margin:auto; background:white; padding:50px; border-radius:16px; text-align:center;">
              <h1 style="color:#27ae60;">Welcome Aboard, {candidate_name}!</h1>
              <p style="font-size:18px;">We are thrilled to extend a job offer for <strong>{job_title}</strong>!</p>
              <p>Your offer letter and joining details will be shared soon.</p>
              <p>Welcome to the {FROM_NAME} family!</p>
              <img src="cid:{FOOTER_CID}" style="max-width:100%; margin-top:40px; border-radius:12px;">
            </div>
          </body>
        </html>
        """



    elif stage == "rejected":
        subject = f"Application Status Update – {job_title}"
        html_body = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="font-family:Arial, sans-serif; padding:20px; background:#f5f5f5;">
            <div style="max-width:650px; margin:auto; background:white; padding:40px; border-radius:12px;">
              <p style="font-size:16px;">Dear {candidate_name},</p>

              <p style="font-size:16px;">
                Thank you for taking the time to participate in the recruitment process for the
                <strong>{job_title}</strong> role at {FROM_NAME}.
              </p>

              <p style="font-size:16px;">
                After careful consideration of your profile and interview performance, we regret to inform you that
                you have not been selected to progress further in the current hiring process.
              </p>

              <p style="font-size:16px;">
                This decision was not easy, as we received applications from many talented candidates. We truly
                appreciate your interest in {FROM_NAME} and the effort you invested in exploring a career with us.
              </p>

              <p style="font-size:16px;">
                We encourage you to stay connected with us and apply again in the future for roles that match your
                skills and experience.
              </p>

              <p style="font-size:16px; margin-top:25px;">
                Wishing you all the very best in your future endeavors.
              </p>

              <p style="font-size:16px; margin-top:10px;">
                Sincerely,<br>
                Talent Acquisition Team<br>
                {FROM_NAME}
              </p>

              <img src="cid:{FOOTER_CID}" style="max-width:100%; margin-top:30px; border-radius:12px;">
            </div>
          </body>
        </html>
        """



    else:
        # Generic fallback
        subject = f"Application Update – {job_title}"
        html_body = f"""
        <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
          </head>
          <body style="font-family:Arial; background:#f9f9f9; padding:20px;">
            <div style="max-width:600px; margin:auto; background:white; padding:40px; border-radius:12px;">
              <h2>Hello {candidate_name},</h2>
              <p>Your application for <strong>{job_title}</strong> has been updated to: <strong>{stage.replace('_', ' ').title()}</strong></p>
              {f"<p>{custom_message}</p>" if custom_message else ""}
              <img src="cid:{FOOTER_CID}" style="max-width:100%; margin-top:30px;">
            </div>
          </body>
        </html>
        """



    # =============================
    # SEND EMAIL WITH EMBEDDED IMAGE
    # =============================
    msg = EmailMessage()
    msg["From"] = f"{FROM_NAME} <{EMAIL_ADDRESS}>"
    msg["To"] = candidate_email
    msg["Subject"] = subject
    msg.add_alternative(html_body, subtype="html")



    # Attach Footer.jpg as inline image
    footer_path = Path(FOOTER_IMAGE_PATH)
    if footer_path.exists():
        with open(footer_path, "rb") as img:
            img_data = img.read()
            msg.get_payload()[0].add_related(img_data, maintype='image', subtype='jpeg', cid=FOOTER_CID)
    else:
        print(f"Warning: Footer image not found: {FOOTER_IMAGE_PATH}")



    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent → {candidate_name} ({candidate_email}) | Stage: {stage}")
        return True
    except Exception as e:
        print(f"Failed to send email to {candidate_email}: {e}")
        return False
