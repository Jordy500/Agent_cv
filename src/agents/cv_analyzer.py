import os
import logging
from collections import Counter
import sys
from pathlib import Path

import PyPDF2
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import spacy

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.guards import check_file_exists, safe_extract_pdf_text

logger = logging.getLogger(__name__)


class CVAnalyzer:
    def __init__(self, cv_data, spacy_model=None):
        # cv_data can be a pymongo cursor or a list; normalize to list for safe multiple iterations
        try:
            # If cursor-like, convert to list (may be large in prod; consider streaming)
            self.cv_data = list(cv_data)
        except Exception:
            self.cv_data = cv_data

        # Load spaCy model: spacy_model may be a model name (str) or an already-loaded nlp object
        if spacy_model and hasattr(spacy_model, 'pipe'):
            self.nlp = spacy_model
        else:
            model_name = spacy_model or os.environ.get('SPACY_MODEL', 'fr_core_news_sm')
            try:
                self.nlp = spacy.load(model_name)
            except OSError:
                raise RuntimeError(
                    f"spaCy model '{model_name}' not found. Install it with: python -m spacy download {model_name}"
                )

        # Ensure required NLTK resources are available (download only if missing)
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')

    def analyze_cvs(self):
        for cv in self.cv_data:
            # If analysis already exists and is complete, skip reanalysis to preserve pre-filled skills
            if isinstance(cv, dict) and 'analysis' in cv and cv['analysis'].get('skills'):
                logger.debug(f'CV for {cv.get("name", "Unknown")} already analyzed; skipping')
                continue
            
            # Extraire le texte du PDF
            path = cv.get('path') if isinstance(cv, dict) else None
            if not path:
                logger.warning('CV entry missing "path": %s', cv)
                continue

            text = self.extract_pdf_text(path)
            if not text:
                logger.warning('No text extracted from %s', path)
                continue

            # Tokeniser le texte
            tokens = word_tokenize(text.lower())

            # Supprimer les stop words (utilise la langue anglaise par défaut; ajustez si nécessaire)
            stop_words = set(stopwords.words('english'))
            filtered_tokens = [token for token in tokens if token.isalpha() and token not in stop_words]

            # Compter les occurrences des mots
            word_counts = Counter(filtered_tokens)

            # Analyser les compétences clés
            skills = self.identify_skills(word_counts)

            # Analyser les expériences
            experiences = self.analyze_experiences(text)

            # Stocker les résultats
            if isinstance(cv, dict):
                cv['analysis'] = {
                    'skills': skills,
                    'experiences': experiences,
                }

            logger.info('Analyse terminée pour le CV : %s', cv.get('name') if isinstance(cv, dict) else str(cv))

    def extract_pdf_text(self, pdf_path):
        """Safely extract text from PDF using guards."""
        return safe_extract_pdf_text(pdf_path, fallback_text="")

    def identify_skills(self, word_counts):
        # Identifie les compétences candidates en utilisant la fréquence des mots
        top_skills = []
        for word, _ in word_counts.most_common(10):  # On prend les 10 mots les plus fréquents
            if len(word) > 3:  # On ignore les mots très courts
                top_skills.append(word)
        return top_skills

    def analyze_experiences(self, text):
        # Cette méthode extrait les informations sur les expériences via NER
        doc = self.nlp(text)
        experiences = []
        # Labels pertinents à garder
        relevant_labels = {
            'PERSON', 'ORG', 'GPE', 'DATE', 'NORP', 'WORK_OF_ART', 'EVENT', 'PRODUCT', 'LANGUAGE'
        }
        for ent in doc.ents:
            if ent.label_ in relevant_labels:
                experiences.append({'entity': ent.text, 'label': ent.label_})
        return experiences

    def get_all_skills(self):
        """Extract and return all unique skills from analyzed CVs.
        
        Returns:
            list of unique skills from all CVs that have been analyzed
        """
        all_skills = set()
        for cv in self.cv_data:
            if isinstance(cv, dict) and 'analysis' in cv:
                analysis = cv['analysis']
                if isinstance(analysis, dict) and 'skills' in analysis:
                    all_skills.update(analysis['skills'])
        return list(all_skills)