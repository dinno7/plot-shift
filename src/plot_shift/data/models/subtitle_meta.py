from dataclasses import dataclass
from datetime import datetime


@dataclass
class SubtitleMeta:
    subtitle_id: str
    download_count: int
    new_download_count: int
    file_id: int
    imdb_id_int: int
    file_name_on_disk: str
    url: str
    id: int | None = None
    language: str | None = None
    upload_date: str | None = None
    fetched_at: datetime | None = None
    dump_json: str | None = None
