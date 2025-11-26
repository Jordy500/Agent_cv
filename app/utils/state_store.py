import json
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "src" / "data"
STATE_FILE = DATA_DIR / "user_state.json"


def load_user_state(user_name: str) -> Dict:
    """Charge l'état UI (favoris, vues, masquées) pour un utilisateur."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}

    state = data.get(user_name) or {
        'favorites': [],
        'viewed': [],
        'hidden': [],
    }
    # Normaliser en listes uniques
    state['favorites'] = list(dict.fromkeys(state.get('favorites', [])))
    state['viewed'] = list(dict.fromkeys(state.get('viewed', [])))
    state['hidden'] = list(dict.fromkeys(state.get('hidden', [])))
    return state


def save_user_state(user_name: str, state: Dict) -> None:
    """Sauvegarde l'état UI pour un utilisateur."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}

    data[user_name] = {
        'favorites': list(dict.fromkeys(state.get('favorites', []))),
        'viewed': list(dict.fromkeys(state.get('viewed', []))),
        'hidden': list(dict.fromkeys(state.get('hidden', []))),
    }

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
