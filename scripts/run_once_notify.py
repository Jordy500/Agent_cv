from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agents.cv_analyzer import CVAnalyzer
from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.motivation_letter_generator import MotivationLetterGenerator
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('run_once_notify')

def run_once():
    logger.info('Starting single-run notification process')

    base_dir = os.path.join(os.path.dirname(__file__), 'src')
    
    from main import get_test_data  # reuse helper
    from utils.adzuna_api import fetch_from_adzuna
    from utils.job_fetcher import filter_offers_by_title_and_location
    
    test_data = get_test_data()

    cv_data = test_data.get('cv_data', [])
    job_offers = test_data.get('job_offers', [])
    
    # Fetch real offers from Adzuna if configured
    job_source = os.environ.get('JOB_SOURCE', '').lower()
    logger.info(f'JOB_SOURCE from env: "{job_source}"')
    if job_source == 'adzuna':
        try:
            logger.info('Fetching job offers from Adzuna API')
            titles = ['data analyst', 'data scientist']
            location_keyword = os.environ.get('JOB_LOCATION', 'paris')
            keywords = ' OR '.join(titles)
            ext_offers = fetch_from_adzuna(keywords=keywords, location=location_keyword, max_results=50)
            filtered = filter_offers_by_title_and_location(ext_offers, titles, location_keyword)
            if filtered:
                job_offers = filtered
                logger.info(f'Using {len(job_offers)} offers from Adzuna')
        except Exception as e:
            logger.warning(f'Failed to fetch Adzuna offers: {e}; using test data')

    spacy_model = os.environ.get('SPACY_MODEL')
    bert_model = os.environ.get('BERT_MODEL')
    gpt_key = os.environ.get('GPT_3_API_KEY')

    cv_analyzer = CVAnalyzer(cv_data, spacy_model)
    job_analyzer = JobOfferAnalyzer(job_offers, bert_model)
    letter_generator = MotivationLetterGenerator(cv_analyzer, job_analyzer, gpt_key)
    email_sender = EmailSender()
    notification_agent = NotificationAgent(job_analyzer, email_sender)

    # Run analysis once
    cv_analyzer.analyze_cvs()
    candidate_skills = cv_analyzer.get_all_skills()
    logger.info(f'Extracted candidate skills: {candidate_skills}')

    job_analyzer.compare_job_offers(cv_skills=candidate_skills)
    logger.info(f'Analyzed offers: {len(job_analyzer.analyzed_offers)}')

    # Generate letters (optional) and send notifications
    letter_generator.generate_letters()
    generated_letters = letter_generator.get_generated_letters()

    notification_email = os.environ.get('NOTIFICATION_EMAIL') or (test_data.get('user_preferences') or {}).get('email')
    # For user-requested immediate send, force=True will bypass duplicate checks
    sent = notification_agent.send_notifications(recipient_email=notification_email, force=True, generated_letters=generated_letters)

    logger.info(f'Notification run completed. Emails sent: {sent}')

if __name__ == '__main__':
    run_once()
