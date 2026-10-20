from abc import ABC, abstractmethod

from plot_shift.data.models import (
    ModelScore,
    MovieMeta,
    MovieSubtitle,
    ReversalFeatures,
    SubtitleMeta,
    SubtitleSegment,
)


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
    """Abstract contract for window-level sentiment score persistence."""

    @abstractmethod
    def insert_many(self, scores: list[ModelScore]) -> None:
        """Insert or update many window-level scores."""
        ...

    @abstractmethod
    def delete_movie_model(self, imdb_id_int: int, scorer_name: str) -> None:
        """Delete existing scores for one movie/scorer pair."""
        ...

    @abstractmethod
    def list_groups(
        self,
        scorer_name: str | None = None,
        dimension: str | None = None,
        limit_movies: int | None = None,
    ) -> list[tuple[int, str, str]]:
        """Return distinct (imdb_id_int, scorer_name, dimension) triples.

        Optionally filter by scorer_name and/or dimension; optionally cap the
        number of distinct movies considered (useful for smoke-test runs).
        Results are ordered by imdb_id_int, scorer_name, dimension.
        """
        ...

    @abstractmethod
    def list_windowed(
        self,
        imdb_id_int: int,
        scorer_name: str,
        dimension: str,
    ) -> list[ModelScore]:
        """Return all window-level scores for one (movie, scorer, dimension) triple.

        Rows are ordered by window_idx ascending so callers can feed the list
        directly into trend-detection without sorting.
        """
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
    def list_valid_imdb_ids(self, limit: int | None) -> list[int]:
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


class ReversalFeaturesRepository(ABC):
    """Abstract contract for reversal-feature persistence.

    One row per (movie, scorer_name, dimension) triple, written after
    trend-detection has been applied to the windowed score series.
    """

    @abstractmethod
    def upsert_many(self, features: list[ReversalFeatures]) -> None:
        """Insert or replace reversal features for a batch of triples."""
        ...

    @abstractmethod
    def list_all(
        self,
        scorer_name: str | None = None,
        dimension: str | None = None,
    ) -> list[ReversalFeatures]:
        """Return all stored features, optionally filtered by scorer/dimension.

        Results are ordered by imdb_id_int, scorer_name, dimension.
        """
        ...

    @abstractmethod
    def find(
        self,
        imdb_id_int: int,
        scorer_name: str,
        dimension: str,
    ) -> ReversalFeatures | None:
        """Return the features for one specific triple, or None."""
        ...

    @abstractmethod
    def delete_by_movie(self, imdb_id_int: int) -> None:
        """Remove all features for one movie (all scorers/dimensions)."""
        ...
