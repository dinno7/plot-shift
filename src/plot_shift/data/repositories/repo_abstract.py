from abc import ABC, abstractmethod

from opensubtitlescom.responses import Subtitle

from plot_shift.data import MovieMeta, SubtitleMeta
from plot_shift.data.repositories.repo_abstract import (
    MovieMetaRepository,
    SubtitleMetaRepository,
    SubtitleRepository,
)


class PlotShiftDB(ABC):
    """Abstract contract for the PlotShift database facade."""

    # INFO: All Repo
    movies_meta: MovieMetaRepository
    subtitle_meta: SubtitleMetaRepository
    subtitles: SubtitleRepository

    @abstractmethod
    def close(self) -> None:
        """Release underlying database resources."""
        ...

    def __enter__(self) -> PlotShiftDB:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class MovieMetaRepository(ABC):
    """Abstract contract for movie metadata persistence."""

    @abstractmethod
    def init_table(self) -> None: ...

    @abstractmethod
    def drop_table(self) -> None: ...

    @abstractmethod
    def fresh_table(self) -> None: ...

    @abstractmethod
    def insert_many(self, movies_meta_list: list[MovieMeta]) -> None: ...

    @abstractmethod
    def get_all(self) -> list[MovieMeta]: ...


class SubtitleRepository(ABC):
    """Abstract contract for subtitle cue persistence."""

    @abstractmethod
    def insert_one(self, entry: Subtitle) -> int | None: ...

    @abstractmethod
    def insert_many(self, entries: list[Subtitle]) -> None: ...

    @abstractmethod
    def get_by_id(self, entry_id: int) -> Subtitle | None: ...

    @abstractmethod
    def get_by_imdb_id(self, imdb_id_int: int) -> list[Subtitle]: ...


class SubtitleMetaRepository(ABC):
    """Abstract contract for downloaded subtitle persistence."""

    @abstractmethod
    def insert_one(self, subtitle: SubtitleMeta) -> int | None: ...

    @abstractmethod
    def get_all(self) -> list[SubtitleMeta]: ...
