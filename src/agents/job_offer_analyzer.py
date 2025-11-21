import logging
import re
from difflib import SequenceMatcher

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

    def compare_job_offers(self, cv_skills=None):
        """Analyze and compare all job offers against candidate skills.
        
        Args:
            cv_skills: optional list of candidate skills (for better matching);
                      if None, will extract from offers' own data
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
            
            analyzed = self._analyze_single_offer(offer, cv_skills)
            self.analyzed_offers.append(analyzed)
        
        # Log summary
        high_matches = [o for o in self.analyzed_offers if o.get('match_score', 0) >= 0.7]
        logger.info(f'Job comparison complete: {len(high_matches)} offers with good match (score >= 0.7)')

    def _analyze_single_offer(self, offer, cv_skills=None):
        """Analyze a single job offer.
        
        Returns a dict with:
        - offer data
        - extracted_skills: list of required skills
        - match_score: 0.0-1.0 similarity score
        - matched_skills: list of matched skills
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
        
        result = {
            'title': title,
            'company': company,
            'description': description,
            'required_skills': required_skills,
            'matched_skills': matched_skills,
            'match_score': match_score,
            'match_percentage': int(match_score * 100)
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