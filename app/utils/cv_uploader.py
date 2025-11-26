import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire src au path pour importer les modules
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from agents.cv_analyzer import CVAnalyzer

# Optional DB imports
try:
    from db.session import get_session
    from db.models import User, CV as CVModel
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False
from utils.guards import safe_extract_pdf_text

DATA_DIR = BASE_DIR / "src" / "data"

def save_and_analyze_cv(uploaded_file, user_name: str, user_email: str):
    """
    Sauvegarde un CV uploadé et l'analyse
    Retourne (success: bool, message: str, skills: list, final_name: str, final_email: str)
    final_name est le nom extrait du CV si détecté, sinon user_name.
    final_email est l'email extrait du CV si détecté, sinon user_email.
    """
    try:
        # Créer le dossier data s'il n'existe pas
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Sauvegarder d'abord vers un fichier temporaire
        tmp_filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        tmp_path = DATA_DIR / tmp_filename
        
        with open(tmp_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Charger les données existantes pour initialiser CVAnalyzer
        cv_data_path = DATA_DIR / "cv_data.json"
        if cv_data_path.exists():
            with open(cv_data_path, 'r', encoding='utf-8') as f:
                existing_cv_data = json.load(f)
        else:
            existing_cv_data = []
        
        # Créer une entrée temporaire pour l'analyse
        temp_cv_entry = {
            'name': user_name,
            'email': user_email,
            'path': str(tmp_path)
        }
        
        # Analyser le CV avec CVAnalyzer
        analyzer = CVAnalyzer([temp_cv_entry])
        analyzer.analyze_cvs()  # Cette méthode ajoute 'analysis' à temp_cv_entry
        
        # Vérifier que l'analyse a réussi
        if 'analysis' not in temp_cv_entry or 'skills' not in temp_cv_entry['analysis']:
            return False, "Impossible d'analyser le CV", []
        
        analysis = temp_cv_entry['analysis']

        # Tenter d'extraire le nom depuis l'analyse (PERSON)
        def _extract_name_from_analysis(analysis_dict):
            try:
                persons = [e.get('entity','').strip() for e in analysis_dict.get('experiences', []) if e.get('label') == 'PERSON']
                # Filtrer des candidats plausibles (2-4 mots alphabétiques)
                for p in persons:
                    text = ' '.join(p.split())
                    parts = [w for w in text.split(' ') if w and (w.isalpha() or w.replace('-', '').isalpha())]
                    if 2 <= len(parts) <= 4:
                        return text.title() if text.isupper() else text
                # fallback: premier PERSON brut
                if persons:
                    cand = persons[0]
                    return cand.title() if cand.isupper() else cand
            except Exception:
                pass
            return None

        extracted_name = _extract_name_from_analysis(analysis) or user_name

        # Déterminer le nom de fichier final: "cv - <Nom>.pdf"
        def _sanitize_filename_part(s: str) -> str:
            s = s.strip()
            # Remplacer les barres et caractères interdits
            keep = "-_. ()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            s = ''.join(ch if ch in keep else ' ' for ch in s)
            # Réduire les espaces multiples
            s = ' '.join(s.split())
            return s

        safe_name = _sanitize_filename_part(extracted_name)
        final_filename = f"cv - {safe_name}.pdf"
        final_path = DATA_DIR / final_filename

        # Remplacer si existe déjà (on garde un seul CV par nom)
        try:
            os.replace(tmp_path, final_path)
        except Exception:
            # Si remplacement échoue, ajouter timestamp pour éviter collision
            final_filename = f"cv - {safe_name} {datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            final_path = DATA_DIR / final_filename
            os.replace(tmp_path, final_path)

        # Extraire email depuis le PDF
        def _extract_email_from_pdf(pdf_path: Path) -> str:
            try:
                text = safe_extract_pdf_text(str(pdf_path), fallback_text="")
                if not text:
                    return None
                # Chercher les emails plausibles
                emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
                if not emails:
                    return None
                # Heuristique: privilégier les domaines courants d'email perso
                preferred = [e for e in emails if any(d in e.lower() for d in ["gmail.com","outlook.com","hotmail.com","yahoo.","icloud.com"]) ]
                return (preferred[0] if preferred else emails[0]).strip()
            except Exception:
                return None

        extracted_email = _extract_email_from_pdf(final_path) or user_email
        
        # Mettre à jour en DB si disponible, sinon cv_data.json
        cv_data_path = DATA_DIR / "cv_data.json"
        if DB_AVAILABLE:
            session = get_session()
            try:
                # Upsert user
                user = None
                if extracted_email:
                    user = session.query(User).filter_by(email=extracted_email).one_or_none()
                if not user:
                    user = session.query(User).filter_by(name=extracted_name).one_or_none()
                if not user:
                    user = User(name=extracted_name, email=extracted_email)
                    session.add(user)
                    session.flush()

                # Upsert CV (latest only)
                cv_row = (
                    session.query(CVModel)
                    .filter(CVModel.user_id == user.id)
                    .order_by(CVModel.created_at.desc())
                    .first()
                )
                if not cv_row:
                    cv_row = CVModel(user_id=user.id, file_path=str(final_path.relative_to(BASE_DIR)), analysis=analysis)
                    session.add(cv_row)
                else:
                    cv_row.file_path = str(final_path.relative_to(BASE_DIR))
                    cv_row.analysis = analysis

                session.commit()
            except Exception:
                session.rollback()
                # Fallback to JSON if DB write failed
                _write_json_fallback = True
            finally:
                session.close()
        else:
            _write_json_fallback = True

        if '_write_json_fallback' in locals() and _write_json_fallback:
            # Charger les données existantes
            if cv_data_path.exists():
                with open(cv_data_path, 'r', encoding='utf-8') as f:
                    cv_data = json.load(f)
            else:
                cv_data = []
            # Chercher si l'utilisateur existe déjà
            user_found = False
            for i, user in enumerate(cv_data):
                if user.get('name') == user_name or user.get('name') == extracted_name:
                    # Mettre à jour
                    cv_data[i] = {
                        "name": extracted_name,
                        "path": str(final_path.relative_to(BASE_DIR)),
                        "email": extracted_email,
                        "analysis": analysis,
                        "updated_at": datetime.now().isoformat()
                    }
                    user_found = True
                    break
            # Si l'utilisateur n'existe pas, l'ajouter
            if not user_found:
                cv_data.append({
                    "name": extracted_name,
                    "path": str(final_path.relative_to(BASE_DIR)),
                    "email": extracted_email,
                    "analysis": analysis,
                    "created_at": datetime.now().isoformat()
                })
            # Sauvegarder
            with open(cv_data_path, 'w', encoding='utf-8') as f:
                json.dump(cv_data, f, indent=2, ensure_ascii=False)
        
        skills = analysis.get('skills', [])
        return True, f"CV analysé avec succès ! {len(skills)} compétences détectées.", skills, extracted_name, extracted_email
        
    except Exception as e:
        return False, f"Erreur lors de l'analyse du CV : {str(e)}", [], user_name, user_email
