import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv
load_dotenv()

from agents.cv_analyzer import CVAnalyzer
from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.motivation_letter_generator import MotivationLetterGenerator
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender
from utils.adzuna_api import fetch_from_adzuna
from utils.job_fetcher import filter_offers_by_title_and_location

log_dir = Path(__file__).parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduler')


def load_cv_data():
    cv_json = Path(__file__).parent.parent / 'src' / 'data' / 'cv_data.json'
    try:
        with open(cv_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load CV data: {e}")
        return []


def load_seen_offers():
    seen_file = Path(__file__).parent.parent / 'logs' / 'seen_offers.json'
    if seen_file.exists():
        try:
            with open(seen_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            logger.warning(f"Failed to load seen offers: {e}")
    return set()


def save_seen_offers(seen_ids):
    seen_file = Path(__file__).parent.parent / 'logs' / 'seen_offers.json'
    try:
        with open(seen_file, 'w', encoding='utf-8') as f:
            json.dump(list(seen_ids), f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save seen offers: {e}")


def fetch_new_jobs():
    job_source = os.environ.get('JOB_SOURCE', '').lower()
    
    if job_source != 'adzuna':
        logger.warning(f"Job source '{job_source}' not supported by scheduler (only 'adzuna')")
        return []
    
    try:
        logger.info("Fetching job offers from Adzuna API")
        titles = ['data analyst', 'data scientist']
        location_keyword = os.environ.get('JOB_LOCATION', 'paris')
        keywords = ' OR '.join(titles)
        
        offers = fetch_from_adzuna(keywords=keywords, location=location_keyword, max_results=50)
        filtered = filter_offers_by_title_and_location(offers, titles, location_keyword)
        
        logger.info(f"Fetched {len(offers)} offers, {len(filtered)} after filtering")
        return filtered
    except Exception as e:
        logger.error(f"Failed to fetch jobs: {e}")
        return []


def main():
    logger.info("=" * 80)
    logger.info(f"JOB NOTIFICATION SCHEDULER STARTED - {datetime.now()}")
    logger.info("=" * 80)
    
    cv_data = load_cv_data()
    if not cv_data:
        logger.error("No CV data found. Exiting.")
        return 1

    job_offers = fetch_new_jobs()
    if not job_offers:
        logger.info("No job offers found. Exiting.")
        return 0

    seen_ids = load_seen_offers()
    logger.info(f"Previously seen {len(seen_ids)} offers")

    new_offers = []
    for offer in job_offers:
        offer_id = offer.get('url', '') or offer.get('title', '')
        if offer_id and offer_id not in seen_ids:
            new_offers.append(offer)
            seen_ids.add(offer_id)
    
    logger.info(f"Found {len(new_offers)} new offers (not seen before)")
    
    if not new_offers:
        logger.info("No new offers to process. Exiting.")
        return 0

    spacy_model = os.environ.get('SPACY_MODEL', 'fr_core_news_sm')
    bert_model = os.environ.get('BERT_MODEL')
    gpt_key = os.environ.get('GPT_3_API_KEY')
    
    cv_analyzer = CVAnalyzer(cv_data, spacy_model)
    cv_analyzer.analyze_cvs()
    candidate_skills = cv_analyzer.get_all_skills()
    
    job_analyzer = JobOfferAnalyzer(new_offers, bert_model)
    job_analyzer.compare_job_offers(cv_skills=candidate_skills)

    letter_generator = MotivationLetterGenerator(cv_analyzer, job_analyzer, gpt_key)
    letter_generator.generate_letters()
    
    email_sender = EmailSender()
    notification_agent = NotificationAgent(job_analyzer, email_sender)
    
    generated_letters = letter_generator.get_generated_letters()
    
    # Send notifications to all collaborators
    total_sent = 0
    for cv in cv_data:
        if isinstance(cv, dict) and cv.get('email'):
            recipient_email = cv['email']
            recipient_name = cv.get('name', 'Collaborateur')
            logger.info(f'Sending notifications to {recipient_name} ({recipient_email})')
            
            sent = notification_agent.send_notifications(
                recipient_email=recipient_email,
                force=True,
                generated_letters=generated_letters
            )
            total_sent += sent
            logger.info(f'Sent {sent} notification(s) to {recipient_name}')
    
    logger.info(f"Total notifications sent: {total_sent}")

    save_seen_offers(seen_ids)
    
    logger.info("=" * 80)
    logger.info(f"JOB NOTIFICATION SCHEDULER COMPLETED - {datetime.now()}")
    logger.info("=" * 80)
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
