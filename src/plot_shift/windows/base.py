from abc import ABC, abstractmethod

from plot_shift.data.models import MovieSubtitle, NarrativeWindow


class WindowGenerator(ABC):
    """
    Generate narrative-level windows from timestamped subtitle segments.
    """

    @abstractmethod
    def generate(
        self,
        movie_subtitle: MovieSubtitle,
    ) -> list[NarrativeWindow]: ...

    @abstractmethod
    def name(self) -> str: ...
