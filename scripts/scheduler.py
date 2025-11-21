#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduler pour récupérer automatiquement les offres d'emploi
Fait par Jordy - 2025

Ce script tourne en boucle via Windows Task Scheduler
Il check les nouvelles offres sur Adzuna, compare avec mon CV,
génère des lettres de motivation et m'envoie des emails
"""

import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Je dois ajouter le dossier src au path pour importer mes modules
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir / 'src'))

# Charger les variables d'environnement depuis .env
from dotenv import load_dotenv
load_dotenv()

# Mes agents et utilitaires
from agents.cv_analyzer import CVAnalyzer
from agents.job_offer_analyzer import JobOfferAnalyzer
from agents.motivation_letter_generator import MotivationLetterGenerator
from agents.notification_agent import NotificationAgent
from utils.email_sender import EmailSender
from utils.adzuna_api import fetch_from_adzuna
from utils.job_fetcher import filter_offers_by_title_and_location

# Configuration des logs - je log tout dans un fichier par jour
log_dir = current_dir / 'logs'
log_dir.mkdir(exist_ok=True)

today = datetime.now().strftime('%Y%m%d')
log_file = log_dir / f"scheduler_{today}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduler')


def load_cv_data():
    """Charge les données de mon CV depuis le fichier JSON"""
    cv_json = current_dir / 'src' / 'data' / 'cv_data.json'
    try:
        with open(cv_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"CV chargé avec succès: {len(data)} entrée(s)")
            return data
    except Exception as e:
        logger.error(f"Erreur lors du chargement du CV: {e}")
        return []


def load_seen_offers():
    """
    Charge la liste des offres déjà vues pour éviter les doublons
    J'utilise un set pour check rapidement si l'offre existe déjà
    """
    seen_file = current_dir / 'logs' / 'seen_offers.json'
    
    if not seen_file.exists():
        logger.debug("Pas encore d'offres vues - première exécution")
        return set()
    
    try:
        with open(seen_file, 'r', encoding='utf-8') as f:
            offers_list = json.load(f)
            logger.debug(f"Chargé {len(offers_list)} offres déjà vues")
            return set(offers_list)
    except Exception as e:
        logger.warning(f"Impossible de charger les offres vues: {e}")
        return set()


def save_seen_offers(seen_ids):
    """Sauvegarde les IDs des offres qu'on a déjà traitées"""
    seen_file = current_dir / 'logs' / 'seen_offers.json'
    try:
        with open(seen_file, 'w', encoding='utf-8') as f:
            json.dump(list(seen_ids), f, indent=2, ensure_ascii=False)
        logger.debug(f"Sauvegardé {len(seen_ids)} offres vues")
    except Exception as e:
        logger.error(f"Erreur sauvegarde seen_offers: {e}")


def fetch_new_jobs():
    """
    Récupère les nouvelles offres depuis Adzuna
    Je cherche les postes Data Analyst et Data Scientist à Paris
    """
    job_source = os.environ.get('JOB_SOURCE', '').lower()
    
    if job_source != 'adzuna':
        logger.warning(f"Source '{job_source}' pas supportée (seulement 'adzuna')")
        return []
    
    try:
        logger.info("Récupération des offres depuis Adzuna API")
        
        # Les postes qui m'intéressent
        titles = ['data analyst', 'data scientist']
        location_keyword = os.environ.get('JOB_LOCATION', 'paris')
        keywords = ' OR '.join(titles)
        
        # Fetch depuis Adzuna (max 50 par appel)
        offers = fetch_from_adzuna(keywords=keywords, location=location_keyword, max_results=50)
        
        # Filtrer pour garder que les postes data à Paris
        filtered = filter_offers_by_title_and_location(offers, titles, location_keyword)
        
        logger.info(f"Récupéré {len(offers)} offres, {len(filtered)} après filtrage")
        return filtered
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des offres: {e}")
        return []


def main():
    """
    Fonction principale du scheduler
    C'est ici que tout se passe !
    """
    logger.info("=" * 80)
    logger.info(f"DÉMARRAGE DU SCHEDULER - {datetime.now()}")
    logger.info("=" * 80)
    
    # 1. Charger mon CV
    cv_data = load_cv_data()
    if not cv_data:
        logger.error("Impossible de charger le CV. Abandon.")
        return 1
    
    # 2. Fetch les nouvelles offres
    job_offers = fetch_new_jobs()
    if not job_offers:
        logger.info("Aucune offre trouvée. Fin.")
        return 0
    
    # 3. Charger les offres déjà vues pour éviter les doublons
    seen_ids = load_seen_offers()
    logger.info(f"J'ai déjà vu {len(seen_ids)} offres")
    
    # 4. Filtrer les nouvelles offres (pas encore vues)
    new_offers = []
    for offer in job_offers:
        # J'utilise l'URL comme identifiant unique
        offer_id = offer.get('url', '') or offer.get('title', '')
        if offer_id and offer_id not in seen_ids:
            new_offers.append(offer)
            seen_ids.add(offer_id)
    
    logger.info(f"Trouvé {len(new_offers)} nouvelles offres (jamais vues)")
    
    if not new_offers:
        logger.info("Pas de nouvelles offres à traiter. Fin.")
        return 0
    
    # 5. Analyser mon CV et les offres
    spacy_model = os.environ.get('SPACY_MODEL', 'fr_core_news_sm')
    bert_model = os.environ.get('BERT_MODEL')  # Pas encore utilisé mais prévu
    gpt_key = os.environ.get('GPT_3_API_KEY')
    
    # Analyser mon CV pour extraire mes compétences
    logger.debug("Analyse du CV...")
    cv_analyzer = CVAnalyzer(cv_data, spacy_model)
    cv_analyzer.analyze_cvs()
    my_skills = cv_analyzer.get_all_skills()
    
    # Comparer les offres avec mes skills
    logger.debug(f"Analyse des {len(new_offers)} offres...")
    job_analyzer = JobOfferAnalyzer(new_offers, bert_model)
    job_analyzer.compare_job_offers(cv_skills=my_skills)
    
    # 6. Générer les lettres de motivation
    logger.debug("Génération des lettres de motivation...")
    letter_generator = MotivationLetterGenerator(cv_analyzer, job_analyzer, gpt_key)
    letter_generator.generate_letters()
    
    # 7. Envoyer les notifications par email
    logger.debug("Préparation des emails...")
    email_sender = EmailSender()
    notification_agent = NotificationAgent(job_analyzer, email_sender)
    
    my_email = os.environ.get('NOTIFICATION_EMAIL')
    letters = letter_generator.get_generated_letters()
    
    sent_count = notification_agent.send_notifications(
        recipient_email=my_email,
        force=True,  # Force l'envoi même si déjà notifié (session différente)
        generated_letters=letters
    )
    
    logger.info(f"✉️  {sent_count} emails envoyés avec succès!")
    
    # 8. Sauvegarder les offres qu'on a traitées
    save_seen_offers(seen_ids)
    
    logger.info("=" * 80)
    logger.info(f"SCHEDULER TERMINÉ - {datetime.now()}")
    logger.info("=" * 80)
    
    return 0


if __name__ == '__main__':
    # Point d'entrée - exécuté quand le script est lancé
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Arrêt manuel du scheduler")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        sys.exit(1)
