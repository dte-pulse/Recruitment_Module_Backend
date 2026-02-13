# resume_parser.py

"""
Lightweight resume parser for PDFs and DOCX files.
Extracts basic fields and a heuristic list of technical skills and keywords.
"""

from __future__ import annotations
from typing import Dict, Any, List
import os
import re

# Optional dependencies
try:
    import docx2txt
except Exception:
    docx2txt = None

try:
    import PyPDF2
except Exception:
    PyPDF2 = None


class ResumeParser:
    # Very simple skills dictionary; extend as needed
    SKILLS = {
        "languages": ["python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql"],
        "web": ["react", "redux", "next.js", "node", "express", "fastapi", "django", "spring", "spring boot", "flask"],
        "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "redis", "nginx"],
        "db": ["mysql", "postgres", "mongodb", "dynamodb", "sqlite", "oracle"],
        "devops": ["git", "ci/cd", "github actions", "jenkins", "ansible", "helm"],
        "data": ["pandas", "numpy", "pyspark", "airflow", "kafka"],
        "ml": ["scikit-learn", "pytorch", "tensorflow", "transformers"],
        "mobile": ["android", "kotlin", "swift", "flutter", "react native"],
    }

    KEYWORDS = [
        "microservices", "rest api", "graphql", "websocket", "message queue",
        "system design", "scalability", "availability", "latency",
        "unit testing", "integration testing", "tdd",
        "agile", "scrum", "kanban"
    ]

    @staticmethod
    def parse_resume(file_path: str) -> Dict[str, Any]:
        """
        Parse resume and return structured data.
        """
        if not os.path.exists(file_path):
            return {"error": "File not found"}

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".pdf":
                text = ResumeParser._extract_text_pdf(file_path)
            elif ext in (".docx", ".doc"):
                text = ResumeParser._extract_text_docx(file_path)
            else:
                return {"error": "Unsupported file type. Use PDF or DOCX."}
        except Exception as e:
            return {"error": f"Failed to extract text: {e}"}

        # Normalize text
        raw_text = text or ""
        text_lower = raw_text.lower()

        # Extract simple fields
        email = ResumeParser._extract_email(text_lower)
        phone = ResumeParser._extract_phone(text_lower)
        name = ResumeParser._extract_name(raw_text)

        # Skills detection
        skills = ResumeParser._detect_skills(text_lower)
        keywords = ResumeParser._detect_keywords(text_lower)

        # Very rough experience inference (years)
        exp_years = ResumeParser._infer_experience_years(text_lower)

        # Basic education detection
        education = ResumeParser._detect_education(text_lower)

        # Certifications (simple heuristics)
        certifications = ResumeParser._detect_certifications(text_lower)

        return {
            "full_name": name,
            "email": email,
            "phone_number": phone,
            "technical_skills": skills,
            "resume_keywords": keywords,
            "total_experience": exp_years,
            "education": education,
            "certifications": certifications,
            "raw_text": raw_text,  # Added raw text support
        }

    # -----------------------------
    # Extractors and heuristics
    # -----------------------------

    @staticmethod
    def _extract_text_pdf(path: str) -> str:
        if PyPDF2 is None:
            raise RuntimeError("PyPDF2 not installed")
        text = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)

    @staticmethod
    def _extract_text_docx(path: str) -> str:
        if docx2txt is None:
            raise RuntimeError("docx2txt not installed")
        return docx2txt.process(path) or ""

    @staticmethod
    def _extract_email(text: str) -> str | None:
        m = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}", text)
        return m.group(0) if m else None

    @staticmethod
    def _extract_phone(text: str) -> str | None:
        m = re.search(r"(\\+\\d{1,3}\\s?)?\\d{10}", text)
        return m.group(0) if m else None

    @staticmethod
    def _extract_name(text: str) -> str | None:
        # crude heuristic: first non-empty line, strip non-letters
        for line in text.splitlines():
            cleaned = re.sub(r"[^A-Za-z\\s\\-\\.]", "", line).strip()
            if cleaned and len(cleaned.split()) in (2, 3) and len(cleaned) <= 60:
                return cleaned
        return None

    @staticmethod
    def _detect_skills(text: str) -> List[str]:
        found = []
        for group in ResumeParser.SKILLS.values():
            for skill in group:
                if re.search(rf"\\b{re.escape(skill)}\\b", text):
                    found.append(skill)
        # dedupe
        seen = set()
        out = []
        for s in found:
            if s not in seen:
                out.append(s)
                seen.add(s)
        return out

    @staticmethod
    def _detect_keywords(text: str) -> List[str]:
        found = []
        for kw in ResumeParser.KEYWORDS:
            if re.search(rf"\\b{re.escape(kw)}\\b", text):
                found.append(kw)
        # dedupe
        return list(dict.fromkeys(found))

    @staticmethod
    def _infer_experience_years(text: str) -> float:
        # Heuristics: look for patterns like "X years", "X+ years"
        yrs = 0.0
        for m in re.findall(r"(\\d+(?:\\.\\d+)?)\\s*\\+?\\s*years?", text):
            try:
                yrs = max(yrs, float(m))
            except Exception:
                pass
        # If mentions internships, add small weight
        if "internship" in text or "intern" in text:
            yrs = max(yrs, 0.5 if yrs < 1.0 else yrs)
        return round(yrs, 2)

    @staticmethod
    def _detect_education(text: str) -> List[str]:
        degrees = [
            "b.tech", "b.e.", "bsc", "b.sc", "bca",
            "m.tech", "m.e.", "msc", "m.sc", "mca", "mba",
            "phd", "doctorate", "diploma"
        ]
        found = []
        for d in degrees:
            if d in text:
                found.append(d)
        return list(dict.fromkeys(found))

    @staticmethod
    def _detect_certifications(text: str) -> List[str]:
        patterns = [
            r"aws\\s+certified[\\w\\s-]*",
            r"azure\\s+certified[\\w\\s-]*",
            r"google\\s+(professional|associate)[\\w\\s-]*",
            r"oracle\\s+certified[\\w\\s-]*",
            r"pmp",
            r"scrum\\s+master",
            r"oca|ocp|ocm",
        ]
        found = []
        for p in patterns:
            for m in re.findall(p, text):
                found.append(m.strip())
        return list(dict.fromkeys(found))
