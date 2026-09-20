import re
import string

import nltk
from nltk.tokenize import sent_tokenize
from unidecode import unidecode

from plot_shift.data.models import MovieSubtitle
from plot_shift.data.models.subtitle_segment import SubtitleSegment
from plot_shift.data.utils import sentence_to_word

# Download required data (run once)
nltk.download("punkt")
nltk.download("punkt_tab")


def clean_subtitle_segment_content(text: str) -> str:
    """Remove common SRT artifacts from a single subtitle segment's text."""
    cleaned = text.lower()
    # Remove HTML-like tags (<i>, <b>, <font color="...">, etc.)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Normalize unicode: é→e, ñ→n, etc.
    cleaned = unidecode(cleaned)
    # Remove ASS/SSA override tags ({\an8}, {\c&H00FFFF&}, etc.)
    cleaned = re.sub(r"\{[^}]*\}", "", cleaned)
    # Remove hearing-impaired descriptors in brackets [LAUGHTER], (SIGHING)
    cleaned = re.sub(r"[\[(][^)\]]*[\])]", "", cleaned)
    # Collapse newlines into a single space
    cleaned = re.sub(r"[\n]", " ", cleaned)
    # Quotes
    cleaned = re.sub(r"['\"](\w+)['\"]", r"\1", cleaned)
    # Remove repeated marks
    cleaned = re.sub(r"-", " ", cleaned)  # dash
    cleaned = re.sub(r"\.+", ".", cleaned)  # dots
    cleaned = re.sub(r"\?+", "?", cleaned)  # question marks
    cleaned = re.sub(r"!+", "!", cleaned)  # exclamation marks
    cleaned = re.sub(r"\s+", " ", cleaned)  # whitespace
    cleaned = re.sub(r"\|\-+", " ", cleaned)  # Speaker change marker |--
    return cleaned.strip()


class MovieSubtitlesService:
    """Cleans and segments subtitle cues, keeping each cue's timestamps.

    A cue is cleaned and sentence-tokenized on its own (never joined with
    other cues first), so every resulting segment can inherit its owning
    cue's start/end. A cue is almost always a single sentence, so sharing
    one timestamp across a cue's rare multi-sentence split is a fine-grained
    enough approximation for window-based (real screen-time) analysis.
    """

    imdb_id: int

    def __init__(self, imdb_id: int) -> None:
        self.imdb_id = imdb_id
        self._segments: list[SubtitleSegment] = []

    def add(self, sub: SubtitleSegment) -> None:
        if sub.imdb_id_int != self.imdb_id:
            raise ValueError("Invalid imdb id for subtitle part")
        self._segments.append(sub)

    def process(self) -> MovieSubtitle:
        segments: list[SubtitleSegment] = []
        words: list[str] = []
        segment_idx = 0

        for segment in self._segments:
            cleaned = clean_subtitle_segment_content(segment.content)
            if not cleaned:
                continue
            for sentence in sent_tokenize(cleaned):
                sentence = sentence.lstrip(string.punctuation).strip()
                if not sentence:
                    continue
                segments.append(
                    SubtitleSegment(
                        imdb_id_int=self.imdb_id,
                        segment_idx=segment_idx,
                        start=segment.start,
                        end=segment.end,
                        content=sentence,
                    )
                )
                words.extend(sentence_to_word(sentence))
                segment_idx += 1

        return MovieSubtitle(imdb_id=self.imdb_id, words=words, _segments=segments)
