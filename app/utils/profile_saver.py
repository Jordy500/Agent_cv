import json
from pathlib import Path
from typing import Dict

# Optional DB imports
try:
    from db.session import get_session
    from db.models import User, Preference
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "src" / "data"

def save_user_profile(user_name: str, profile_data: Dict):
    """
    Sauvegarde/Met à jour le profil (DB si dispo, sinon user_preferences.json)
    """
    try:
        if DB_AVAILABLE:
            session = get_session()
            try:
                # Upsert user by email or name
                email = profile_data.get('email')
                user = None
                if email:
                    user = session.query(User).filter_by(email=email).one_or_none()
                if not user:
                    user = session.query(User).filter_by(name=user_name).one_or_none()
                if not user:
                    user = User(name=user_name, email=email)
                    session.add(user)
                    session.flush()

                pref = session.query(Preference).filter_by(user_id=user.id).one_or_none()
                if not pref:
                    pref = Preference(user_id=user.id)
                    session.add(pref)

                pref.keywords = profile_data.get('keywords', [])
                pref.location = profile_data.get('location', '')
                pref.contract_types = profile_data.get('contract_types', [])
                pref.min_match_score = int(profile_data.get('match_score', 70))
                pref.notify_via_email = bool(profile_data.get('notify_via_email', True))

                session.commit()
                return True, "Profil sauvegardé avec succès !"
            except Exception as e:
                session.rollback()
                return False, f"Erreur lors de la sauvegarde (DB) : {str(e)}"
            finally:
                session.close()

        # JSON fallback
        pref_path = DATA_DIR / "user_preferences.json"
        
        # Charger les données existantes
        if pref_path.exists():
            with open(pref_path, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
        else:
            preferences = []
        
        # Chercher l'utilisateur
        user_found = False
        for i, user in enumerate(preferences):
            if user.get('name') == user_name:
                # Mettre à jour les préférences
                preferences[i].update({
                    'email': profile_data.get('email'),
                    'preferred_jobs': profile_data.get('keywords', []),
                    'location': profile_data.get('location', ''),
                    'contract_types': profile_data.get('contract_types', []),
                    'min_match_score': profile_data.get('match_score', 70),
                    'notify_via_email': profile_data.get('notify_via_email', True)
                })
                user_found = True
                break
        
        # Si l'utilisateur n'existe pas, l'ajouter
        if not user_found:
            preferences.append({
                'name': user_name,
                'email': profile_data.get('email'),
                'preferred_jobs': profile_data.get('keywords', []),
                'location': profile_data.get('location', ''),
                'contract_types': profile_data.get('contract_types', []),
                'min_match_score': profile_data.get('match_score', 70),
                'notify_via_email': True
            })
        
        # Sauvegarder
        with open(pref_path, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, indent=2, ensure_ascii=False)
        
        return True, "Profil sauvegardé avec succès !"
        
    except Exception as e:
        return False, f"Erreur lors de la sauvegarde : {str(e)}"
