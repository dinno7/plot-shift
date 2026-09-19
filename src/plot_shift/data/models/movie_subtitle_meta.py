from dataclasses import dataclass
from datetime import timedelta

from plot_shift.data.models.subtitle_segment import SubtitleSegment


@dataclass()
class MovieSubtitle:
    imdb_id: int
    words: list[str]
    _segments: list[SubtitleSegment]

    @property
    def segments(self) -> list[SubtitleSegment]:
        return [segment for segment in self._segments]

    @property
    def segments_text(self) -> list[str]:
        return [segment.content for segment in self._segments]

    @property
    def words_count(self) -> int:
        return len(self.words)

    @property
    def sentences_count(self) -> int:
        return len(self._segments)

    @property
    def duration(self) -> timedelta:
        """Real screen-time span, derived from segment timestamps (not the
        sum of cue durations, which would double-count overlapping cues)."""
        if not self._segments:
            return timedelta()
        return max(segment.end for segment in self._segments)

    @property
    def is_valid(self) -> bool:
        duration_minutes = self.duration.total_seconds() / 60
        if duration_minutes <= 0:
            return False
        return self.words_count >= 1000 and self.words_count >= (duration_minutes / 5)
