"""Fixed maps from a model's training scale onto [-1, 1].

These are properties of the annotation scale, not of a sample. A min and max
taken from one corpus would move whenever a film is added, and fitting them
per film would stretch a flat film to the same width as a film with a real swing.
"""


def emobank_to_bipolar(value: float) -> float:
    """Map an EmoBank rating from the 1–5 scale onto [-1, 1].

    EmoBank (Buechel and Hahn, 2017) scores valence, arousal, and dominance
    with a 5-point Self-Assessment Manikin. The midpoint 3 is neutral.
    ``(value - 3) / 2`` sends 1 to -1, 3 to 0, and 5 to 1. The EmoPair release
    stores this same map as ``A_rescaled`` and ``D_rescaled``.
    """
    return (value - 3.0) / 2.0
