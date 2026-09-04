"""NRC-VAD intensity scorer.

Same idea as VADER's ``polarity_scores``: look up words in a lexicon, apply a
small set of intensity rules, then report ``neg`` / ``neu`` / ``pos`` /
``compound``. The difference is the lexicon. NRC-VAD scores three dimensions
(valence, arousal, dominance), each on a -1 to +1 scale, so this scorer returns
that four-way breakdown once per dimension.

Rules kept from VADER (the ones that are easy to explain):

* negation in the previous three tokens ("not good", "isn't very funny")
* degree modifiers in the previous three tokens ("very", "kind of")
* contrastive "but" (text after "but" counts more than text before it)

Special-case idioms, emoji rewriting, ALL-CAPS, and punctuation amplifiers are
intentionally omitted.
"""

import csv
import math
import string
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple, TypedDict

_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_LEXICON = _THIS_DIR / "unigrams-NRC-VAD-Lexicon-v2.1.txt"

# Multiplicative intensity changes. VADER used additive constants on a
# roughly ±4 lexicon; NRC-VAD is already ±1, so a factor is simpler and
# scale-independent.
BOOSTER_FACTOR = 1.3
DAMPENER_FACTOR = 0.7
NEGATION_SCALAR = -0.74

# Farther modifiers have slightly less effect (same 1 / 2 / 3 token window
# as VADER).
_BOOSTER_DECAY = (1.0, 0.95, 0.9)

# ``score / sqrt(score^2 + alpha)`` maps an unbounded sum into (-1, 1).
# Alpha is smaller than VADER's 15 because NRC-VAD values are ~4x smaller.
NORMALIZE_ALPHA = 1.0

NEGATIONS = frozenset(
    [
        "aint",
        "arent",
        "cannot",
        "cant",
        "couldnt",
        "darent",
        "didnt",
        "doesnt",
        "ain't",
        "aren't",
        "can't",
        "couldn't",
        "daren't",
        "didn't",
        "doesn't",
        "dont",
        "hadnt",
        "hasnt",
        "havent",
        "isnt",
        "mightnt",
        "mustnt",
        "neither",
        "don't",
        "hadn't",
        "hasn't",
        "haven't",
        "isn't",
        "mightn't",
        "mustn't",
        "neednt",
        "needn't",
        "never",
        "none",
        "nope",
        "nor",
        "not",
        "nothing",
        "nowhere",
        "oughtnt",
        "shant",
        "shouldnt",
        "uhuh",
        "wasnt",
        "werent",
        "oughtn't",
        "shan't",
        "shouldn't",
        "uh-uh",
        "wasn't",
        "weren't",
        "without",
        "wont",
        "wouldnt",
        "won't",
        "wouldn't",
        "rarely",
        "seldom",
        "despite",
        "no",
    ]
)

