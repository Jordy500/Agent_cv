import logging
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List

from utils.text_processing import normalize_text
try:
    from utils.nlp_extractors import (
        extract_years_experience,
        extract_education_level,
        extract_seniority_level,
    )
except Exception:
    # Fallbacks if extractors are not available
    def extract_years_experience(text: str):
        m = re.search(r"(\d{1,2})\s+(?:years|ans|années)", text, flags=re.I)
        return float(m.group(1)) if m else None
    def extract_education_level(text: str):
        t = text.lower()
        if 'phd' in t or 'doctorat' in t:
            return 'phd'
        if 'master' in t or 'msc' in t:
            return 'master'
        if 'bachelor' in t or 'licence' in t:
            return 'bachelor'
        if 'bac' in t:
            return 'bac'
        return 'none'
    def extract_seniority_level(text: str):
        t = text.lower()
        if any(x in t for x in ['senior','lead']):
            return 'senior'
        if any(x in t for x in ['junior','entry']):
            return 'junior'
        return 'mid'

logger = logging.getLogger(__name__)


class JobOfferAnalyzer:
    """Analyzes and compares job offers with candidate skills.
    
    This analyzer extracts required skills from job offers and scores them
    against the candidate's CV analysis results using simple similarity matching.
    """

    def __init__(self, job_offers, bert_model=None):
        """Initialize the analyzer.
        
        Args:
            job_offers: list of job offer dicts or pymongo cursor
            bert_model: optional BERT model name or object (currently unused; for future NLP enhancement)
        """
        # Normalize to list for safe multiple iterations
        try:
            self.job_offers = list(job_offers)
        except Exception:
            self.job_offers = job_offers
        
        self.bert_model = bert_model
        self.analyzed_offers = []

    def compare_job_offers(self, cv_skills=None, cv_data: List[Dict[str, Any]] = None):
        """Analyze and compare all job offers against candidate skills.
        
        Args:
            cv_skills: optional list of candidate skills (for better matching);
                      if None, will extract from offers' own data
            cv_data: optional list of CV dicts with `analysis` providing
                     `skills`, `years_experience`, and `education_level` for ATS scoring
        """
        if not self.job_offers:
            logger.info('No job offers to analyze')
            return
        
        logger.info(f'Comparing {len(self.job_offers)} job offer(s)')
        self.analyzed_offers = []
        
        for offer in self.job_offers:
            if not isinstance(offer, dict):
                logger.warning(f'Skipping invalid offer format: {offer}')
                continue
            
            analyzed = self._analyze_single_offer(offer, cv_skills, cv_data=cv_data)
            self.analyzed_offers.append(analyzed)
        
        # Log summary
        high_matches = [o for o in self.analyzed_offers if o.get('match_score', 0) >= 0.7]
        logger.info(f'Job comparison complete: {len(high_matches)} offers with good match (score >= 0.7)')

    def _analyze_single_offer(self, offer, cv_skills=None, cv_data: List[Dict[str, Any]] = None):
        """Analyze a single job offer.
        
        Returns a dict with:
        - offer data
        - extracted_skills: list of required skills
        - match_score: 0.0-1.0 similarity score
        - matched_skills: list of matched skills
        - ats_score: weighted score including years, education, location
        """
        title = offer.get('title', 'Unknown')
        company = offer.get('company', 'Unknown')
        description = offer.get('description', '')
        required_skills = offer.get('skills', [])
        
        logger.debug(f'Analyzing offer: {title} at {company}')
        
        # If no explicit skills provided, extract from title + description
        if not required_skills:
            required_skills = self._extract_skills_from_text(title + ' ' + description)
            # If still no skills found but title suggests data role, infer common skills
            if len(required_skills) == 0:
                title_lower = title.lower()
                if any(term in title_lower for term in ['data analyst', 'data scientist', 'data engineer']):
                    # Infer common skills for data roles (4 skills to allow 75% match with 3/4)
                    required_skills = ['sql', 'python', 'data analysis', 'data visualization']
                    logger.info(f'No skills extracted, inferred basic skills for "{title}": {required_skills}')
            elif len(required_skills) > 0:
                logger.info(f'Extracted {len(required_skills)} skills from "{title}": {required_skills}')
            else:
                logger.debug(f'No skills extracted from "{title}"')
        
        # Normalize skills (lowercase, strip whitespace)
        required_skills = [s.lower().strip() for s in required_skills]
        
        # Calculate match score against CV skills
        match_score = 0.0
        matched_skills = []
        
        if cv_skills:
            cv_skills_lower = [s.lower().strip() for s in cv_skills]
            matched_skills, match_score = self._calculate_skill_match(
                required_skills, cv_skills_lower
            )
        else:
            logger.debug(f'No CV skills provided for matching against {title}')
        
        # ATS-style requirement extraction
        requirements = self._extract_requirements(offer)

        ats_score = None
        best_match_cv = None
        if cv_data:
            # pick best cv against this offer
            best_score = -1.0
            for cv in cv_data:
                score = self._score_offer(cv, offer, requirements, fallback_cv_skills=cv_skills)
                if score > best_score:
                    best_score = score
                    best_match_cv = cv
            ats_score = round(best_score, 4)

        result = {
            'title': title,
            'company': company,
            'description': description,
            'url': offer.get('url', ''),
            'location': offer.get('location', ''),
            'source': offer.get('source', ''),
            'created': offer.get('created', ''),
            'required_skills': required_skills,
            'matched_skills': matched_skills,
            'match_score': match_score,
            'match_percentage': int(match_score * 100),
            'requirements': requirements,
            'ats_score': ats_score,
            'best_match_cv': best_match_cv.get('name') if best_match_cv else None,
        }
        
        if match_score > 0:
            logger.info(
                f'Offer match: "{title}" ({company}) — {int(match_score * 100)}% match '
                f'({len(matched_skills)}/{len(required_skills)} skills matched)'
            )
        
        return result

    def _extract_skills_from_text(self, text):
        """Extract technical skills from job title/description using keyword matching.
        
        Searches for common data/tech skills in the text (supports English and French).
        
        Args:
            text: job title + description
            
        Returns:
            list of detected skills
        """
        # Common tech skills database with French equivalents
        # Format: (canonical_skill_name, [patterns_to_match])
        skill_patterns = [
            # Programming languages
            ('python', ['python']),
            ('r', [r'\br\b', r'\blanguage r\b']),
            ('java', ['java']),
            ('javascript', ['javascript', 'js']),
            ('sql', ['sql', 'mysql', 'postgresql', 't-sql', 'pl/sql']),
            ('scala', ['scala']),
            
            # Data tools & libraries
            ('pandas', ['pandas']),
            ('numpy', ['numpy']),
            ('scikit-learn', ['scikit-learn', 'sklearn']),
            ('tensorflow', ['tensorflow']),
            ('pytorch', ['pytorch']),
            ('spark', ['spark', 'pyspark']),
            ('hadoop', ['hadoop']),
            ('tableau', ['tableau']),
            ('power bi', ['power bi', 'powerbi']),
            ('excel', ['excel']),
            
            # Data Science concepts (English + French)
            ('machine learning', ['machine learning', 'ml', 'apprentissage automatique', 'apprentissage machine']),
            ('deep learning', ['deep learning', 'apprentissage profond']),
            ('data visualization', ['data visualization', 'visualisation', 'dataviz', 'data viz']),
            ('statistical analysis', ['statistical analysis', 'statistiques', 'analyse statistique']),
            ('data mining', ['data mining', 'exploration de données', 'fouille de données']),
            ('data analysis', ['data analysis', 'analyse de données', 'analyse des données']),
            
            # Cloud
            ('aws', ['aws', 'amazon web services']),
            ('azure', ['azure', 'microsoft azure']),
            ('gcp', ['gcp', 'google cloud']),
            ('docker', ['docker']),
            
            # General
            ('git', ['git', 'github', 'gitlab']),
            ('api', ['api', 'rest api', 'restful']),
            ('etl', ['etl'])
        ]
        
        text_lower = text.lower()
        detected = set()  # Use set to avoid duplicates
        
        for skill_name, patterns in skill_patterns:
            for pattern in patterns:
                # Search for pattern in text
                if pattern in text_lower:
                    detected.add(skill_name)
                    break  # Found match, move to next skill
        
        return list(detected)

    def _calculate_skill_match(self, required_skills, cv_skills):
        """Calculate skill matching between required and available skills.
        
        Uses exact matches and fuzzy matching (SequenceMatcher) for similar skill names.
        
        Returns:
            (matched_skills, score) where score is 0.0-1.0
        """
        if not required_skills or not cv_skills:
            return [], 0.0
        
        matched = []
        match_count = 0
        
        for req_skill in required_skills:
            # Exact match
            if req_skill in cv_skills:
                matched.append(req_skill)
                match_count += 1
                continue
            
            # Fuzzy match (similarity threshold 0.7)
            best_sim = 0.0
            best_cv_skill = None
            
            for cv_skill in cv_skills:
                similarity = SequenceMatcher(None, req_skill, cv_skill).ratio()
                if similarity > best_sim and similarity >= 0.7:
                    best_sim = similarity
                    best_cv_skill = cv_skill
            
            if best_cv_skill:
                matched.append(f"{req_skill} (similar: {best_cv_skill})")
                match_count += 1
        
        score = match_count / len(required_skills) if required_skills else 0.0
        return matched, score

    # --- ATS helpers ---
    _WEIGHTS = {
        'skills': 0.60,
        'experience': 0.20,
        'education': 0.15,
        'location': 0.05,
    }

    _EDU_ORDER = {
        'none': 0,
        'bac': 1,
        'bachelor': 2,
        'master': 3,
        'phd': 4,
    }

    def _extract_requirements(self, offer: Dict[str, Any]) -> Dict[str, Any]:
        text = normalize_text(offer.get('description', '') + ' ' + offer.get('title', ''))
        required_years = extract_years_experience(text) or 0.0
        required_edu = extract_education_level(text) or 'none'
        seniority = extract_seniority_level(text)
        # simple skill hints from description
        skill_hints = set()
        for token in re.findall(r"[a-zA-Z+#.]{2,}", text):
            t = token.lower()
            if t in {'python','java','javascript','typescript','react','vue','angular','node','go','rust','c++','c#','dotnet','sql','nosql','mysql','postgres','mongodb','redis','aws','gcp','azure','docker','kubernetes','terraform','ansible','linux','git','jira','spark','hadoop','airflow','dbt','pandas','numpy','sklearn','pytorch','tensorflow'}:
                skill_hints.add(t)
        return {
            'required_years': required_years,
            'required_education': required_edu,
            'seniority': seniority,
            'skill_hints': list(skill_hints),
        }

    def _score_offer(self, cv: Dict[str, Any], offer: Dict[str, Any], reqs: Dict[str, Any], fallback_cv_skills=None) -> float:
        analysis = cv.get('analysis', {})
        cv_skills = set(map(str.lower, analysis.get('skills', cv.get('skills', fallback_cv_skills or []))))
        offer_skills = set(map(str.lower, offer.get('skills', []))) | set(reqs.get('skill_hints', []))
        # skills score
        common = cv_skills & offer_skills
        skills_score = (len(common) / max(1, len(offer_skills))) if offer_skills else (1.0 if cv_skills else 0.0)

        # experience score
        cv_years = float(analysis.get('years_experience') or 0)
        req_years = float(reqs.get('required_years') or 0)
        if req_years <= 0:
            exp_score = 1.0
        else:
            exp_score = min(1.0, cv_years / req_years)

        # education score
        cv_edu = str(analysis.get('education_level') or 'none').lower()
        req_edu = str(reqs.get('required_education') or 'none').lower()
        cv_rank = self._EDU_ORDER.get(cv_edu, 0)
        req_rank = self._EDU_ORDER.get(req_edu, 0)
        edu_score = 1.0 if cv_rank >= req_rank else (cv_rank / max(1, req_rank))

        # location score (placeholder: prefer remote matches)
        location = str(offer.get('location', '')).lower()
        prefers_remote = bool(cv.get('preferences', {}).get('remote', True))
        if 'remote' in location or 'télétravail' in location:
            loc_score = 1.0
        else:
            loc_score = 1.0 if not prefers_remote else 0.6

        total = (
            self._WEIGHTS['skills'] * skills_score +
            self._WEIGHTS['experience'] * exp_score +
            self._WEIGHTS['education'] * edu_score +
            self._WEIGHTS['location'] * loc_score
        )
        return round(total, 4)

    def get_best_matches(self, top_n=5):
        """Return top N job offers sorted by match score.
        
        Args:
            top_n: number of top offers to return
        
        Returns:
            list of analyzed offers, sorted by match_score descending
        """
        sorted_offers = sorted(
            self.analyzed_offers,
            key=lambda x: x.get('match_score', 0),
            reverse=True
        )
        return sorted_offers[:top_n]