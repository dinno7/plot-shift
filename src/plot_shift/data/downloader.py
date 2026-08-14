import os
from pathlib import Path

from dotenv import load_dotenv
from opensubtitlescom import OpenSubtitles
from opensubtitlescom.responses import Subtitle

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

    def download_with_file_id(self, file_id: int, file_path: str):
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
        item: Subtitle | None = None
        try:
            item = self.best_sub_with_imdb_id(id)
        except Exception as err:
            raise err

        out_file = str(Path(self.out_dir) / f"{item.imdb_id}_{item.file_id}.srt")
        self.download_with_file_id(item.file_id, out_file)

        return (item, out_file)

    def download_with_imdb_ids(self, ids: list[int]):
        for id in ids:
            try:
                self.download_with_imdb_id(id)
            except Exception as err:
                print(err)
                continue


if __name__ == "__main__":
    load_dotenv()

    envs = [
        "OPEN_SUBTITLE_API_KEY",
        "OPEN_SUBTITLE_USER_AGENT",
        "OPEN_SUBTITLE_USERNAME",
        "OPEN_SUBTITLE_PASSWORD",
    ]
    for e in envs:
        if os.getenv(e) == None:
            raise ValueError(f"Please set {e}")

    api_key = os.getenv("OPEN_SUBTITLE_API_KEY")
    user_agent = os.getenv("OPEN_SUBTITLE_USER_AGENT")
    username = os.getenv("OPEN_SUBTITLE_USERNAME")
    password = os.getenv("OPEN_SUBTITLE_PASSWORD")

    out_dir = "./data/raw/subtitles"
    sub_downloader = SubtitleDownloader(
        out_dir=out_dir,
        api_key=api_key,
        user_agent=user_agent,
        username=username,
        password=password,
    )
    repo = PlotShiftSqliteDB("./data/proceeded/data.db")

    metas = repo.movies_meta.get_all()
    downloaded_subs = repo.subtitle_meta.get_all()
    downloaded_ids = {d.imdb_id_int for d in downloaded_subs}
    remained = [m for m in metas if m.imdb_id_int not in downloaded_ids]

    print(" > REMAINED", len(remained))
    for m in remained:
        print(f"🔃 Start Downloading subtitle with id {m.imdb_id_int}")

        sub, filepath = sub_downloader.download_with_imdb_id(m.imdb_id_int)
        new_sub = SubtitleMeta(
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
        repo.subtitle_meta.insert_one(new_sub)

        print(
            f"✅ Subtitle with id {sub.imdb_id} and name {sub.file_name} downloaded from {sub.url} to {filepath}"
        )