BOOSTERS: dict[str, float] = {
    "absolutely": BOOSTER_FACTOR,
    "amazingly": BOOSTER_FACTOR,
    "awfully": BOOSTER_FACTOR,
    "completely": BOOSTER_FACTOR,
    "considerable": BOOSTER_FACTOR,
    "considerably": BOOSTER_FACTOR,
    "decidedly": BOOSTER_FACTOR,
    "deeply": BOOSTER_FACTOR,
    "effing": BOOSTER_FACTOR,
    "enormous": BOOSTER_FACTOR,
    "enormously": BOOSTER_FACTOR,
    "entirely": BOOSTER_FACTOR,
    "especially": BOOSTER_FACTOR,
    "exceptional": BOOSTER_FACTOR,
    "exceptionally": BOOSTER_FACTOR,
    "extreme": BOOSTER_FACTOR,
    "extremely": BOOSTER_FACTOR,
    "fabulously": BOOSTER_FACTOR,
    "flipping": BOOSTER_FACTOR,
    "flippin": BOOSTER_FACTOR,
    "frackin": BOOSTER_FACTOR,
    "fracking": BOOSTER_FACTOR,
    "fricking": BOOSTER_FACTOR,
    "frickin": BOOSTER_FACTOR,
    "frigging": BOOSTER_FACTOR,
    "friggin": BOOSTER_FACTOR,
    "fully": BOOSTER_FACTOR,
    "fuckin": BOOSTER_FACTOR,
    "fucking": BOOSTER_FACTOR,
    "fuggin": BOOSTER_FACTOR,
    "fugging": BOOSTER_FACTOR,
    "greatly": BOOSTER_FACTOR,
    "hella": BOOSTER_FACTOR,
    "highly": BOOSTER_FACTOR,
    "hugely": BOOSTER_FACTOR,
    "incredible": BOOSTER_FACTOR,
    "incredibly": BOOSTER_FACTOR,
    "intensely": BOOSTER_FACTOR,
    "major": BOOSTER_FACTOR,
    "majorly": BOOSTER_FACTOR,
    "more": BOOSTER_FACTOR,
    "most": BOOSTER_FACTOR,
    "particularly": BOOSTER_FACTOR,
    "purely": BOOSTER_FACTOR,
    "quite": BOOSTER_FACTOR,
    "really": BOOSTER_FACTOR,
    "remarkably": BOOSTER_FACTOR,
    "so": BOOSTER_FACTOR,
    "substantially": BOOSTER_FACTOR,
    "thoroughly": BOOSTER_FACTOR,
    "total": BOOSTER_FACTOR,
    "totally": BOOSTER_FACTOR,
    "tremendous": BOOSTER_FACTOR,
    "tremendously": BOOSTER_FACTOR,
    "uber": BOOSTER_FACTOR,
    "unbelievably": BOOSTER_FACTOR,
    "unusually": BOOSTER_FACTOR,
    "utter": BOOSTER_FACTOR,
    "utterly": BOOSTER_FACTOR,
    "very": BOOSTER_FACTOR,
    "almost": DAMPENER_FACTOR,
    "barely": DAMPENER_FACTOR,
    "hardly": DAMPENER_FACTOR,
    "kinda": DAMPENER_FACTOR,
    "kindof": DAMPENER_FACTOR,
    "kind-of": DAMPENER_FACTOR,
    "less": DAMPENER_FACTOR,
    "little": DAMPENER_FACTOR,
    "marginal": DAMPENER_FACTOR,
    "marginally": DAMPENER_FACTOR,
    "occasional": DAMPENER_FACTOR,
    "occasionally": DAMPENER_FACTOR,
    "partly": DAMPENER_FACTOR,
    "scarce": DAMPENER_FACTOR,
    "scarcely": DAMPENER_FACTOR,
    "slight": DAMPENER_FACTOR,
    "slightly": DAMPENER_FACTOR,
    "somewhat": DAMPENER_FACTOR,
    "sorta": DAMPENER_FACTOR,
    "sortof": DAMPENER_FACTOR,
    "sort-of": DAMPENER_FACTOR,
}

# Two-word dampeners. Matched against (previous token, current preceding token).
BIGRAM_BOOSTERS: dict[tuple[str, str], float] = {
    ("kind", "of"): DAMPENER_FACTOR,
    ("sort", "of"): DAMPENER_FACTOR,
    ("just", "enough"): DAMPENER_FACTOR,
}


class PolarityScores(TypedDict):
    neg: float
    neu: float
    pos: float
    compound: float


class VADPolarityScores(TypedDict):
    valence: PolarityScores
    arousal: PolarityScores
    dominance: PolarityScores


class VADVector(NamedTuple):
    valence: float
    arousal: float
    dominance: float

    def __mul__(self, scalar: float) -> VADVector:
        return VADVector(self.valence * scalar, self.arousal * scalar, self.dominance * scalar)


_ZERO = VADVector(0.0, 0.0, 0.0)


def tokenize(text: str) -> list[str]:
    """Split on whitespace and strip wrapping punctuation, keeping short tokens.

    Short tokens are left as-is so things like ``:)`` are not erased. Matches
    VADER's tokenizer closely, then lowercases for lexicon lookup.
    """
    tokens: list[str] = []
    for raw in text.split():
        stripped = raw.strip(string.punctuation)
        token = raw if len(stripped) <= 2 else stripped
        tokens.append(token.lower())
    return tokens


def is_negation(token: str) -> bool:
    return token in NEGATIONS or "n't" in token


def is_modifier(token: str) -> bool:
    return token in BOOSTERS or is_negation(token)


def booster_factor(tokens: Sequence[str], index: int) -> float | None:
    """Booster/dampener factor for the token at ``index``, if it is one."""
    token = tokens[index]
    if token in BOOSTERS:
        return BOOSTERS[token]
    if index > 0:
        bigram = (tokens[index - 1], token)
        if bigram in BIGRAM_BOOSTERS:
            return BIGRAM_BOOSTERS[bigram]
    return None


def context_multiplier(tokens: Sequence[str], index: int) -> float:
    """Combine negation and degree modifiers from the previous three tokens."""
    factor = 1.0
    for distance in (1, 2, 3):
        prev = index - distance
        if prev < 0:
            break
        booster = booster_factor(tokens, prev)
        if booster is not None:
            decay = _BOOSTER_DECAY[distance - 1]
            factor *= 1.0 + (booster - 1.0) * decay
        if is_negation(tokens[prev]):
            factor *= NEGATION_SCALAR
    return factor


def apply_but_contrast(tokens: Sequence[str], scores: list[float]) -> list[float]:
    """Halve scores before ``but`` and boost scores after it."""
    try:
        but_at = tokens.index("but")
    except ValueError:
        return scores
    adjusted: list[float] = []
    for i, score in enumerate(scores):
        if i < but_at:
            adjusted.append(score * 0.5)
        elif i > but_at:
            adjusted.append(score * 1.5)
        else:
            adjusted.append(score)
    return adjusted


