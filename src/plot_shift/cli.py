from __future__ import annotations

import argparse
import subprocess
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import cast

from plot_shift.data.downloader import download_remaining
from plot_shift.data.services import list_supported_scorer
from plot_shift.data.services.colab_io_service import (
    export_windows_for_colab,
    import_colab_scores,
)
from plot_shift.data.services.process_movies_service import run_process
from plot_shift.data.services.reversal_service import run_extract_reversals
from plot_shift.data.services.scoring_service import run_score_model


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


def cmd_score_model(args: argparse.Namespace) -> int:
    stats = run_score_model(
        model=args.model,
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
        vad_lexicon_file=args.lexicon_file,
        distilbert_max_length=args.semantic_max_length,
        n_windows=args.n_windows,
        window_duration=timedelta(seconds=args.window_seconds),
        windower=args.windower,
    )
    print(stats)
    return 0


def cmd_export_colab_data(args: argparse.Namespace) -> int:
    stats = export_windows_for_colab(
        db_path=args.db,
        out_csv=args.out_csv,
        n_windows=args.n_windows,
        window_seconds=args.window_seconds,
        windower=args.windower,
        limit=args.limit,
    )
    print(stats)
    return 0


def cmd_import_colab_scores(args: argparse.Namespace) -> int:
    stats = import_colab_scores(
        csv_path=args.csv_path,
        db_path=args.db,
        batch_size=args.batch_size,
    )
    print(stats)
    return 0


def cmd_extract_reversals(args: argparse.Namespace) -> int:
    stats = run_extract_reversals(
        db_path=args.db,
        scorer_name=args.model,
        dimension=args.dimension,
        limit_movies=args.limit_movies,
        detector=args.detector,
        trend_window_size=args.trend_window_size,
        ruptures_penalty=args.ruptures_penalty,
        window_seconds=args.window_seconds,
    )
    print(stats)
    return 0


def _add_window_kind(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--windower",
        choices=("fixed-width-duration", "fixed-duration"),
        default="fixed-width-duration",
        help=(
            "fixed-width-duration places --n-windows windows of --window-seconds across the movie. "
            "fixed-duration places abutting windows of --window-seconds and the count "
            "follows the movie length (default: fixed-width-duration)"
        ),
    )


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
        default=100,
        help="Insert batch size",
    )
    process_subs.set_defaults(func=cmd_process_subs)

    score_model = subparsers.add_parser(
        "score-model",
        help="Score subtitle sentences with selected model strategy",
    )
    score_model.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    score_model.add_argument(
        "--model",
        choices=list_supported_scorer(),
        required=True,
        help="Scoring strategy",
    )
    score_model.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for sentence score upserts",
    )
    score_model.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on valid movies to score",
    )
    score_model.add_argument(
        "--lexicon-file",
        default="data/raw/lexicons/vad_lexicon.txt",
        help="VAD lexicon file (used when --model vad)",
    )
    score_model.add_argument(
        "--semantic-max-length",
        type=int,
        default=512,
        help="Max token length for distilbert-sst2 (default: 512)",
    )
    score_model.add_argument(
        "--window-seconds",
        type=int,
        default=300,
        help="Window duration in seconds (default: 300)",
    )
    score_model.add_argument(
        "--n-windows",
        type=int,
        default=100,
        help="Window count for --windower fixed-width-duration (default: 100)",
    )
    _add_window_kind(score_model)
    score_model.set_defaults(func=cmd_score_model)

    export_colab = subparsers.add_parser(
        "export-colab-data",
        help="Export narrative windows to CSV for remote scoring in Google Colab",
    )
    export_colab.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    export_colab.add_argument(
        "--out-csv",
        default="data/proceeded/colab_input.csv",
        help="Output CSV path (upload this to Colab)",
    )
    export_colab.add_argument(
        "--n-windows",
        type=int,
        default=100,
        help="Number of equal-width windows per movie (default: 100)",
    )
    export_colab.add_argument(
        "--window-seconds",
        type=int,
        default=300,
        help="Window width in seconds (default: 300 = 5 min)",
    )
    _add_window_kind(export_colab)
    export_colab.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on the number of movies to export",
    )
    export_colab.set_defaults(func=cmd_export_colab_data)

    import_colab = subparsers.add_parser(
        "import-colab-scores",
        help="Import window-level scores from the Colab scoring notebook",
    )
    import_colab.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    import_colab.add_argument(
        "--csv-path",
        required=True,
        help=(
            "Path to the scored CSV from Colab. "
            "Required columns: imdb_id_int, window_idx, total_windows, "
            "from_segment_idx, to_segment_idx, scorer_name, scorer_kind, "
            "dimension, score"
        ),
    )
    import_colab.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Rows per DB insert batch (default: 1000)",
    )
    import_colab.set_defaults(func=cmd_import_colab_scores)

    extract_reversals = subparsers.add_parser(
        "extract-reversals",
        help="Detect narrative reversals on windowed model_scores",
    )
    extract_reversals.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    extract_reversals.add_argument(
        "--model",
        default=None,
        choices=["vader", "vad", "vad-bert", "pert-emopair", "distilbert-sst2", "jev"],
        required=True,
        help="scorer name",
    )
    extract_reversals.add_argument(
        "--dimension",
        default=None,
        help="Optional dimension filter (valence, arousal, dominance, aggregate)",
    )
    extract_reversals.add_argument(
        "--limit-movies",
        type=int,
        default=None,
        help="Optional cap on movies considered",
    )
    extract_reversals.add_argument(
        "--detector",
        choices=["trendet", "ruptures"],
        default="trendet",
        help="Reversal detector implementation (default: trendet)",
    )
    extract_reversals.add_argument(
        "--trend-window-size",
        type=int,
        default=5,
        help="Shortest trend piece in windows, like trendet window_size (ruptures min_size, default: 5)",
    )
    extract_reversals.add_argument(
        "--ruptures-penalty",
        type=float,
        default=1.0,
        help=(
            "Penalty multiplier c; PELT uses c * var(series) * log(n), so it is "
            "scorer-independent. Higher means fewer reversals (default: 1.0)"
        ),
    )
    extract_reversals.add_argument(
        "--window-seconds",
        type=int,
        default=300,
        help="Window width used when scoring, recorded with the features (default: 300)",
    )
    extract_reversals.set_defaults(func=cmd_extract_reversals)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    func = cast(Callable[[argparse.Namespace], int], args.func)
    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
