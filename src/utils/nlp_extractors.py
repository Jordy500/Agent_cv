"""Utility NLP extractors for CVs and job offers.

Lightweight regex + heuristics (language-agnostic FR/EN) to extract:
- years of experience
- education level
- soft skills
- certifications
- seniority level (title-based)
"""

import re
from typing import Optional, List


def extract_years_experience(text: str) -> Optional[float]:
    """Extract years of experience from free text.

    Supports patterns like:
    - "5 ans d'expérience", "5 ans d’expérience"
    - "3+ years experience"
    - "2-4 ans"
    - "X years" alone

    Returns a float (average for ranges) or None.
    """
    if not text:
        return None
    t = text.lower()

    # Range like "2 à 4 ans" or "2-4 years"
    m = re.search(r"(\d+)\s*(?:-|à|to)\s*(\d+)\s*(?:ans?|years?)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return round((a + b) / 2, 1)

    # Explicit years experience (FR/EN)
    m = re.search(r"\b(\d{1,2})\+?\s*(?:ans?|years?)\s*(?:d['’]?)?(?:expérience|experience)?\b", t)
    if m:
        val = float(m.group(1))
        if 0 <= val <= 60:
            return val

    # Since year -> compute delta
    m = re.search(r"\b(?:depuis|since)\s*(\d{4})\b", t)
    if m:
        try:
            start_year = int(m.group(1))
            from datetime import datetime
            years = datetime.now().year - start_year
            if years >= 0:
                return float(years)
        except Exception:
            pass

    # Fallback: any "X years" occurrences
    m = re.search(r"\b(\d{1,2})\s*years\b", t)
    if m:
        val = float(m.group(1))
        if 0 <= val <= 60:
            return val

    return None


def extract_education_level(text: str) -> str:
    """Detect highest education level from text.

    Returns one of: 'phd', 'master', 'bachelor', 'bac', 'none'.
    """
    if not text:
        return 'none'
    t = text.lower()

    # PhD
    if re.search(r"\b(phd|doctorat|docteur)\b", t):
        return 'phd'
    # Master / Engineer (bac+5)
    if re.search(r"\b(master|msc|bac\+5|ingénieur|engineer)\b", t):
        return 'master'
    # Bachelor / Licence (bac+3)
    if re.search(r"\b(licence|bachelor|bac\+3)\b", t):
        return 'bachelor'
    # Bac
    if re.search(r"\b(baccalauréat|bac)\b", t):
        return 'bac'
    return 'none'


def extract_soft_skills(text: str) -> List[str]:
    """Extract common soft skills from text (FR/EN keywords).

    Returns a list of unique soft skills.
    """
    if not text:
        return []
    t = text.lower()
    keywords = {
        'leadership': ['leadership', 'leader'],
        'communication': ['communication', 'communicate', 'communiquer'],
        'teamwork': ['teamwork', 'travail en équipe', 'collaboration'],
        'problem solving': ['problem solving', 'résolution de problèmes'],
        'adaptability': ['adaptabilité', 'adaptability', 'flexible'],
        'creativity': ['créativité', 'creativity'],
        'time management': ['gestion du temps', 'time management'],
        'critical thinking': ['esprit critique', 'critical thinking'],
        'ownership': ['autonomie', 'ownership'],
    }
    found = set()
    for label, variants in keywords.items():
        for v in variants:
            if v in t:
                found.add(label)
                break
    return list(found)


def extract_certifications(text: str) -> List[str]:
    """Extract common data/BI/cloud certifications.

    Heuristic detection of well-known cert names.
    """
    if not text:
        return []
    t = text.lower()
    patterns = {
        'aws certified': [r"aws\s+certified", r"certification\s+aws"],
        'azure fundamentals': [r"azure\s+fundamentals", r"az-900"],
        'azure data engineer': [r"dp-203", r"azure\s+data\s+engineer"],
        'gcp data engineer': [r"gcp\s+data\s+engineer", r"professional\s+data\s+engineer"],
        'power bi certification': [r"power\s*bi\s*certification", r"certified\s+power\s*bi"],
        'tableau certification': [r"tableau\s+certified", r"tableau\s+desktop\s+specialist"],
        'scrum master': [r"scrum\s+master", r"psm\s*i"],
        'itil': [r"\bitil\b"],
    }
    found = set()
    for label, regs in patterns.items():
        for r in regs:
            if re.search(r, t):
                found.add(label)
                break
    return list(found)


def extract_seniority_level(title: str) -> str:
    """Detect seniority level from a job title.

    Returns: 'junior', 'mid', 'senior', 'lead', 'principal'.
    """
    if not title:
        return 'mid'
    t = title.lower()
    if re.search(r"\b(principal|distinguished|fellow)\b", t):
        return 'principal'
    if re.search(r"\b(lead|chef|head\s+of|manager)\b", t):
        return 'lead'
    if re.search(r"\b(senior|confirmé|expert|sr\.?|sen\.?)\b", t):
        return 'senior'
    if re.search(r"\b(junior|débutant|jr\.?|graduate)\b", t):
        return 'junior'
    return 'mid'
