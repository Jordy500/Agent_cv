import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Chemin vers le script run_once_notify.py
BASE_DIR = Path(__file__).parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
VENV_PYTHON = BASE_DIR / "IA_agent" / "bin" / "python3"

def run_job_scan():
    """
    Lance le scan des offres d'emploi en exécutant run_once_notify.py
    Retourne True si succès, False sinon
    """
    try:
        script_path = SCRIPTS_DIR / "run_once_notify.py"
        
        if not script_path.exists():
            return False, "Script run_once_notify.py introuvable"
        
        # Exécuter le script avec le Python de l'environnement virtuel
        result = subprocess.run(
            [str(VENV_PYTHON), str(script_path)],
            capture_output=True,
            text=True,
            timeout=120  # Timeout de 2 minutes
        )
        
        if result.returncode == 0:
            return True, f"Scan terminé avec succès ! Vérifiez vos emails."
        else:
            # Récupérer les dernières lignes d'erreur
            error_lines = result.stderr.split('\n')[-5:] if result.stderr else []
            error_msg = '\n'.join(error_lines)
            return False, f"Erreur lors du scan : {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, "Le scan a pris trop de temps (timeout de 2 minutes)"
    except Exception as e:
        return False, f"Erreur inattendue : {str(e)}"

def get_scan_status():
    """
    Vérifie si un scan est en cours
    """
    # Cette fonction pourrait vérifier l'existence d'un fichier de lock
    # Pour l'instant, on retourne toujours False
    return False
