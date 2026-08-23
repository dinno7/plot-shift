import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download("stopwords")

stop_words = set(stopwords.words("english"))


def sentence_to_word(sentence: str) -> list[str]:
    tokenized_words = [w for w in word_tokenize(sentence) if w.isalpha() and w not in stop_words]
    return tokenized_words
