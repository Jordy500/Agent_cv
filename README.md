# Agent_cv

Petit projet d'agents pour analyser des CV, comparer des offres, générer des lettres de motivation et envoyer des notifications par email.

Important — sécurité
- Ne commitez jamais de clés API ou secrets dans le dépôt. Utilisez un fichier `.env` (ignoré) ou des variables d'environnement.

Installation (Windows, PowerShell)

1. Créez et activez un environnement virtuel (si ce n'est pas déjà fait) :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Installer les dépendances :

```powershell
pip install -r requirements.txt
```

3. Créez un fichier `.env` à partir de `.env.example` et remplissez vos clés :

```powershell
copy .env.example .env
# puis éditez .env avec vos vraies valeurs (ne pas committer)
```

4. Installer un modèle spaCy (exemple français) :

```powershell
python -m spacy download fr_core_news_sm
```

Exécution

```powershell
python src\main.py
```

Ce que j'ai modifié pour la sécurité et la reproductibilité
- `src/key_api.py` : retiré les secrets du fichier et conservé uniquement des valeurs non secrètes (noms de modèles).
- Ajout de `.env.example` : liste des variables d'environnement attendues.
- `requirements.txt` rempli avec dépendances détectées.
- `src/main.py` : lecture des configurations depuis les variables d'environnement (via `python-dotenv` si `.env` présent).
- `src/utils/text_processing.py` : correction pour charger le modèle spaCy depuis l'environnement.
- `src/utils/email_sender.py` : utilise maintenant SMTP ou SendGrid en lisant les clés depuis les variables d'environnement.

Prochaines étapes recommandées
- Révoquer/rotater toute clé exposée précédemment (si vous l'avez commitée quelque part public).
- Compléter les agents manquants (`job_offer_analyzer`, `motivation_letter_generator`, `notification_agent`).
- Ajouter des tests unitaires et CI.

Si vous voulez, je peux :
- retirer l'ancienne `key_api.py` du suivi Git (git rm --cached) et committer la suppression; ou
- implémenter une des fonctionnalités manquantes (par ex. comparaison simple d'offres) et ajouter des tests.

# Agent_cv