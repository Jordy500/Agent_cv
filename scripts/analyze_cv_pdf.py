#!/usr/bin/env python3
"""
Analyze CV PDF and update cv_data.json with extracted skills.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dotenv import load_dotenv
load_dotenv()

from agents.cv_analyzer import CVAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Analyze CV PDF and update JSON with extracted data."""
    
    cv_json_path = Path(__file__).parent.parent / 'src' / 'data' / 'cv_data.json'
    
    # Load existing CV data
    try:
        with open(cv_json_path, 'r', encoding='utf-8') as f:
            cv_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load cv_data.json: {e}")
        return 1
    
    if not cv_data or not isinstance(cv_data, list):
        logger.error("cv_data.json must contain a list of CV entries")
        return 1
    
    logger.info(f"Found {len(cv_data)} CV entry/entries in cv_data.json")
    
    # Get spaCy model from env
    spacy_model = os.environ.get('SPACY_MODEL', 'fr_core_news_sm')
    
    # Analyze CVs
    analyzer = CVAnalyzer(cv_data, spacy_model)
    analyzer.analyze_cvs()
    
    # Get extracted skills
    all_skills = analyzer.get_all_skills()
    logger.info(f"Extracted {len(all_skills)} skills from CV(s): {all_skills}")
    
    # cv_data is already updated in-place by analyzer.analyze_cvs()
    # Just log the results
    for cv in cv_data:
        name = cv.get('name', 'unknown')
        skills = cv.get('analysis', {}).get('skills', [])
        logger.info(f"CV '{name}' now has {len(skills)} skills: {skills}")
    
    # Save updated JSON
    try:
        with open(cv_json_path, 'w', encoding='utf-8') as f:
            json.dump(cv_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Successfully updated {cv_json_path}")
        return 0
    except Exception as e:
        logger.error(f"Failed to save updated cv_data.json: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
