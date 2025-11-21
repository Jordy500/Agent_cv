import os
import spacy


def get_spacy_model():
    model_name = os.environ.get('SPACY_MODEL', 'fr_core_news_sm')
    try:
        nlp = spacy.load(model_name)
    except OSError:
        # Le modèle n'est pas installé — remonter l'erreur claire
        raise RuntimeError(f"spaCy model '{model_name}' not found. Install it with: python -m spacy download {model_name}")
    return nlp


def preprocess_text(text, nlp=None):
    if nlp is None:
        nlp = get_spacy_model()
    return nlp(text)