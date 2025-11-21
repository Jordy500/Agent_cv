import os
import requests
import logging
import time

from .rate_limiter import openai_limiter

logger = logging.getLogger(__name__)


def chat_completion(messages, model="gpt-3.5-turbo", max_tokens=500, temperature=0.7, 
                   max_retries=3, initial_delay=1.0):
    """Call OpenAI Chat Completions via REST API with exponential backoff retry.

    Args:
        messages: list of dicts like [{"role":"user","content":"..."}, ...]
        model: OpenAI model name
        max_tokens: maximum tokens in response
        temperature: randomness (0.0-2.0)
        max_retries: maximum number of retry attempts for rate limit errors
        initial_delay: initial delay in seconds before first retry
        
    Returns:
        The assistant text or raises RuntimeError on failure.
    """
    api_key = os.environ.get('GPT_3_API_KEY')
    if not api_key:
        raise RuntimeError('GPT_3_API_KEY not set')

    url = 'https://api.openai.com/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': temperature
    }

    last_exception = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            # Use global rate limiter to prevent exceeding API quota
            with openai_limiter:
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            
            # Navigate response to get text
            if 'choices' in data and len(data['choices']) > 0:
                choice = data['choices'][0]
                # Try assistant content in message
                if 'message' in choice and 'content' in choice['message']:
                    return choice['message']['content'].strip()
                if 'text' in choice:
                    return choice['text'].strip()
            raise RuntimeError('No completion returned by OpenAI')
            
        except requests.exceptions.HTTPError as e:
            last_exception = e

            if e.response.status_code in [429, 500, 502, 503, 504]:
                if attempt < max_retries:
                    logger.warning(
                        f'OpenAI API error {e.response.status_code} (attempt {attempt + 1}/{max_retries + 1}). '
                        f'Retrying in {delay:.1f}s...'
                    )
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f'OpenAI API error {e.response.status_code} after {max_retries + 1} attempts')
                    raise RuntimeError(f'OpenAI API failed after retries: {e}') from e
            else:

                logger.error(f'OpenAI API error: {e}')
                raise RuntimeError(f'OpenAI API error: {e}') from e
                
        except Exception as e:
            last_exception = e
            logger.warning(f'OpenAI chat_completion failed: {e}')
            if attempt < max_retries:
                logger.info(f'Retrying in {delay:.1f}s...')
                time.sleep(delay)
                delay *= 2
                continue
            raise
    
    # If we get here, all retries failed
    if last_exception:
        raise last_exception
    raise RuntimeError('OpenAI chat_completion failed after all retries')
