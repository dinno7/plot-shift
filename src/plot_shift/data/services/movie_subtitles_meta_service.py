import re
import string
from datetime import timedelta

import nltk
from nltk.tokenize import sent_tokenize
from unidecode import unidecode

from plot_shift.data.models import MovieSubtitlesMeta, Subtitle
from plot_shift.data.utils import sentence_to_word

# Download required data (run once)
nltk.download("punkt")
nltk.download("punkt_tab")


class MovieSubtitlesMetaService:
    imdb_id: int

    _text: str = ""
    _duration = timedelta()

    def __init__(self, imdb_id: int) -> None:
        self.imdb_id = imdb_id

    def add(self, sub: Subtitle) -> None:
        if sub.imdb_id_int != self.imdb_id:
            raise ValueError("Invalid imdb id for subtitle part")
        self._text += " " + sub.text_raw
        self._duration += sub.duration

    def process(self) -> MovieSubtitlesMeta:
        """Remove common SRT artifacts from subtitle text."""
        cleaned = self._text.lower()
        # Remove HTML-like tags (<i>, <b>, <font color="...">, etc.)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        # Normalize unicode: é→e, ñ→n, etc.
        cleaned = unidecode(cleaned)
        # Remove ASS/SSA override tags ({\an8}, {\c&H00FFFF&}, etc.)
        cleaned = re.sub(r"\{[^}]*\}", "", cleaned)
        # Remove hearing-impaired descriptors in brackets [LAUGHTER], (SIGHING)
        cleaned = re.sub(r"[\[(][^)\]]*[\])]", "", cleaned)
        # Collapse multiple spaces/newlines into single space and dash(-)
        cleaned = re.sub(r"[\n]", " ", cleaned)  # new line
        # Quotes
        cleaned = re.sub(r"['\"](\w+)['\"]", r"\1", cleaned)
        # Remove repeated marks
        cleaned = re.sub(r"-", " ", cleaned)  # dash
        cleaned = re.sub(r"\.+", ".", cleaned)  # dots
        cleaned = re.sub(r"\?+", "?", cleaned)  # question marks
        cleaned = re.sub(r"!+", "!", cleaned)  # exclamation marks
        cleaned = re.sub(r"\s+", " ", cleaned)  # whitespace
        cleaned = re.sub(r"\|\-+", " ", cleaned)  # Speaker change marker |--

        # Clean sentences and extract words
        tokenized_sentences = sent_tokenize(cleaned)

        sentences: list[str] = []
        words: list[str] = []
        for sentence in tokenized_sentences:
            sentence = sentence.lstrip(string.punctuation)
            sentences.append(sentence)
            words.extend(sentence_to_word(sentence))
        return MovieSubtitlesMeta(
            imdb_id=self.imdb_id,
            words=words,
            sentences=sentences,
            duration=self._duration,
        )
