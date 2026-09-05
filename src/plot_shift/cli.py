from __future__ import annotations

import argparse
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from plot_shift.data.downloader import download_remaining
from plot_shift.data.services.process_movies_service import run_process
from plot_shift.data.services.score_lexicon_service import (
    run_score_semantic,
    run_score_vad,
    run_score_vader,
)


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


def cmd_score_vader(args: argparse.Namespace) -> int:
    stats = run_score_vader(
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
    )
    print(stats)
    return 0


def cmd_score_vad(args: argparse.Namespace) -> int:
    stats = run_score_vad(
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
        lexicon_file=args.lexicon_file,
    )
    print(stats)
    return 0


def cmd_score_semantic(args: argparse.Namespace) -> int:
    stats = run_score_semantic(
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
        model_name=args.model_name,
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

    score_vader = subparsers.add_parser(
        "score-vader",
        help="Score subtitle sentences with VADER and persist results",
    )
    score_vader.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    score_vader.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for sentence score upserts",
    )
    score_vader.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of valid movies to score",
    )
    score_vader.set_defaults(func=cmd_score_vader)

    score_vad = subparsers.add_parser(
        "score-vad",
        help="Score subtitle sentences with NRC-VAD and persist results",
    )
    score_vad.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    score_vad.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for sentence score upserts",
    )
    score_vad.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of valid movies to score",
    )
    score_vad.add_argument(
        "--lexicon-file",
        default="data/raw/lexicons/vad_lexicon.txt",
        help="Path to VAD lexicon file",
    )
    score_vad.set_defaults(func=cmd_score_vad)

    score_semantic = subparsers.add_parser(
        "score-semantic",
        help="Score subtitle sentences with a transformer sentiment model",
    )
    score_semantic.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    score_semantic.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for sentence score upserts",
    )
    score_semantic.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on valid movies to score",
    )
    score_semantic.add_argument(
        "--model-name",
        default="cardiffnlp/twitter-roberta-base-sentiment-latest",
        help="Hugging Face model name for sequence classification",
    )
    score_semantic.set_defaults(func=cmd_score_semantic)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    func = cast(Callable[[argparse.Namespace], int], args.func)
    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
