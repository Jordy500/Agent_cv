import os
import spacy


def get_spacy_model():
    """Charge et renvoie l'objet spaCy (cache simple via module).
    Le nom du modèle est lu depuis la variable d'environnement SPACY_MODEL
    ou utilise la valeur par défaut 'fr_core_news_sm'.
    """
    model_name = os.environ.get('SPACY_MODEL', 'fr_core_news_sm')
    try:
        nlp = spacy.load(model_name)
    except OSError:
        # Le modèle n'est pas installé — remonter l'erreur claire
        raise RuntimeError(f"spaCy model '{model_name}' not found. Install it with: python -m spacy download {model_name}")
    return nlp


def preprocess_text(text, nlp=None):
    """Prétraite `text` en utilisant un pipeline spaCy.

    Args:
        text (str): texte brut
        nlp (spacy.Language|None): objet spaCy (optionnel). Si None, la fonction charge le modèle par défaut.

    Returns:
        spacy.tokens.Doc: document spaCy tokenisé et analysé
    """
    if nlp is None:
        nlp = get_spacy_model()
    return nlp(text)