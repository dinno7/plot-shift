from abc import ABC, abstractmethod

from plot_shift.data.models import (
    MovieMeta,
    ModelScore,
    SubtitleMeta,
)
from plot_shift.data.models.movie_subtitle_meta import MovieSubtitle
from plot_shift.data.models.subtitle_segment import SubtitleSegment


class MovieMetaRepository(ABC):
    """Abstract contract for movie metadata persistence."""

    @abstractmethod
    def insert_many(self, movies_meta_list: list[MovieMeta]) -> None: ...

    @abstractmethod
    def get_all(self) -> list[MovieMeta]: ...


class SubtitleMetaRepository(ABC):
    """Abstract contract for downloaded subtitle persistence."""

    @abstractmethod
    def insert_one(self, subtitle: SubtitleMeta) -> int | None: ...

    @abstractmethod
    def get_all(self) -> list[SubtitleMeta]: ...


class ModelScoresRepository(ABC):
    """Abstract contract for sentence-level sentiment score persistence."""

    @abstractmethod
    def insert_many(self, scores: list[ModelScore]) -> None:
        """Insert or update many window-level scores."""
        ...

    @abstractmethod
    def delete_movie_model(self, imdb_id_int: int, model: str) -> None:
        """Delete existing scores for one movie/model pair."""
        ...


class MovieSubtitlesRepository(ABC):
    """
    Abstract repository contract for MovieSubtitlesMeta persistence.

    All implementations must handle the full lifecycle of processed
    subtitle metadata including aggregate statistics and cleaned sentences.
    """

    @abstractmethod
    def upsert(
        self,
        movie_sub: MovieSubtitle,
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
    def upsert_many(self, movie_subs: list[MovieSubtitle]) -> None:
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
    def find_by_imdb_id(self, imdb_id: int) -> MovieSubtitle | None:
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
        """Return processed segment texts for one IMDb integer id, in order."""
        ...

    @abstractmethod
    def list_segments_by_imdb_id(self, imdb_id: int) -> list[SubtitleSegment]:
        """Return processed, timestamped segments for one IMDb integer id, in order."""
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


class SubtitleSegmentsRepository(ABC):
    """
    Abstract repository contract for SubtitleSegment persistence.
    """

    @abstractmethod
    def upsert(
        self,
        segment: SubtitleSegment,
    ) -> None:
        """
        Upsert processed subtitle's segment into SubtitleSegment.
        """
        ...

    @abstractmethod
    def upsert_many(self, segments: list[SubtitleSegment]) -> None:
        """
        Upsert multiple processed subtitle's segment into SubtitleSegment.

        All records are saved within a single transaction. If any record fails
        validation, none are persisted.
        """
        ...

    @abstractmethod
    def find_by_imdb_id(self, imdb_id: int) -> list[SubtitleSegment]: ...

    @abstractmethod
    def delete(self, imdb_id: int) -> None:
        """
        Remove all persisted data for a given IMDb ID.
        """
        ...
