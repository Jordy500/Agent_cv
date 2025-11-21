import os
import logging
from datetime import datetime

from utils.guards import check_api_key

logger = logging.getLogger(__name__)


class MotivationLetterGenerator:
    """Generates motivation letters for matching job offers.
    
    This agent uses OpenAI GPT-3/4 to generate personalized motivation letters
    based on CV analysis and job offer details. Falls back to a template-based
    approach if no API key is provided.
    """

    def __init__(self, cv_analyzer, job_analyzer, gpt_api_key=None):
        """Initialize the letter generator.
        
        Args:
            cv_analyzer: CVAnalyzer instance (provides skills, experiences)
            job_analyzer: JobOfferAnalyzer instance (provides analyzed_offers)
            gpt_api_key: OpenAI API key (optional; fallback used if None)
        """
        self.cv_analyzer = cv_analyzer
        self.job_analyzer = job_analyzer
        self.gpt_api_key = gpt_api_key
        self.generated_letters = {}  # Track generated letters {offer_key: letter}
        
        # Guard: check API key validity
        if gpt_api_key and not check_api_key(gpt_api_key, 'GPT API Key'):
            logger.warning('GPT API key provided but appears invalid; will use fallback')
            self.openai_available = False
        elif gpt_api_key:
            try:
                import openai
                openai.api_key = gpt_api_key
                self.openai_available = True
                logger.info('OpenAI API key loaded; will use GPT for letter generation')
            except Exception as e:
                logger.warning(f'Failed to initialize OpenAI: {e}; will use template fallback')
                self.openai_available = False
        else:
            self.openai_available = False
            logger.info('No GPT API key provided; using template-based fallback for letters')

    def generate_letters(self, min_match_score=0.7):
        """Generate motivation letters for matching job offers.
        
        Args:
            min_match_score: only generate for offers with score >= this threshold
        
        Returns:
            dict of generated letters {offer_key: letter_content}
        """
        if not self.job_analyzer.analyzed_offers:
            logger.debug('No analyzed offers available for letter generation')
            return {}

        # Filter offers with good match
        matched_offers = [
            o for o in self.job_analyzer.analyzed_offers
            if o.get('match_score', 0) >= min_match_score
        ]

        if not matched_offers:
            logger.debug(f'No offers with match_score >= {min_match_score}; no letters to generate')
            return {}

        logger.info(f'Generating motivation letters for {len(matched_offers)} matching offer(s)')

        for offer in matched_offers:
            offer_key = f"{offer['title']}_{offer['company']}"

            # Skip if already generated
            if offer_key in self.generated_letters:
                logger.debug(f'Letter already generated for "{offer_key}"; skipping')
                continue

            try:
                # Extract CV info
                cv_data = self.cv_analyzer.cv_data[0] if self.cv_analyzer.cv_data else {}
                candidate_name = cv_data.get('name', 'Candidate')
                candidate_skills = offer.get('matched_skills', [])
                
                # Generate letter
                if self.openai_available:
                    letter = self._generate_with_gpt(candidate_name, offer, candidate_skills)
                else:
                    letter = self._generate_template(candidate_name, offer, candidate_skills)

                self.generated_letters[offer_key] = letter
                logger.info(f'Letter generated for "{offer["title"]}" at {offer["company"]}')

            except Exception as e:
                logger.warning(f'Failed to generate letter for "{offer_key}": {e}')

        return self.generated_letters

    def _generate_with_gpt(self, candidate_name, offer, matched_skills):
        """Generate letter using OpenAI GPT-3/4."""
        try:
            import openai
            # Prompt en français pour obtenir une lettre rédigée en français
            prompt = f"""Rédige une lettre de motivation professionnelle et personnalisée en français pour une candidature.

Candidat : {candidate_name}
Poste : {offer['title']}
Entreprise : {offer['company']}
Description du poste : {offer.get('description', 'N/A')}
Compétences du candidat : {', '.join(matched_skills) if matched_skills else 'N/A'}

Consignes :
- Écrire en français soigné et professionnel.
- Longueur : environ 180-250 mots.
- Mettre en avant les compétences pertinentes et expliquer pourquoi le candidat correspond au poste.
- Montrer un réel intérêt pour l'entreprise et le poste.
- Rédiger la lettre sous forme de lettre formelle (politesse, structure). 

Rédige la lettre maintenant en français :"""

            # Use REST-based helper to avoid dependency on local openai package
            from utils.openai_client import chat_completion
            messages = [{"role": "user", "content": prompt}]
            letter = chat_completion(messages, model="gpt-3.5-turbo", max_tokens=600, temperature=0.7)
            logger.debug(f'GPT letter generated ({len(letter)} chars)')
            return letter

        except Exception as e:
            logger.warning(f'GPT generation failed, falling back to template: {e}')
            # Fallback to template
            return self._generate_template(candidate_name, offer, matched_skills)

    def _generate_template(self, candidate_name, offer, matched_skills):
        """Generate letter using a simple template."""
        title = offer.get('title', 'le poste')
        company = offer.get('company', "l'entreprise")
        description = offer.get('description', '')
        match_score = int(offer.get('match_score', 0) * 100)

        skills_str = ', '.join(matched_skills) if matched_skills else 'compétences pertinentes'

        letter = f"""Madame, Monsieur,

    Je souhaite vous faire part de mon vif intérêt pour le poste de {title} au sein de {company}. Fort(e) d'une expérience significative et d'un ensemble de compétences adaptées, je suis convaincu(e) de pouvoir contribuer efficacement à vos projets.

    Au cours de mon parcours, j'ai développé des compétences en {skills_str} qui correspondent étroitement aux attentes liées à ce poste. J'ai su mettre en œuvre ces compétences dans des contextes professionnels exigeants, en obtenant des résultats mesurables et en m'adaptant rapidement aux besoins des équipes.

    Ce qui motive particulièrement ma candidature, c'est la perspective de rejoindre {company} et de participer à ses enjeux en apportant mon savoir-faire et mon engagement. Je suis enthousiaste à l'idée de relever les défis proposés par ce poste et d'évoluer au sein d'une organisation reconnue pour son dynamisme.

    Je me tiens à votre disposition pour un entretien afin d'échanger plus en détail sur ma candidature et la valeur ajoutée que je peux apporter.

    Je vous remercie par avance de l'attention portée à ma candidature.

    Veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

    {candidate_name}

    ---
    Généré le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    Score de correspondance : {match_score}%"""

        return letter

    def get_generated_letters(self):
        """Return all generated letters."""
        return self.generated_letters.copy()

    def get_letter_for_offer(self, offer_key):
        """Get a specific generated letter by offer key."""
        return self.generated_letters.get(offer_key)

    def clear_generated_letters(self):
        """Clear all generated letters."""
        self.generated_letters.clear()
        logger.info('Generated letters cleared')