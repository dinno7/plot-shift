import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


# FIXME:
def ensure_nltk_data(*resources: str):
    """Download NLTK data only if it doesn't already exist."""
    for resource in resources:
        try:
            nltk.data.find(resource)
        except LookupError:
            print("Here")
            resource_name = resource.split("/")[-1]
            nltk.download(resource_name)


ensure_nltk_data("corpora/stopwords")
stop_words = set(stopwords.words("english"))


def tokenize_all_words(sentence: str) -> list[str]:
    """Alphabetic tokens, including stopwords. Used for N-word windows."""
    ensure_nltk_data("tokenizers/punkt", "tokenizers/punkt_tab")
    return [w.lower() for w in word_tokenize(sentence) if w.isalpha()]


def sentence_to_word(sentence: str) -> list[str]:
    """Stopword-dropped alphabetic tokens. Used for dictionary scoring."""
    return [w for w in tokenize_all_words(sentence) if w not in stop_words]
