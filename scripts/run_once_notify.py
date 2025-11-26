from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'app'))
# Optional DB
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from db.session import get_session
    from db.models import User, CV as CVModel, Preference, JobOffer as JobOfferModel
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

from agents.cv_analyzer import CVAnalyzer
from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.motivation_letter_generator import MotivationLetterGenerator
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender
from utils.notification_logger import log_notification
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('run_once_notify')

def run_once():
    logger.info('Starting single-run notification process')

    base_dir = os.path.join(os.path.dirname(__file__), 'src')
    
    from main import get_test_data  # reuse helper
    from utils.adzuna_api import fetch_from_adzuna
    from utils.job_fetcher import filter_offers_by_title_and_location
    
    test_data = get_test_data()

    # Load CVs from DB if available
    cv_data = []
    if DB_AVAILABLE:
        try:
            session = get_session()
            rows = (
                session.query(CVModel, User)
                .join(User, CVModel.user_id == User.id)
                .all()
            )
            for cv, user in rows:
                cv_data.append({
                    'name': user.name,
                    'email': user.email,
                    'path': cv.file_path,
                    'analysis': cv.analysis or {}
                })
            session.close()
        except Exception:
            cv_data = []
    if not cv_data:
        cv_data = test_data.get('cv_data', [])

    # Load offers from DB if available
    job_offers = []
    if DB_AVAILABLE:
        try:
            session = get_session()
            rows = session.query(JobOfferModel).all()
            for o in rows:
                job_offers.append({
                    'title': o.title,
                    'company': o.company,
                    'description': o.description,
                    'url': o.url,
                    'source': o.source,
                    'created': o.created,
                    'requirements': o.requirements or {},
                    'skills': o.extracted_skills or [],
                })
            session.close()
        except Exception:
            job_offers = []
    if not job_offers:
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
                # Sauvegarder pour l'UI Streamlit
                try:
                    job_file = Path(__file__).parent.parent / 'src' / 'data' / 'job_offers.json'
                    with open(job_file, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(job_offers, f, indent=2, ensure_ascii=False)
                    logger.info(f'Saved {len(job_offers)} offers to {job_file}')
                except Exception as e:
                    logger.warning(f'Failed to save offers to job_offers.json: {e}')
                # Save into DB if available
                if DB_AVAILABLE:
                    try:
                        session = get_session()
                        added = 0
                        for o in job_offers:
                            url = o.get('url') or ''
                            if not url:
                                continue
                            exists = session.query(JobOfferModel).filter_by(url=url).one_or_none()
                            if exists:
                                continue
                            offer = JobOfferModel(
                                title=o.get('title',''),
                                company=o.get('company',''),
                                description=o.get('description','')[:3900],
                                url=url,
                                source=o.get('source',''),
                                created=o.get('created',''),
                                requirements=o.get('requirements') or {},
                                extracted_skills=o.get('skills') or [],
                            )
                            session.add(offer)
                            added += 1
                        session.commit()
                        logger.info(f"Saved {added} offers to DB")
                    except Exception as e:
                        logger.warning(f"Failed to save offers to DB: {e}")
                    finally:
                        try:
                            session.close()
                        except Exception:
                            pass
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

    job_analyzer.compare_job_offers(cv_skills=candidate_skills, cv_data=cv_data)
    logger.info(f'Analyzed offers: {len(job_analyzer.analyzed_offers)}')

    # Generate letters (optional) and send notifications
    letter_generator.generate_letters()
    generated_letters = letter_generator.get_generated_letters()

    # Send notifications to all collaborators
    total_sent = 0
    # Charger préférences utilisateur
    user_prefs = []
    if DB_AVAILABLE:
        try:
            session = get_session()
            rows = (
                session.query(Preference, User)
                .join(User, Preference.user_id == User.id)
                .all()
            )
            for pref, user in rows:
                user_prefs.append({
                    'name': user.name,
                    'email': user.email,
                    'min_match_score': pref.min_match_score,
                })
            session.close()
        except Exception:
            user_prefs = []
    if not user_prefs:
        try:
            pref_path = Path(__file__).parent.parent / 'src' / 'data' / 'user_preferences.json'
            with open(pref_path, 'r', encoding='utf-8') as f:
                user_prefs = json.load(f)
        except Exception:
            user_prefs = []

    for cv in cv_data:
        if isinstance(cv, dict) and cv.get('email'):
            recipient_email = cv['email']
            recipient_name = cv.get('name', 'Collaborateur')
            logger.info(f'Sending notifications to {recipient_name} ({recipient_email})')
            # Appliquer le seuil depuis préférences si disponible
            try:
                pref = next((p for p in user_prefs if (p.get('email') == recipient_email or p.get('name') == recipient_name)), None)
                if pref and isinstance(pref.get('min_match_score'), (int, float)):
                    notification_agent.min_match_score = float(pref['min_match_score']) / 100.0
                    logger.info(f"Using min_match_score={notification_agent.min_match_score} for {recipient_name}")
            except Exception as e:
                logger.warning(f"Failed to apply min_match_score for {recipient_name}: {e}")
            
            sent = notification_agent.send_notifications(
                recipient_email=recipient_email, 
                force=True, 
                generated_letters=generated_letters
            )
            total_sent += sent
            logger.info(f'Sent {sent} notification(s) to {recipient_name}')
            
            # Enregistrer dans l'historique
            if sent > 0:
                log_notification(
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    job_count=sent,
                    status="success"
                )

    logger.info(f'Notification run completed. Total emails sent: {total_sent}')

if __name__ == '__main__':
    run_once()
