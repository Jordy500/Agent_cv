import json
from pathlib import Path
import sys
from dotenv import load_dotenv

# Ensure project root is on sys.path for 'db' package imports
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load environment variables (e.g., DATABASE_URL) from .env if present
load_dotenv()

from db.session import get_session, engine
from db.models import Base, User, CV, Preference, JobOffer, UserState, Notification

DATA = ROOT / 'src' / 'data'


def init_db():
    Base.metadata.create_all(bind=engine)


def import_from_json():
    session = get_session()
    try:
        # Import users + CVs
        cv_file = DATA / 'cv_data.json'
        if cv_file.exists():
            try:
                cv_list = json.loads(cv_file.read_text(encoding='utf-8'))
            except Exception:
                cv_list = []
            for entry in cv_list or []:
                name = entry.get('name') or 'Utilisateur'
                email = entry.get('email') or None
                user = None
                if email:
                    user = session.query(User).filter_by(email=email).one_or_none()
                if not user:
                    user = User(name=name, email=email or f"{name}@example.com")
                    session.add(user)
                    session.flush()
                # Add CV
                path = entry.get('path') or ''
                analysis = entry.get('analysis') or {}
                cv = CV(user_id=user.id, file_path=path, analysis=analysis)
                session.add(cv)

        # Import preferences
        pref_file = DATA / 'user_preferences.json'
        if pref_file.exists():
            try:
                pref_list = json.loads(pref_file.read_text(encoding='utf-8'))
            except Exception:
                pref_list = []
            for p in pref_list or []:
                name = p.get('name')
                email = p.get('email')
                user = None
                if email:
                    user = session.query(User).filter_by(email=email).one_or_none()
                if not user and name:
                    user = session.query(User).filter_by(name=name).one_or_none()
                if not user and email:
                    user = User(name=name or 'Utilisateur', email=email)
                    session.add(user)
                    session.flush()
                if user:
                    pref = session.query(Preference).filter_by(user_id=user.id).one_or_none()
                    if not pref:
                        pref = Preference(user_id=user.id)
                        session.add(pref)
                    pref.keywords = p.get('preferred_jobs') or []
                    pref.location = p.get('location') or ''
                    pref.contract_types = p.get('contract_types') or []
                    pref.min_match_score = int(p.get('min_match_score') or 70)
                    pref.notify_via_email = bool(p.get('notify_via_email', True))

        # Import job offers
        jobs_file = DATA / 'job_offers.json'
        if jobs_file.exists():
            try:
                jobs = json.loads(jobs_file.read_text(encoding='utf-8'))
            except Exception:
                jobs = []
            for j in jobs or []:
                url = j.get('url') or ''
                if not url:
                    continue
                exists = session.query(JobOffer).filter_by(url=url).one_or_none()
                if exists:
                    continue
                offer = JobOffer(
                    title=j.get('title',''),
                    company=j.get('company',''),
                    description=j.get('description','')[:3900],
                    url=url,
                    source=j.get('source',''),
                    created=j.get('created',''),
                    requirements=j.get('requirements') or {},
                    extracted_skills=j.get('skills') or [],
                )
                session.add(offer)

        # Import notification history (optional)
        notif_file = DATA / 'notification_history.json'
        if notif_file.exists():
            try:
                notif_list = json.loads(notif_file.read_text(encoding='utf-8'))
            except Exception:
                notif_list = []
            for n in notif_list or []:
                name = n.get('recipient_name') or 'Utilisateur'
                email = n.get('recipient_email')
                status = n.get('status', 'success')
                ts = n.get('timestamp')
                # Resolve or create user
                user = None
                if email:
                    user = session.query(User).filter_by(email=email).one_or_none()
                if not user:
                    user = session.query(User).filter_by(name=name).one_or_none()
                if not user:
                    user = User(name=name, email=email)
                    session.add(user)
                    session.flush()
                # Create one row per job (approx), else single row
                count = int(n.get('job_count') or 1)
                when = None
                try:
                    from datetime import datetime
                    when = datetime.fromisoformat(ts) if ts else None
                except Exception:
                    when = None
                for _ in range(max(1, count)):
                    notif = Notification(user_id=user.id, status=status)
                    if when:
                        notif.sent_at = when
                    session.add(notif)

        session.commit()
        print('DB import completed')
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    init_db()
    import_from_json()
