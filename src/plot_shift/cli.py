from __future__ import annotations

import argparse
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from plot_shift.data.downloader import download_remaining
from plot_shift.data.services.process_movies_service import run_process
from plot_shift.data.services.reversal_features_service import (
    run_evaluate_models,
    run_extract_reversals,
    run_report_snapshot,
)
from plot_shift.data.services.score_lexicon_service import run_score_model
from plot_shift.data.services.semantic_io_service import (
    export_sentences_for_semantic,
    import_semantic_scores,
)
from plot_shift.sentiment import DEFAULT_SEMANTIC_MODEL_NAME, list_supported_scorer_strategies


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
    stats = run_score_model(
        model="vader",
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
    )
    print(stats)
    return 0


def cmd_score_vad(args: argparse.Namespace) -> int:
    stats = run_score_model(
        model="vad",
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
        vad_lexicon_file=args.lexicon_file,
    )
    print(stats)
    return 0


def cmd_score_semantic(args: argparse.Namespace) -> int:
    stats = run_score_model(
        model="semantic",
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
        semantic_model_name=args.model_name,
        semantic_max_length=args.max_length,
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
        semantic_model_name=args.semantic_model_name,
        semantic_max_length=args.semantic_max_length,
    )
    print(stats)
    return 0


def cmd_export_sentences_for_semantic(args: argparse.Namespace) -> int:
    stats = export_sentences_for_semantic(
        db_path=args.db,
        out_csv=args.out_csv,
        limit=args.limit,
    )
    print(stats)
    return 0


def cmd_import_semantic_scores(args: argparse.Namespace) -> int:
    stats = import_semantic_scores(
        csv_path=args.csv_path,
        db_path=args.db,
        batch_size=args.batch_size,
        default_model=args.default_model,
        default_dimension=args.default_dimension,
    )
    print(stats)
    return 0


def cmd_extract_reversals(args: argparse.Namespace) -> int:
    stats = run_extract_reversals(
        db_path=args.db,
        model=args.model,
        dimension=args.dimension,
        limit_movies=args.limit_movies,
        prominence=args.prominence,
    )
    print(stats)
    return 0


def cmd_evaluate_models(args: argparse.Namespace) -> int:
    stats = run_evaluate_models(
        db_path=args.db,
        out_csv=args.out_csv,
        model=args.model,
        dimension=args.dimension,
    )
    print(stats)
    return 0


def cmd_report_snapshot(args: argparse.Namespace) -> int:
    stats = run_report_snapshot(
        db_path=args.db,
        out_md=args.out_md,
        out_csv=args.out_csv,
        model=args.model,
        dimension=args.dimension,
        min_movies=args.min_movies,
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
        default=DEFAULT_SEMANTIC_MODEL_NAME,
        help="Hugging Face model name for sequence classification",
    )
    score_semantic.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Max tokens per sentence for semantic model",
    )
    score_semantic.set_defaults(func=cmd_score_semantic)

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
        choices=list_supported_scorer_strategies(),
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
        "--semantic-model-name",
        default=DEFAULT_SEMANTIC_MODEL_NAME,
        help="HF semantic model id (used when --model semantic)",
    )
    score_model.add_argument(
        "--semantic-max-length",
        type=int,
        default=512,
        help="Max semantic model token length (used when --model semantic)",
    )
    score_model.set_defaults(func=cmd_score_model)

    export_semantic = subparsers.add_parser(
        "export-sentences-for-semantic",
        help="Export sentence rows to CSV for cloud semantic scoring",
    )
    export_semantic.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    export_semantic.add_argument(
        "--out-csv",
        default="data/proceeded/semantic_input.csv",
        help="Output CSV path",
    )
    export_semantic.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on valid movies to export",
    )
    export_semantic.set_defaults(func=cmd_export_sentences_for_semantic)

    import_semantic = subparsers.add_parser(
        "import-semantic-scores",
        help="Import scored semantic CSV rows into sentence_model_scores",
    )
    import_semantic.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    import_semantic.add_argument(
        "--csv-path",
        required=True,
        help="Input CSV path (headers: imdb_id_int,sentence_idx,score[,model,dimension])",
    )
    import_semantic.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for score upserts",
    )
    import_semantic.add_argument(
        "--default-model",
        default="semantic:cardiffnlp/twitter-roberta-base-sentiment-latest",
        help="Fallback model name if CSV has no model column",
    )
    import_semantic.add_argument(
        "--default-dimension",
        default="valence",
        help="Fallback dimension if CSV has no dimension column",
    )
    import_semantic.set_defaults(func=cmd_import_semantic_scores)

    extract_reversals = subparsers.add_parser(
        "extract-reversals",
        help="Extract reversal features from sentence-level sentiment series",
    )
    extract_reversals.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    extract_reversals.add_argument(
        "--model",
        default=None,
        help="Optional model filter",
    )
    extract_reversals.add_argument(
        "--dimension",
        default=None,
        help="Optional dimension filter",
    )
    extract_reversals.add_argument(
        "--limit-movies",
        type=int,
        default=None,
        help="Optional cap on movies considered",
    )
    extract_reversals.add_argument(
        "--prominence",
        type=float,
        default=0.2,
        help="Peak/trough prominence threshold",
    )
    extract_reversals.set_defaults(func=cmd_extract_reversals)

    evaluate_models = subparsers.add_parser(
        "evaluate-models",
        help="Evaluate reversal features against IMDb rating",
    )
    evaluate_models.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    evaluate_models.add_argument(
        "--out-csv",
        default="data/proceeded/eval_reversal_summary.csv",
        help="Output summary CSV path",
    )
    evaluate_models.add_argument(
        "--model",
        default=None,
        help="Optional model filter",
    )
    evaluate_models.add_argument(
        "--dimension",
        default=None,
        help="Optional dimension filter",
    )
    evaluate_models.set_defaults(func=cmd_evaluate_models)

    report_snapshot = subparsers.add_parser(
        "report-snapshot",
        help="Generate compact markdown snapshot from evaluation results",
    )
    report_snapshot.add_argument(
        "--db",
        default="data/proceeded/data.db",
        help="SQLite database path",
    )
    report_snapshot.add_argument(
        "--out-md",
        default="data/proceeded/eval_snapshot.md",
        help="Output markdown report path",
    )
    report_snapshot.add_argument(
        "--out-csv",
        default="data/proceeded/eval_reversal_summary.csv",
        help="Output evaluation CSV path",
    )
    report_snapshot.add_argument(
        "--model",
        default=None,
        help="Optional model filter",
    )
    report_snapshot.add_argument(
        "--dimension",
        default=None,
        help="Optional dimension filter",
    )
    report_snapshot.add_argument(
        "--min-movies",
        type=int,
        default=2,
        help="Minimum movies required to include a group in top correlations",
    )
    report_snapshot.set_defaults(func=cmd_report_snapshot)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    func = cast(Callable[[argparse.Namespace], int], args.func)
    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
