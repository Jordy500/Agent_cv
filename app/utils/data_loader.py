import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Optional DB imports (fallback to JSON if DB unavailable)
try:
    from db.session import get_session
    from db.models import User, CV, Preference, JobOffer, Notification
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

# Chemins vers les fichiers de données
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "src" / "data"

def load_cv_data() -> List[Dict]:
    """Charge les données des CVs (DB si dispo, sinon JSON)"""
    if DB_AVAILABLE:
        try:
            session = get_session()
            rows = (
                session.query(CV, User)
                .join(User, CV.user_id == User.id)
                .all()
            )
            result = []
            for cv, user in rows:
                result.append({
                    'name': user.name,
                    'email': user.email,
                    'path': cv.file_path,
                    'analysis': cv.analysis or {},
                    'updated_at': getattr(cv, 'updated_at', None).isoformat() if getattr(cv, 'updated_at', None) else None,
                    'created_at': getattr(cv, 'created_at', None).isoformat() if getattr(cv, 'created_at', None) else None,
                })
            session.close()
            return result
        except Exception:
            pass
    cv_file = DATA_DIR / "cv_data.json"
    if cv_file.exists():
        with open(cv_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def load_job_offers() -> List[Dict]:
    """Charge les offres d'emploi (DB si dispo, sinon JSON)"""
    if DB_AVAILABLE:
        try:
            session = get_session()
            rows = session.query(JobOffer).all()
            result = []
            for o in rows:
                result.append({
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
            return result
        except Exception:
            pass
    job_file = DATA_DIR / "job_offers.json"
    if job_file.exists():
        with open(job_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def load_user_preferences() -> List[Dict]:
    """Charge les préférences utilisateur (DB si dispo, sinon JSON)"""
    if DB_AVAILABLE:
        try:
            session = get_session()
            rows = (
                session.query(Preference, User)
                .join(User, Preference.user_id == User.id)
                .all()
            )
            result = []
            for pref, user in rows:
                result.append({
                    'name': user.name,
                    'email': user.email,
                    'preferred_jobs': pref.keywords or [],
                    'location': pref.location or '',
                    'contract_types': pref.contract_types or [],
                    'min_match_score': pref.min_match_score,
                    'notify_via_email': pref.notify_via_email,
                })
            session.close()
            return result
        except Exception:
            pass
    pref_file = DATA_DIR / "user_preferences.json"
    if pref_file.exists():
        with open(pref_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_user_by_name(name: str) -> Optional[Dict]:
    """Récupère un utilisateur par son nom"""
    users = load_user_preferences()
    for user in users:
        if user.get('name', '').lower() == name.lower():
            # Trouver les données CV correspondantes
            cv_data_list = load_cv_data()
            for cv in cv_data_list:
                if cv.get('name', '').lower() == name.lower():
                    user['cv_analysis'] = cv.get('analysis', {})
                    user['cv_path'] = cv.get('path', '')
                    break
            return user
    return None

def get_matching_jobs(user_skills: List[str], min_match_percentage: int = 50) -> List[Dict]:
    """Trouve les offres correspondant aux compétences de l'utilisateur"""
    jobs = load_job_offers()
    matched_jobs = []
    
    # Fonction simple d'extraction de compétences si non fournies
    def infer_skills_from_text(title: str, description: str) -> List[str]:
        text = f"{title} {description}".lower()
        keywords = {
            'python','r','java','javascript','typescript','sql','scala','pandas','numpy','scikit-learn','sklearn',
            'tensorflow','pytorch','spark','hadoop','tableau','power bi','excel','machine learning','deep learning',
            'data visualization','visualisation','dataviz','statistical analysis','analyse statistique','data mining',
            'data analysis','aws','azure','gcp','docker','git','api','etl','airflow','dbt','fastapi','django','flask',
            'kubernetes','terraform','ansible','linux','redis','postgres','mysql','mongodb'
        }
        detected = set()
        for kw in keywords:
            if kw in text:
                detected.add(kw)
        return list(detected)
    
    for job in jobs:
        job_skills = [s.lower() for s in job.get('skills', [])]
        if not job_skills:
            # Essayer d'inférer depuis le titre + description
            job_skills = infer_skills_from_text(job.get('title',''), job.get('description',''))
        user_skills_lower = [s.lower() for s in user_skills]
        
        # Calculer le pourcentage de match
        if job_skills:
            matches = sum(1 for skill in job_skills if skill in user_skills_lower)
            match_percentage = (matches / len(job_skills)) * 100
            
            if match_percentage >= min_match_percentage:
                job['match_percentage'] = round(match_percentage)
                job['matched_skills'] = matches
                job['total_skills'] = len(job_skills)
                job['missing_skills'] = [s for s in job_skills if s not in user_skills_lower]
                matched_jobs.append(job)
    
    # Trier par pourcentage de match décroissant
    matched_jobs.sort(key=lambda x: x['match_percentage'], reverse=True)
    return matched_jobs

def calculate_dashboard_metrics() -> Dict:
    """Calcule les métriques pour le dashboard (DB prioritaire)."""
    users = load_user_preferences()
    jobs = load_job_offers()
    cv_data = load_cv_data()

    # Emails envoyés: utiliser la DB si dispo
    emails_sent = 0
    if DB_AVAILABLE:
        try:
            session = get_session()
            # Compter toutes les notifications envoyées
            emails_sent = session.query(Notification).count()
            session.close()
        except Exception:
            emails_sent = 0
    if not emails_sent:
        # Fallback: base sur utilisateurs actifs (approximation)
        emails_sent = sum(1 for user in users if user.get('notify_via_email', False))

    # Nombre total d'offres
    total_offers = len(jobs)

    # Calculer le score moyen de matching
    all_scores = []
    for cv in cv_data:
        skills = cv.get('analysis', {}).get('skills', [])
        if skills:
            matched = get_matching_jobs(skills, min_match_percentage=0)
            if matched:
                avg_score = sum(j['match_percentage'] for j in matched) / len(matched)
                all_scores.append(avg_score)

    avg_match_score = round(sum(all_scores) / len(all_scores)) if all_scores else 0

    return {
        'emails_sent': int(emails_sent),
        'offers_found': total_offers,
        'avg_score': avg_match_score,
        'active_users': len([u for u in users if u.get('notify_via_email', False)])
    }

def load_notification_history(user_email: str = None, limit: int = 10) -> List[Dict]:
    """Charge l'historique des notifications (DB prioritaire)."""
    if DB_AVAILABLE:
        try:
            session = get_session()
            q = session.query(Notification, User).join(User, Notification.user_id == User.id)
            if user_email:
                q = q.filter(User.email == user_email)
            rows = q.order_by(Notification.sent_at.desc()).limit(limit).all()
            result = []
            for n, u in rows:
                result.append({
                    'timestamp': getattr(n, 'sent_at', None).isoformat() if getattr(n, 'sent_at', None) else None,
                    'recipient_email': u.email,
                    'recipient_name': u.name,
                    'job_count': 1,
                    'status': n.status,
                })
            session.close()
            return result
        except Exception:
            pass
    history_file = DATA_DIR / "notification_history.json"
    if not history_file.exists():
        return []
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception:
        return []
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    if user_email:
        history = [n for n in history if n.get('recipient_email') == user_email]
    return history[:limit]

def format_notification_time(timestamp_str: str) -> str:
    """Formate un timestamp en temps relatif"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        delta = now - timestamp
        
        if delta.days > 0:
            return f"Il y a {delta.days} jour{'s' if delta.days > 1 else ''}"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"Il y a {hours} heure{'s' if hours > 1 else ''}"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"Il y a {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return "À l'instant"
    except:
        return timestamp_str
