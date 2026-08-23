from dataclasses import dataclass
from datetime import timedelta


@dataclass()
class MovieSubtitlesMeta:
    imdb_id: int
    words: list[str]
    sentences: list[str]
    duration: timedelta

    @property
    def words_count(self) -> int:
        return len(self.words)

    @property
    def unique_words_count(self) -> int:
        return len(set(self.words))

    @property
    def sentences_count(self) -> int:
        return len(self.sentences)

    @property
    def cleaned_text(self) -> str:
        return " ".join(self.sentences)

    @property
    def is_valid(self) -> bool:
        duration_minutes = self.duration.total_seconds() / 60
        return self.words_count >= 1000 and self.words_count >= (duration_minutes / 5)
