# -*- coding: utf-8 -*-
"""
Fonctions de vérification et utilitaires
Par Jordy - 2025
"""

import os
import logging

logger = logging.getLogger(__name__)


def check_file_exists(file_path, description="File"):
    """Vérifie si un fichier existe"""
    if not os.path.isfile(file_path):
        logger.warning(f'{description} not found: {file_path}')
        return False
    return True


def check_env_var(var_name, required=False):
    """Vérifie si une variable d'environnement existe"""
    value = os.environ.get(var_name)
    if value:
        logger.debug(f'Environment variable {var_name} is set')
        return value
    
    if required:
        logger.error(f'Required environment variable {var_name} not set')
    else:
        logger.debug(f'Optional environment variable {var_name} not set')
    
    return None


def check_api_key(api_key, key_name='API Key', min_length=10):
    """Vérifie la validité d'une clé API"""
    if not api_key:
        logger.debug(f'{key_name} not provided')
        return False
    
    if len(str(api_key)) < min_length:
        logger.warning(f'{key_name} looks invalid (too short: {len(api_key)} chars)')
        return False
    
    logger.debug(f'{key_name} appears valid')
    return True


def safe_extract_pdf_text(pdf_path, fallback_text=""):
    """Extrait le texte d'un PDF avec gestion d'erreur"""
    if not check_file_exists(pdf_path, "PDF file"):
        return fallback_text
    
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text += page_text
        
        if text.strip():
            logger.debug(f'Extracted {len(text)} chars from {pdf_path}')
            return text
        else:
            logger.warning(f'PDF {pdf_path} is empty or unreadable')
            return fallback_text
    
    except Exception as e:
        logger.warning(f'Failed to extract PDF text from {pdf_path}: {e}')
        return fallback_text
