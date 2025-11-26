import json
from pathlib import Path
from datetime import datetime

# Optional DB (fallback to JSON)
try:
    from db.session import get_session
    from db.models import User, Notification
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent.parent
NOTIFICATION_LOG_FILE = BASE_DIR / "src" / "data" / "notification_history.json"


def log_notification(recipient_email: str, recipient_name: str, job_count: int, status: str = "success"):
    """
    Enregistre une notification dans la DB si disponible, sinon JSON.
    """
    if DB_AVAILABLE:
        session = get_session()
        try:
            # Trouver ou créer l'utilisateur
            user = None
            if recipient_email:
                user = session.query(User).filter_by(email=recipient_email).one_or_none()
            if not user and recipient_name:
                user = session.query(User).filter_by(name=recipient_name).one_or_none()
            if not user:
                user = User(name=recipient_name or "Utilisateur", email=recipient_email or None)
                session.add(user)
                session.flush()

            # Enregistrer N entrées si job_count > 1 pour rester simple
            count = max(1, int(job_count or 1))
            now = datetime.utcnow()
            for _ in range(count):
                n = Notification(user_id=user.id, sent_at=now, status=status)
                session.add(n)
            session.commit()
            return
        except Exception:
            session.rollback()
        finally:
            try:
                session.close()
            except Exception:
                pass

    # Fallback JSON
    NOTIFICATION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if NOTIFICATION_LOG_FILE.exists():
        try:
            with open(NOTIFICATION_LOG_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = []

    notification = {
        "timestamp": datetime.now().isoformat(),
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "job_count": job_count,
        "status": status
    }
    history.append(notification)
    history = history[-50:]
    with open(NOTIFICATION_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_notification_history(user_email: str = None, limit: int = 10):
    """
    Récupère l'historique (DB prioritaire). Retourne des dicts: timestamp, recipient_email, recipient_name, status.
    """
    if DB_AVAILABLE:
        session = get_session()
        try:
            q = session.query(Notification, User).join(User, Notification.user_id == User.id)
            if user_email:
                q = q.filter(User.email == user_email)
            rows = q.order_by(Notification.sent_at.desc()).limit(limit).all()
            result = []
            for n, u in rows:
                result.append({
                    "timestamp": (getattr(n, 'sent_at', None) or datetime.utcnow()).isoformat(),
                    "recipient_email": u.email,
                    "recipient_name": u.name,
                    "job_count": 1,
                    "status": n.status,
                })
            return result
        except Exception:
            pass
        finally:
            try:
                session.close()
            except Exception:
                pass

    # Fallback JSON
    if not NOTIFICATION_LOG_FILE.exists():
        return []
    try:
        with open(NOTIFICATION_LOG_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception:
        return []
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    if user_email:
        history = [n for n in history if n.get('recipient_email') == user_email]
    return history[:limit]


def get_notification_stats(user_email: str = None):
    """
    Statistiques de notifications (DB prioritaire).
    """
    if DB_AVAILABLE:
        session = get_session()
        try:
            q = session.query(Notification, User).join(User, Notification.user_id == User.id)
            if user_email:
                q = q.filter(User.email == user_email)
            rows = q.all()
            if not rows:
                return {"total_sent": 0, "total_jobs": 0, "last_notification": None}
            total_sent = len(rows)
            last_ts = max((getattr(n, 'sent_at', None) for n, _ in rows if getattr(n, 'sent_at', None)), default=None)
            return {
                "total_sent": total_sent,
                "total_jobs": total_sent,  # on compte 1/notification
                "last_notification": last_ts.isoformat() if last_ts else None,
            }
        except Exception:
            pass
        finally:
            try:
                session.close()
            except Exception:
                pass

    # Fallback JSON
    if not NOTIFICATION_LOG_FILE.exists():
        return {"total_sent": 0, "total_jobs": 0, "last_notification": None}
    try:
        with open(NOTIFICATION_LOG_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception:
        return {"total_sent": 0, "total_jobs": 0, "last_notification": None}
    if user_email:
        history = [n for n in history if n.get('recipient_email') == user_email]
    if not history:
        return {"total_sent": 0, "total_jobs": 0, "last_notification": None}
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return {
        "total_sent": len(history),
        "total_jobs": sum(n.get('job_count', 0) for n in history),
        "last_notification": history[0].get('timestamp'),
    }
