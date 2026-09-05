from abc import ABC, abstractmethod
from typing import Self

from plot_shift.data.models import (
    MovieMeta,
    SentenceModelScore,
    Subtitle,
    SubtitleMeta,
)
from plot_shift.data.models.movie_subtitle_meta import MovieSubtitlesMeta


class PlotShiftDB(ABC):
    """Abstract contract for the PlotShift database facade."""

    # INFO: All Repo
    movies_meta: MovieMetaRepository
    subtitle_meta: SubtitleMetaRepository
    subtitles: SentencesRepository
    movie_subtitles_meta: MovieSubtitlesMetaRepository
    sentence_model_scores: SentenceModelScoreRepository

    @abstractmethod
    def close(self) -> None:
        """Release underlying database resources."""
        ...

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()


class MovieMetaRepository(ABC):
    """Abstract contract for movie metadata persistence."""

    @abstractmethod
    def insert_many(self, movies_meta_list: list[MovieMeta]) -> None: ...

    @abstractmethod
    def get_all(self) -> list[MovieMeta]: ...


class SentencesRepository(ABC):
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


class SentenceModelScoreRepository(ABC):
    """Abstract contract for sentence-level sentiment score persistence."""

    @abstractmethod
    def insert_many(self, scores: list[SentenceModelScore]) -> None:
        """Insert or update many sentence-level scores."""
        ...

    @abstractmethod
    def delete_movie_model(self, imdb_id_int: int, model: str) -> None:
        """Delete existing scores for one movie/model pair."""
        ...


class MovieSubtitlesMetaRepository(ABC):
    """
    Abstract repository contract for MovieSubtitlesMeta persistence.

    All implementations must handle the full lifecycle of processed
    subtitle metadata including aggregate statistics and cleaned sentences.
    """

    @abstractmethod
    def insert(
        self,
        meta: MovieSubtitlesMeta,
    ) -> None:
        """
        Persist or update processed MovieSubtitlesMeta and its sentences.

        Args:
            meta: A fully processed MovieSubtitlesMeta instance.
                  meta.process() MUST be called before saving.

        Raises:
            ValueError: If meta has not been processed (_sentences is None).
        """
        ...

    @abstractmethod
    def insert_many(self, metas: list[MovieSubtitlesMeta]) -> None:
        """
        Persist or update multiple processed MovieSubtitlesMeta records atomically.

        All records are saved within a single transaction. If any record fails
        validation, none are persisted.

        Args:
            metas: List of fully processed MovieSubtitlesMeta instances.

        Raises:
            ValueError: If any meta has not been processed.
        """
        ...

    @abstractmethod
    def list_valid_imdb_ids(self) -> list[int]:
        """IMDb integer ids with is_valid true."""
        ...

    @abstractmethod
    def find_by_imdb_id(self, imdb_id: int) -> MovieSubtitlesMeta | None:
        """
        Reconstruct a MovieSubtitlesMeta from persistent storage.

        The returned object will have pre-computed statistics and cleaned
        sentences. The raw 'text' field may be empty depending on the
        storage schema.

        Args:
            imdb_id: The IMDb integer identifier.

        Returns:
            Reconstructed domain object, or None if not found.
        """
        ...

    @abstractmethod
    def list_sentences_by_imdb_id(self, imdb_id: int) -> list[str]:
        """Return processed sentences for one IMDb integer id."""
        ...

    @abstractmethod
    def exists(self, imdb_id: int) -> bool:
        """
        Check whether processed metadata exists for a given IMDb ID.

        This should be more efficient than find_by_imdb_id() since it
        does not need to reconstruct the full domain object.

        Args:
            imdb_id: The IMDb integer identifier.

        Returns:
            True if a record exists, False otherwise.
        """
        ...

    @abstractmethod
    def delete(self, imdb_id: int) -> None:
        """
        Remove all persisted data for a given IMDb ID.

        Must atomically remove both the meta record and all associated
        sentences to prevent orphaned data.

        Args:
            imdb_id: The IMDb integer identifier.
        """
        ...
