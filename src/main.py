import os
import logging
import time
from agents.cv_analyzer import CVAnalyzer
from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.motivation_letter_generator import MotivationLetterGenerator
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender
from utils.database_handler import DatabaseHandler
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_test_data():
    """Retourne des données de test quand MongoDB n'est pas disponible."""
    return {
        'cv_data': [],
        'job_offers': []
    }


def main():
    # Charger variables d'environnement depuis .env si présent
    load_dotenv()

    db_url = os.environ.get('DATABASE_URL')
    use_test_mode = os.environ.get('USE_TEST_MODE', 'false').lower() == 'true'
    
    logger.info('Starting Agent_cv...')
    logger.info(f'Test mode: {use_test_mode}')

    # Initialiser les données (MongoDB ou test)
    if db_url and not use_test_mode:
        try:
            db_handler = DatabaseHandler(db_url)
            cv_data = list(db_handler.get_cv_data())
            job_offers = list(db_handler.get_job_offers())
            logger.info(f'Connected to MongoDB: {len(cv_data)} CVs, {len(job_offers)} job offers loaded')
        except Exception as e:
            logger.warning(f'Failed to connect to MongoDB: {e}. Falling back to test mode.')
            test_data = get_test_data()
            cv_data = test_data['cv_data']
            job_offers = test_data['job_offers']
    else:
        logger.info('Using test mode (no MongoDB)')
        test_data = get_test_data()
        cv_data = test_data['cv_data']
        job_offers = test_data['job_offers']

    # Charger les modèles/config depuis variables d'environnement
    spacy_model = os.environ.get('SPACY_MODEL')
    bert_model = os.environ.get('BERT_MODEL')
    gpt_key = os.environ.get('GPT_3_API_KEY')

    # Initialiser les agents
    cv_analyzer = CVAnalyzer(cv_data, spacy_model)
    job_analyzer = JobOfferAnalyzer(job_offers, bert_model)
    letter_generator = MotivationLetterGenerator(cv_analyzer, job_analyzer, gpt_key)
    notification_agent = NotificationAgent(job_analyzer, EmailSender())

    logger.info('All agents initialized successfully')

    # Processus principale
    if not cv_data and not job_offers:
        logger.info('No data to process. Add CVs and job offers to your database or use test mode.')
        logger.info('To add test data, populate src/data/*.json files.')
        return

    try:
        iteration = 0
        while True:
            iteration += 1
            logger.info(f'--- Iteration {iteration} ---')
            cv_analyzer.analyze_cvs()
            job_analyzer.compare_job_offers()
            letter_generator.generate_letters()
            notification_agent.send_notifications()
            sleep_time = int(os.environ.get('LOOP_SLEEP_SECONDS', 60))
            logger.info(f'Sleeping for {sleep_time} seconds...')
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info('Shutting down gracefully...')
    except Exception as e:
        logger.exception(f'Unexpected error: {e}')


if __name__ == "__main__":
    main()