from __future__ import annotations

import argparse
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from plot_shift.data.downloader import download_remaining
from plot_shift.data.services.process_movies_service import run_process


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def cmd_fetch_imdb(_: argparse.Namespace) -> int:
    script = repo_root() / "download_prerequire_raw.sh"
    subprocess.run(["bash", str(script)], check=True, cwd=repo_root())
    return 0


def cmd_download_subs(args: argparse.Namespace) -> int:
    stats = download_remaining(
        db_path=args.db,
        out_dir=args.subtitles_dir,
        limit=args.limit,
    )
    print(stats)
    return 0


def cmd_process_subs(args: argparse.Namespace) -> int:
    stats = run_process(
        db_path=args.db,
        subtitles_dir=args.subtitles_dir,
        batch_size=args.batch_size,
    )
    print(stats)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plot-shift",
        description="Plot Shift thesis pipeline (main branch minimal CLI)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_imdb = subparsers.add_parser(
        "fetch-imdb",
        help="Download IMDb title.basics and title.ratings TSV files",
    )
    fetch_imdb.set_defaults(func=cmd_fetch_imdb)

    download_subs = subparsers.add_parser(
        "download-subs",
        help="Download subtitles for movies from the local catalog",
    )
    download_subs.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    download_subs.add_argument(
        "--subtitles-dir",
        default="data/raw/subtitles",
        help="Subtitle output directory",
    )
    download_subs.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of remaining movies to download",
    )
    download_subs.set_defaults(func=cmd_download_subs)

    process_subs = subparsers.add_parser(
        "process-subs",
        help="Parse downloaded .srt files and insert cleaned subtitle rows",
    )
    process_subs.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    process_subs.add_argument(
        "--subtitles-dir",
        default="data/raw/subtitles",
        help="Directory containing downloaded subtitle files",
    )
    process_subs.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Insert batch size",
    )
    process_subs.set_defaults(func=cmd_process_subs)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    func = cast(Callable[[argparse.Namespace], int], args.func)
    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
