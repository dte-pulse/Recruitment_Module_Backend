# scoring_service.py

from __future__ import annotations
from typing import Dict, List, Any, Tuple
import re


class ScoringService:
    """
    Compute application scores against a job using simple, explainable heuristics.

    Returns a dictionary with:
      - overall_score
      - skills_match_score
      - experience_match_score
      - education_match_score
      - certification_match_score
      - keywords_match_score
    """

    # Component weights used for overall score aggregation
    WEIGHTS = {
        "skills": 0.40,
        "experience": 0.25,
        "education": 0.15,
        "certifications": 0.10,
        "keywords": 0.10,
    }

    # Qualification ranking for rough comparison
    QUAL_RANK = {
        "phd": 6, "doctorate": 6,
        "m.tech": 5, "m.e.": 5, "mca": 5, "m.sc": 5, "mba": 5, "postgraduate": 5,
        "b.tech": 4, "b.e.": 4, "bca": 4, "b.sc": 4, "undergraduate": 4,
        "diploma": 2, "hsc": 2, "intermediate": 2,
        "ssc": 1, "10th": 1, "12th": 2,
    }

    # Heuristic mapping from job experience level label to (min_years, max_years)
    EXP_BANDS = {
        "fresher": (0.0, 1.0),
        "0-1 years": (0.0, 1.0),
        "1-3 years": (1.0, 3.0),
        "3-5 years": (3.0, 5.0),
        "3-6 years": (3.0, 6.0),
        "5-8 years": (5.0, 8.0),
        "6+ years": (6.0, 100.0),
        "6 plus": (6.0, 100.0),
        "6+": (6.0, 100.0),
    }

    @staticmethod
    def score_application(candidate_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute all component scores and the weighted overall score.

        candidate_data keys:
          - technical_skills: List[str]
          - total_experience: float
          - highest_qualification: str
          - academic_score: str (e.g., "8.0 CGPA" or "75%")
          - certifications: List[str]
          - resume_keywords: List[str]

        job_data keys:
          - required_skills: List[str]
          - preferred_skills: List[str]
          - experience_level: str
          - education_requirement: str
          - minimum_academic_score: str
          - required_certifications: List[str]
          - keywords: List[str]
        """

        # Normalize inputs
        c_skills = ScoringService._norm_list(candidate_data.get("technical_skills", []))
        j_req = ScoringService._norm_list(job_data.get("required_skills", []))
        j_pref = ScoringService._norm_list(job_data.get("preferred_skills", []))

        c_total_exp = ScoringService._safe_float(candidate_data.get("total_experience", 0.0))
        j_exp_label = ScoringService._safe_str(job_data.get("experience_level", ""))

        c_qual = ScoringService._safe_str(candidate_data.get("highest_qualification", ""))
        j_edu = ScoringService._safe_str(job_data.get("education_requirement", ""))
        c_acad = ScoringService._safe_str(candidate_data.get("academic_score", ""))
        j_min_acad = ScoringService._safe_str(job_data.get("minimum_academic_score", ""))

        c_certs = ScoringService._norm_list(candidate_data.get("certifications", []))
        j_req_certs = ScoringService._norm_list(job_data.get("required_certifications", []))

        c_keywords = ScoringService._norm_list(candidate_data.get("resume_keywords", []))
        j_keywords = ScoringService._norm_list(job_data.get("keywords", []))

        # Component scores (0–100)
        skills_match_score = ScoringService._score_skills(c_skills, j_req, j_pref)
        experience_match_score = ScoringService._score_experience(c_total_exp, j_exp_label)
        education_match_score = ScoringService._score_education(c_qual, j_edu, c_acad, j_min_acad)
        certification_match_score = ScoringService._score_certifications(c_certs, j_req_certs)
        keywords_match_score = ScoringService._score_keywords(c_keywords, j_keywords)

        # Weighted overall
        overall_score = (
            skills_match_score * ScoringService.WEIGHTS["skills"]
            + experience_match_score * ScoringService.WEIGHTS["experience"]
            + education_match_score * ScoringService.WEIGHTS["education"]
            + certification_match_score * ScoringService.WEIGHTS["certifications"]
            + keywords_match_score * ScoringService.WEIGHTS["keywords"]
        )

        return {
            "overall_score": round(overall_score, 2),
            "skills_match_score": round(skills_match_score, 2),
            "experience_match_score": round(experience_match_score, 2),
            "education_match_score": round(education_match_score, 2),
            "certification_match_score": round(certification_match_score, 2),
            "keywords_match_score": round(keywords_match_score, 2),
        }

    # -------------------------
    # Component scoring methods
    # -------------------------

    @staticmethod
    def _score_skills(candidate: List[str], required: List[str], preferred: List[str]) -> float:
        """70% weight on required, 30% on preferred."""
        if not candidate and not required and not preferred:
            return 0.0

        c_set = set(candidate)
        req_set = set(required)
        pref_set = set(preferred)

        req_ratio = len(c_set & req_set) / len(req_set) if req_set else 1.0
        pref_ratio = len(c_set & pref_set) / len(pref_set) if pref_set else 1.0

        return ScoringService._clip(100.0 * (0.7 * req_ratio + 0.3 * pref_ratio))

    @staticmethod
    def _score_experience(total_exp_years: float, exp_label: str) -> float:
        """
        Match candidate's total_experience against job.experience_level.

        Examples:
          - job.experience_level = "3-5 years" → min=3, max=5
          - "fresher" → 0–1
          - "6+" → 6–100

        Score:
          - 100 if within [min, max]
          - Linear decay below min
          - Slight penalty if > max (overqualified)
        """
        exp_label = exp_label.strip().lower()
        total_exp = max(0.0, float(total_exp_years))

        # Try predefined bands
        band = ScoringService.EXP_BANDS.get(exp_label)
        if band:
            min_req, max_req = band
        else:
            # Parse "X-Y years" pattern
            match = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", exp_label)
            if match:
                min_req = float(match.group(1))
                max_req = float(match.group(2))
            elif "fresher" in exp_label:
                min_req, max_req = 0.0, 1.0
            elif any(x in exp_label for x in ["6+", "6 plus", "6+ years"]):
                min_req, max_req = 6.0, 100.0
            else:
                min_req, max_req = 0.0, 100.0  # fallback

        if min_req <= total_exp <= max_req:
            return 100.0
        elif total_exp < min_req:
            # Below minimum: scale from 0 to 100 as we approach min
            if min_req <= 0:
                return 100.0
            ratio = total_exp / min_req
            return ScoringService._clip(100.0 * ratio * 0.9)  # cap at 90% if below
        else:
            # Overqualified: small penalty
            excess = total_exp - max_req
            penalty = min(20.0, excess * 2.0)  # max 20-point penalty
            return ScoringService._clip(100.0 - penalty)

    @staticmethod
    def _score_education(c_qual: str, j_edu: str, c_acad: str, j_min_acad: str) -> float:
        """70% qualification + 30% academic score."""
        qual_score = ScoringService._score_qualification(c_qual, j_edu)
        acad_score = ScoringService._score_academic_threshold(c_acad, j_min_acad)
        return ScoringService._clip(0.7 * qual_score + 0.3 * acad_score)

    @staticmethod
    def _score_certifications(candidate: List[str], required: List[str]) -> float:
        rset = set(required)
        if not rset:
            return 100.0
        cset = set(candidate)
        return ScoringService._clip(100.0 * len(cset & rset) / len(rset))

    @staticmethod
    def _score_keywords(candidate: List[str], required: List[str]) -> float:
        rset = set(required)
        if not rset:
            return 100.0
        cset = set(candidate)
        return ScoringService._clip(100.0 * len(cset & rset) / len(rset))

    # -------------------------
    # Helpers
    # -------------------------

    @staticmethod
    def _norm_list(items: Any) -> List[str]:
        if not items:
            return []
        out = []
        seen = set()
        for x in items:
            if not x:
                continue
            s = str(x).strip().lower()
            if s and s not in seen:
                out.append(s)
                seen.add(s)
        return out

    @staticmethod
    def _safe_str(x: Any) -> str:
        return str(x or "").strip()

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, float(x)))

    @staticmethod
    def _qual_rank(label: str) -> int:
        s = label.strip().lower()
        if s in ScoringService.QUAL_RANK:
            return ScoringService.QUAL_RANK[s]
        for k, v in ScoringService.QUAL_RANK.items():
            if k in s:
                return v
        return 0

    @staticmethod
    def _score_qualification(c_qual: str, j_edu: str) -> float:
        if not j_edu:
            return 100.0
        cr = ScoringService._qual_rank(c_qual)
        jr = ScoringService._qual_rank(j_edu)
        if jr == 0:
            return 100.0
        ratio = cr / jr if jr > 0 else 1.0
        return 100.0 if ratio >= 1.0 else ScoringService._clip(100.0 * ratio * 0.9)

    @staticmethod
    def _parse_academic_value(s: str) -> Tuple[float, str]:
        text = s.strip().lower()
        if not text:
            return 0.0, "unknown"

        # Percent
        if "%" in text or "percent" in text:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
            return (float(m.group(1)) if m else 0.0, "percent")

        # CGPA out of 10
        if "/" in text:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*/\s*10", text)
            if m:
                return (float(m.group(1)), "cgpa")

        if "cgpa" in text:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
            return (float(m.group(1)) if m else 0.0, "cgpa")

        # Pure number
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        if m:
            val = float(m.group(1))
            return (val, "cgpa") if val <= 10.0 else (val, "percent")

        return 0.0, "unknown"

    @staticmethod
    def _score_academic_threshold(c_acad: str, j_min_acad: str) -> float:
        if not j_min_acad:
            return 100.0

        c_val, c_type = ScoringService._parse_academic_value(c_acad)
        j_val, j_type = ScoringService._parse_academic_value(j_min_acad)

        if j_type == "unknown":
            return 100.0

        if j_type == "percent":
            c_cmp = c_val * 10.0 if c_type == "cgpa" else c_val
            return 100.0 if c_cmp >= j_val else ScoringService._clip(100.0 * c_cmp / max(j_val, 1))
        else:  # cgpa
            c_cmp = c_val if c_type == "cgpa" else c_val / 10.0
            return 100.0 if c_cmp >= j_val else ScoringService._clip(100.0 * c_cmp / max(j_val, 1))