def normalize(score: float, alpha: float = NORMALIZE_ALPHA) -> float:
    """Map a raw sum into (-1, 1). Same formula VADER uses."""
    norm = score / math.sqrt(score * score + alpha)
    return max(-1.0, min(1.0, norm))


def sift_scores(scores: Sequence[float]) -> tuple[float, float, int]:
    """Split word scores into a positive sum, negative sum, and neutral count.

    The ±1 shift is VADER's way of giving each polar word a base weight so that
    ``pos`` / ``neg`` / ``neu`` are proportions of the text, not just sums of
    intensity.
    """
    pos_sum = 0.0
    neg_sum = 0.0
    neu_count = 0
    for score in scores:
        if score > 0:
            pos_sum += score + 1.0
        elif score < 0:
            neg_sum += score - 1.0
        else:
            neu_count += 1
    return pos_sum, neg_sum, neu_count


def polarity_from_scores(scores: Sequence[float]) -> PolarityScores:
    if not scores:
        return {"neg": 0.0, "neu": 0.0, "pos": 0.0, "compound": 0.0}

    compound = normalize(sum(scores))
    pos_sum, neg_sum, neu_count = sift_scores(scores)
    total = pos_sum + abs(neg_sum) + neu_count
    if total == 0:
        return {"neg": 0.0, "neu": 0.0, "pos": 0.0, "compound": round(compound, 4)}

    return {
        "neg": round(abs(neg_sum / total), 3),
        "neu": round(abs(neu_count / total), 3),
        "pos": round(abs(pos_sum / total), 3),
        "compound": round(compound, 4),
    }


def load_lexicon(path: Path) -> dict[str, VADVector]:
    lexicon: dict[str, VADVector] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            term = row["term"].lower()
            lexicon[term] = VADVector(
                valence=float(row["valence"]),
                arousal=float(row["arousal"]),
                dominance=float(row["dominance"]),
            )
    return lexicon


class VADIntensityAnalyzer:
    """Give valence, arousal, and dominance intensity scores to a sentence."""

    def __init__(self, lexicon_file: str | Path | None = None) -> None:
        path = Path(lexicon_file) if lexicon_file is not None else _DEFAULT_LEXICON
        self.lexicon = load_lexicon(path)

    def polarity_scores(self, text: str) -> VADPolarityScores:
        """Return ``neg`` / ``neu`` / ``pos`` / ``compound`` for each VAD dimension.

        Example::

            {
                "valence":   {"neg": 0.0, "neu": 0.4, "pos": 0.6, "compound": 0.72},
                "arousal":   {"neg": 0.1, "neu": 0.7, "pos": 0.2, "compound": 0.11},
                "dominance": {"neg": 0.0, "neu": 0.5, "pos": 0.5, "compound": 0.40},
            }
        """
        tokens = tokenize(text)
        valence: list[float] = []
        arousal: list[float] = []
        dominance: list[float] = []

        for i, token in enumerate(tokens):
            vector = self._score_token(tokens, i, token)
            valence.append(vector.valence)
            arousal.append(vector.arousal)
            dominance.append(vector.dominance)

        return {
            "valence": polarity_from_scores(apply_but_contrast(tokens, valence)),
            "arousal": polarity_from_scores(apply_but_contrast(tokens, arousal)),
            "dominance": polarity_from_scores(apply_but_contrast(tokens, dominance)),
        }

    def _score_token(self, tokens: Sequence[str], index: int, token: str) -> VADVector:
        if is_modifier(token):
            return _ZERO
        if _is_bigram_booster_prefix(tokens, index):
            return _ZERO
        entry = self.lexicon.get(token)
        if entry is None:
            return _ZERO
        return entry * context_multiplier(tokens, index)


def _is_bigram_booster_prefix(tokens: Sequence[str], index: int) -> bool:
    if index + 1 >= len(tokens):
        return False
    return (tokens[index], tokens[index + 1]) in BIGRAM_BOOSTERS


if __name__ == "__main__":
    sentences = [
        "VADER is smart, handsome, and funny.",
        "VADER is very smart, handsome, and funny.",
        "VADER is not smart, handsome, nor funny.",
        "The book was good.",
        "The book was only kind of good.",
        "The plot was good, but the characters are uncompelling and the dialog is not great.",
        "I love this.",
        "I hate this.",
    ]
    analyzer = VADIntensityAnalyzer()
    for sentence in sentences:
        scores = analyzer.polarity_scores(sentence)
        print(f"{sentence}")
        for dimension in ("valence", "arousal", "dominance"):
            print(f"  {dimension:10} {scores[dimension]}")
        print()
