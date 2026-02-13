# s3_service.py
import os
import mimetypes
import boto3
from datetime import datetime
from fastapi import UploadFile, HTTPException


class S3Service:
    def __init__(self):
        self.bucket = os.getenv("S3_BUCKET_NAME")
        if not self.bucket:
            raise Exception("S3_BUCKET_NAME not set in .env")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )

    # ---------------------------------------------------------
    # 1️⃣ Upload File to S3 (PRIVATE)
    # ---------------------------------------------------------
    async def upload_file(self, file: UploadFile) -> dict:
        allowed_types = [
            ".pdf", ".doc", ".docx",
            ".mp4", ".avi", ".mov", ".webm",
            ".jpg", ".jpeg", ".png", ".webp"
        ]

        if not any(file.filename.lower().endswith(ext) for ext in allowed_types):
            raise HTTPException(status_code=400, detail="Unsupported file type")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_filename = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in file.filename
        )
        key = f"uploads/{timestamp}_{safe_filename}"

        try:
            file_content = await file.read()

            # Detect content-type safely
            guessed_type, _ = mimetypes.guess_type(file.filename)
            content_type = file.content_type or guessed_type or "application/octet-stream"

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type
            )

            return {"key": key, "filename": file.filename}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"S3 Upload Failed: {str(e)}")

    # ---------------------------------------------------------
    # 2️⃣ Generate Pre-Signed URL (INLINE VIEW ENABLED)
    # ---------------------------------------------------------
    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            # Try to guess file content type based on extension
            content_type, _ = mimetypes.guess_type(key)
            content_type = content_type or "application/octet-stream"

            # Force inline view for browsers
            params = {
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": "inline",
                "ResponseContentType": content_type
            }

            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expires_in
            )

            return url

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"URL generation failed: {str(e)}")
