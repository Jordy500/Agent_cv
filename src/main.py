import os
import time
from agents.cv_analyzer import CVAnalyzer
from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.motivation_letter_generator import MotivationLetterGenerator
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender
from utils.text_processing import get_spacy_model
from utils.database_handler import DatabaseHandler
from dotenv import load_dotenv


def main():
    # Charger variables d'environnement depuis .env si présent
    load_dotenv()

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise RuntimeError('DATABASE_URL not set in environment')

    # Initialiser la base de données
    db_handler = DatabaseHandler(db_url)

    # Charger les modèles/config depuis variables d'environnement
    spacy_model = os.environ.get('SPACY_MODEL')
    bert_model = os.environ.get('BERT_MODEL')
    gpt_key = os.environ.get('GPT_3_API_KEY')

    # Initialiser les agents
    cv_data = db_handler.get_cv_data()
    job_offers = db_handler.get_job_offers()

    # CVAnalyzer attends un itérable de dicts et un modèle spaCy (nom ou objet)
    cv_analyzer = CVAnalyzer(cv_data, spacy_model)
    job_analyzer = JobOfferAnalyzer(job_offers, bert_model)
    letter_generator = MotivationLetterGenerator(cv_analyzer, job_analyzer, gpt_key)
    notification_agent = NotificationAgent(job_analyzer, EmailSender())

    # Processus principale (ajoutez une pause ou remplacez par scheduler selon besoin)
    try:
        while True:
            cv_analyzer.analyze_cvs()
            job_analyzer.compare_job_offers()
            letter_generator.generate_letters()
            notification_agent.send_notifications()
            # Petite pause pour éviter boucle serrée (configurable via env `LOOP_SLEEP_SECONDS`)
            time.sleep(int(os.environ.get('LOOP_SLEEP_SECONDS', 60)))
    except KeyboardInterrupt:
        print('Shutting down')


if __name__ == "__main__":
    main()