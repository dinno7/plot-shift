import os
from pathlib import Path

from dotenv import load_dotenv
from opensubtitlescom import OpenSubtitles
from opensubtitlescom.responses import Subtitle

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models.subtitle_meta import SubtitleMeta


class SubtitleDownloader:
    def __init__(
        self,
        out_dir: str,
        user_agent: str,
        api_key: str,
        username: str,
        password: str,
    ):
        self.opensub = OpenSubtitles(user_agent=user_agent, api_key=api_key)
        self.opensub.login(username=username, password=password)
        self.out_dir = out_dir

    def best_sub_with_imdb_id(self, id: int) -> Subtitle:
        subs = self.opensub.search(
            imdb_id=id,
            languages="en",
            type="movie",
            machine_translated="exclude",
            ai_translated="exclude",
            order_by="download_count",
            order_direction="desc",
        )

        if subs.total_count == 0:
            raise NameError(f"No any result for {id}")
        return max(subs.data, key=lambda x: x.download_count)

    def download_with_file_id(self, file_id: int, file_path: str) -> None:
        sub_content = self.opensub.download(
            str(file_id),
        )
        out_file = file_path
        with open(
            out_file,
            mode="wb",
        ) as subfile:
            subfile.write(sub_content)

    def download_with_imdb_id(self, id: int) -> tuple[Subtitle, str]:
        item: Subtitle = self.best_sub_with_imdb_id(id)
        if item == None and item.file_id == None:
            raise ValueError("item or file_id is not exists")
            return

        out_file = str(Path(self.out_dir) / f"{item.imdb_id}_{item.file_id}.srt")
        self.download_with_file_id(item.file_id, out_file)
        return (item, out_file)

    def download_with_imdb_ids(self, ids: list[int]) -> None:
        for id in ids:
            try:
                self.download_with_imdb_id(id)
            except Exception as err:  # noqa: BLE001 - batch downloader must skip bad ids
                print(err)
                continue


def download_remaining(
    db_path: str = "data/proceeded/data.db",
    out_dir: str = "data/raw/subtitles",
    limit: int | None = None,
) -> dict[str, int]:
    """Download English subs for catalog ids not yet in subtitles_meta."""
    load_dotenv()
    required = (
        "OPEN_SUBTITLE_API_KEY",
        "OPEN_SUBTITLE_USER_AGENT",
        "OPEN_SUBTITLE_USERNAME",
        "OPEN_SUBTITLE_PASSWORD",
    )
    for name in required:
        if os.getenv(name) is None:
            raise ValueError(f"Please set {name}")

    api_key = os.getenv("OPEN_SUBTITLE_API_KEY")
    user_agent = os.getenv("OPEN_SUBTITLE_USER_AGENT")
    username = os.getenv("OPEN_SUBTITLE_USERNAME")
    password = os.getenv("OPEN_SUBTITLE_PASSWORD")
    assert api_key is not None and user_agent is not None
    assert username is not None and password is not None

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    downloader = SubtitleDownloader(
        out_dir=out_dir,
        api_key=api_key,
        user_agent=user_agent,
        username=username,
        password=password,
    )
    stats = {"remaining": 0, "ok": 0, "failed": 0}
    with PlotShiftSqliteDB(db_path) as repo:
        metas = repo.movies_meta.get_all()
        downloaded_ids = {d.imdb_id_int for d in repo.subtitle_meta.get_all()}
        remained = [m for m in metas if m.imdb_id_int not in downloaded_ids]
        if limit is not None:
            remained = remained[:limit]
        stats["remaining"] = len(remained)
        print(f"remaining {len(remained)}")
        for movie in remained:
            assert movie.imdb_id_int is not None
            print(f"downloading imdb_id={movie.imdb_id_int}")
            try:
                sub, filepath = downloader.download_with_imdb_id(movie.imdb_id_int)
                if sub.file_id is None:
                    sub.file_id = 0
                repo.subtitle_meta.insert_one(
                    SubtitleMeta(
                        file_id=sub.file_id,
                        download_count=sub.download_count,
                        imdb_id_int=sub.imdb_id,
                        file_name_on_disk=Path(filepath).name,
                        language=sub.language,
                        new_download_count=sub.new_download_count,
                        subtitle_id=sub.subtitle_id,
                        upload_date=sub.upload_date,
                        url=sub.url,
                        dump_json=sub.to_json(),
                    )
                )
                stats["ok"] += 1
                print(f"saved {filepath}")
            except Exception as err:  # noqa: BLE001 - skip bad ids
                stats["failed"] += 1
                print(err)
                continue
    return stats


if __name__ == "__main__":
    download_remaining()
