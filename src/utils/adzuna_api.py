"""Adzuna API adapter for fetching job offers.

Adzuna provides a free REST API for job search across multiple countries.
Free tier: 1000 calls/month.

Documentation: https://developer.adzuna.com/docs/search
"""
from __future__ import annotations
import os
import logging
from typing import List, Dict, Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None


def fetch_from_adzuna(keywords: str = "data analyst OR data scientist",
                      location: str = "Paris",
                      max_results: int = 50,
                      country: str = "fr") -> List[Dict[str, Any]]:
    """Fetch job offers from Adzuna API.
    
    Args:
        keywords: Search keywords
        location: Location (city name)
        max_results: Maximum number of results (API returns max 50 per page)
        country: Country code (fr, uk, us, etc.)
    
    Returns:
        List of offer dicts with keys: title, company, location, description, url
    """
    if not requests:
        raise RuntimeError("requests library not installed")
    
    app_id = os.environ.get('ADZUNA_APP_ID')
    app_key = os.environ.get('ADZUNA_APP_KEY')
    
    if not app_id or not app_key:
        raise RuntimeError("ADZUNA_APP_ID and ADZUNA_APP_KEY must be set in environment")
    
    # Adzuna API endpoint
    # Format: https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
    base_url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    
    params = {
        'app_id': app_id,
        'app_key': app_key,
        'what': keywords,
        'where': location,
        'results_per_page': min(max_results, 50),  # API max is 50
        'content-type': 'application/json'
    }
    
    try:
        logger.info(f"Fetching jobs from Adzuna: {keywords} in {location}")
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse results
        offers = []
        results = data.get('results', [])
        
        for item in results:
            offer = {
                'title': item.get('title', 'N/A'),
                'company': item.get('company', {}).get('display_name', 'N/A'),
                'location': item.get('location', {}).get('display_name', location),
                'description': item.get('description', ''),
                'url': item.get('redirect_url', ''),
                'source': 'adzuna.com',
                'created': item.get('created', ''),
                'salary_min': item.get('salary_min'),
                'salary_max': item.get('salary_max'),
                'contract_type': item.get('contract_type', '')
            }
            # Debug: log first offer's description length
            if len(offers) == 0:
                logger.debug(f"First offer description length: {len(offer['description'])} chars")
            offers.append(offer)
        
        logger.info(f"Fetched {len(offers)} offers from Adzuna")
        return offers
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise RuntimeError("Adzuna API authentication failed. Check your APP_ID and APP_KEY") from e
        elif e.response.status_code == 429:
            raise RuntimeError("Adzuna API rate limit exceeded") from e
        else:
            raise RuntimeError(f"Adzuna API error: {e}") from e
    except Exception as e:
        logger.error(f"Failed to fetch from Adzuna: {e}")
        raise


def test_adzuna_connection() -> bool:
    """Test if Adzuna API credentials are valid.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        offers = fetch_from_adzuna(keywords="data", location="Paris", max_results=1)
        return len(offers) >= 0  # Even 0 results means connection is OK
    except Exception as e:
        logger.error(f"Adzuna connection test failed: {e}")
        return False
