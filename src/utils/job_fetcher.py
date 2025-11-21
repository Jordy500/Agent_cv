# -*- coding: utf-8 -*-
"""
Utilitaires pour filtrer les offres d'emploi
Par Jordy - 2025
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def filter_offers_by_title_and_location(offers: List[Dict[str, Any]],
                                       titles: List[str],
                                       location_keyword: str) -> List[Dict[str, Any]]:
    """
    Filtre les offres selon le titre et la localisation
    
    Args:
        offers: Liste d'offres
        titles: Liste des titres recherchés (ex: ['data analyst', 'data scientist'])
        location_keyword: Mot-clé de localisation (ex: 'paris')
    
    Returns:
        Liste des offres filtrées
    """
    titles_lower = [t.lower() for t in titles]
    loc_lower = location_keyword.lower() if location_keyword else ''

    def match_title(offer_title: str) -> bool:
        """Check si le titre de l'offre correspond"""
        if not offer_title:
            return False
        t = offer_title.lower()
        return any(key in t for key in titles_lower)

    def match_location(offer_loc: str, desc: str) -> bool:
        """Check si la localisation correspond"""
        if not loc_lower:
            return True  # Pas de filtre localisation
        if offer_loc and loc_lower in offer_loc.lower():
            return True
        if desc and loc_lower in desc.lower():
            return True
        return False

    # Filtrage
    filtered = []
    for o in offers:
        if match_title(o.get('title', '')) and match_location(o.get('location', ''), o.get('description', '')):
            filtered.append(o)
    
    return filtered

