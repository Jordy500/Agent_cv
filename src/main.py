import os
import logging
import json
from agents.cv_analyzer import CVAnalyzer
from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.motivation_letter_generator import MotivationLetterGenerator
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender
from utils.adzuna_api import fetch_from_adzuna
from utils.job_fetcher import filter_offers_by_title_and_location
from dotenv import load_dotenv

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_test_data():
    """
    Charge les données de test depuis les fichiers JSON locaux
    Utilisé quand on n'a pas de base de données
    """
    base_dir = os.path.join(os.path.dirname(__file__), 'data')
    result = {
        'cv_data': [],
        'job_offers': []
    }

    def _load_json(filename):
        path = os.path.join(base_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.debug(f'Fichier non trouvé: {path}')
            return None
        except Exception as e:
            logger.warning(f'Erreur chargement {path}: {e}')
            return None

    # Charger CV
    cv = _load_json('cv_data.json')
    if isinstance(cv, list):
        result['cv_data'] = cv

    # Charger offres
    jobs = _load_json('job_offers.json')
    if isinstance(jobs, list):
        result['job_offers'] = jobs

    return result


def main():
    """Point d'entrée principal de l'application"""
    load_dotenv()
    
    logger.info('Démarrage Agent_cv...')

    # Charger les données locales
    test_data = get_test_data()
    cv_data = test_data['cv_data']
    job_offers = test_data['job_offers']
    
    # Check si on doit récupérer depuis Adzuna
    job_source = os.environ.get('JOB_SOURCE', '').lower()
    
    if job_source == 'adzuna':
        try:
            titles = ['data analyst', 'data scientist']
            location = os.environ.get('JOB_LOCATION', 'paris')
            
            logger.info('Récupération des offres depuis Adzuna...')
            keywords = ' OR '.join(titles)
            offers = fetch_from_adzuna(keywords=keywords, location=location, max_results=50)
            
            # Filtrer les offres
            filtered = filter_offers_by_title_and_location(offers, titles, location)
            if filtered:
                job_offers = filtered
                logger.info(f'Chargé {len(job_offers)} offres depuis Adzuna')
        except Exception as e:
            logger.warning(f'Erreur Adzuna: {e}, utilisation données test')
    
    logger.info(f'Données chargées: {len(cv_data)} CV(s), {len(job_offers)} offre(s)')

    # Config depuis .env
    spacy_model = os.environ.get('SPACY_MODEL', 'fr_core_news_sm')
    bert_model = os.environ.get('BERT_MODEL')
    gpt_key = os.environ.get('GPT_3_API_KEY')
    notification_email = os.environ.get('NOTIFICATION_EMAIL')

    # Initialiser les agents
    cv_analyzer = CVAnalyzer(cv_data, spacy_model)
    job_analyzer = JobOfferAnalyzer(job_offers, bert_model)
    letter_generator = MotivationLetterGenerator(cv_analyzer, job_analyzer, gpt_key)
    notification_agent = NotificationAgent(job_analyzer, EmailSender())

    logger.info('Agents initialisés avec succès')

    # Vérifier qu'on a des données
    if not cv_data and not job_offers:
        logger.warning('Aucune donnée à traiter. Ajoutez des données dans src/data/*.json')
        return

    # Traitement
    try:
        logger.info('Début du traitement...')
        
        # Analyser les CV
        cv_analyzer.analyze_cvs()
        
        # Extraire mes compétences
        my_skills = cv_analyzer.get_all_skills()
        
        # Comparer avec les offres
        job_analyzer.compare_job_offers(cv_skills=my_skills)
        
        # Générer les lettres
        letter_generator.generate_letters()
        
        # Envoyer les notifications
        notification_agent.send_notifications(recipient_email=notification_email)
        
        logger.info('Traitement terminé avec succès')
        
    except KeyboardInterrupt:
        logger.info('Arrêt manuel')
    except Exception as e:
        logger.exception(f'Erreur: {e}')


if __name__ == "__main__":
    main()