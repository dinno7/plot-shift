from __future__ import annotations

import csv
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from scipy.stats import pearsonr


def _compute_reversal_features(
    scores: list[float],
    prominence: float,
) -> tuple[int, float, float, int]:
    from scipy.signal import find_peaks

    if len(scores) < 3:
        return (0, 0.0, 0.0, len(scores))

    peak_idx, peak_props = find_peaks(scores, prominence=prominence)
    trough_idx, trough_props = find_peaks([-value for value in scores], prominence=prominence)

    prominences: list[float] = []
    prominences.extend(float(v) for v in peak_props.get("prominences", []))
    prominences.extend(float(v) for v in trough_props.get("prominences", []))

    n_reversals = int(len(peak_idx) + len(trough_idx))
    if not prominences:
        return (n_reversals, 0.0, 0.0, len(scores))

    mean_intensity = float(sum(prominences) / len(prominences))
    max_intensity = float(max(prominences))
    return (n_reversals, mean_intensity, max_intensity, len(scores))


def run_extract_reversals(
    db_path: str = "data/proceeded/data.db",
    model: str | None = None,
    dimension: str | None = None,
    limit_movies: int | None = None,
    prominence: float = 0.2,
) -> dict[str, int | float]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        movie_filter_sql = ""
        movie_filter_args: list[object] = []
        if limit_movies is not None:
            movie_filter_sql = (
                "AND sms.imdb_id_int IN ("
                "SELECT DISTINCT imdb_id_int FROM sentence_model_scores "
                "ORDER BY imdb_id_int LIMIT ?)"
            )
            movie_filter_args.append(limit_movies)

        where_parts = ["1=1"]
        where_args: list[object] = []
        if model is not None:
            where_parts.append("sms.model = ?")
            where_args.append(model)
        if dimension is not None:
            where_parts.append("sms.dimension = ?")
            where_args.append(dimension)

        groups = conn.execute(
            f"""
            SELECT DISTINCT sms.imdb_id_int, sms.model, sms.dimension
            FROM sentence_model_scores sms
            WHERE {" AND ".join(where_parts)}
            {movie_filter_sql}
            ORDER BY sms.imdb_id_int, sms.model, sms.dimension
            """,
            [*where_args, *movie_filter_args],
        ).fetchall()

        rows_to_upsert: list[tuple[object, ...]] = []
        for group in groups:
            imdb_id_int = int(group["imdb_id_int"])
            group_model = str(group["model"])
            group_dimension = str(group["dimension"])

            series_rows = conn.execute(
                """
                SELECT score
                FROM sentence_model_scores
                WHERE imdb_id_int = ? AND model = ? AND dimension = ?
                ORDER BY sentence_idx ASC
                """,
                (imdb_id_int, group_model, group_dimension),
            ).fetchall()
            scores = [float(row["score"]) for row in series_rows]
            n_reversals, mean_intensity, max_intensity, series_length = _compute_reversal_features(
                scores=scores,
                prominence=prominence,
            )

            rows_to_upsert.append(
                (
                    imdb_id_int,
                    group_model,
                    group_dimension,
                    float(prominence),
                    series_length,
                    n_reversals,
                    mean_intensity,
                    max_intensity,
                )
            )

        if rows_to_upsert:
            conn.executemany(
                """
                INSERT INTO reversal_features
                    (imdb_id_int, model, dimension, prominence, series_length, n_reversals, mean_intensity, max_intensity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(imdb_id_int, model, dimension) DO UPDATE SET
                    prominence = excluded.prominence,
                    series_length = excluded.series_length,
                    n_reversals = excluded.n_reversals,
                    mean_intensity = excluded.mean_intensity,
                    max_intensity = excluded.max_intensity
                """,
                rows_to_upsert,
            )
            conn.commit()

    return {
        "groups_processed": len(rows_to_upsert),
        "prominence": float(prominence),
    }


def run_evaluate_models(
    db_path: str = "data/proceeded/data.db",
    out_csv: str = "data/proceeded/eval_reversal_summary.csv",
    model: str | None = None,
    dimension: str | None = None,
) -> dict[str, int | str]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        where_parts = ["1=1"]
        args: list[object] = []
        if model is not None:
            where_parts.append("rf.model = ?")
            args.append(model)
        if dimension is not None:
            where_parts.append("rf.dimension = ?")
            args.append(dimension)

        rows = conn.execute(
            f"""
            SELECT
              rf.imdb_id_int,
              rf.model,
              rf.dimension,
              rf.n_reversals,
              rf.mean_intensity,
              rf.max_intensity,
              mm.average_rating
            FROM reversal_features rf
            JOIN movies_meta mm ON mm.imdb_id_int = rf.imdb_id_int
            WHERE {" AND ".join(where_parts)}
            ORDER BY rf.model, rf.dimension, rf.imdb_id_int
            """,
            args,
        ).fetchall()

    grouped: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for row in rows:
        key = (str(row["model"]), str(row["dimension"]))
        grouped.setdefault(key, []).append(row)

    output_rows: list[dict[str, object]] = []
    for (model_name, dimension_name), group_rows in grouped.items():
        ratings = [float(r["average_rating"]) for r in group_rows]
        reversals = [float(r["n_reversals"]) for r in group_rows]
        mean_intensity = [float(r["mean_intensity"]) for r in group_rows]
        max_intensity = [float(r["max_intensity"]) for r in group_rows]

        def corr(x: list[float], y: list[float]) -> float | None:
            if len(x) < 2:
                return None
            if len(set(x)) <= 1 or len(set(y)) <= 1:
                return None
            return float(pearsonr(x, y).statistic)

        output_rows.append(
            {
                "model": model_name,
                "dimension": dimension_name,
                "n_movies": len(group_rows),
                "pearson_n_reversals_vs_rating": corr(reversals, ratings),
                "pearson_mean_intensity_vs_rating": corr(mean_intensity, ratings),
                "pearson_max_intensity_vs_rating": corr(max_intensity, ratings),
            }
        )

    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "model",
                "dimension",
                "n_movies",
                "pearson_n_reversals_vs_rating",
                "pearson_mean_intensity_vs_rating",
                "pearson_max_intensity_vs_rating",
            ],
        )
        writer.writeheader()
        for row in output_rows:
            writer.writerow(row)

    return {
        "groups_evaluated": len(output_rows),
        "rows_loaded": len(rows),
        "out_csv": str(out_path),
    }


def run_report_snapshot(
    db_path: str = "data/proceeded/data.db",
    out_md: str = "data/proceeded/eval_snapshot.md",
    out_csv: str = "data/proceeded/eval_reversal_summary.csv",
    model: str | None = None,
    dimension: str | None = None,
    min_movies: int = 2,
) -> dict[str, str | int]:
    eval_result = run_evaluate_models(
        db_path=db_path,
        out_csv=out_csv,
        model=model,
        dimension=dimension,
    )
    eval_csv_path = Path(str(eval_result["out_csv"]))
    report_path = Path(out_md)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    with eval_csv_path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({k: str(v) for k, v in row.items()})

    def to_float(value: str) -> float | None:
        v = value.strip()
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    filtered_rows = [row for row in rows if int(row["n_movies"]) >= min_movies]

    ranked: list[tuple[float, dict[str, str], str, float]] = []
    for row in filtered_rows:
        metrics: list[tuple[str, float]] = []
        for col in (
            "pearson_n_reversals_vs_rating",
            "pearson_mean_intensity_vs_rating",
            "pearson_max_intensity_vs_rating",
        ):
            value = to_float(row.get(col, ""))
            if value is not None:
                metrics.append((col, value))
        if not metrics:
            continue
        metric_name, metric_value = max(metrics, key=lambda item: abs(item[1]))
        ranked.append((abs(metric_value), row, metric_name, metric_value))

    ranked.sort(key=lambda item: item[0], reverse=True)
    top_rows = ranked[:5]

    lines: list[str] = []
    generated_at = datetime.now(UTC).isoformat()
    lines.append("# Evaluation snapshot")
    lines.append("")
    lines.append(f"- generated_at_utc: `{generated_at}`")
    lines.append(f"- db_path: `{db_path}`")
    lines.append(f"- evaluated_groups_total: `{len(rows)}`")
    lines.append(f"- groups_with_n_movies_gte_{min_movies}: `{len(filtered_rows)}`")
    lines.append(f"- source_csv: `{eval_csv_path}`")
    lines.append("")
    lines.append("## Top groups by strongest absolute Pearson correlation")
    lines.append("")
    if not top_rows:
        lines.append("No groups met the filter or had valid correlation values.")
    else:
        lines.append("| model | dimension | n_movies | strongest_metric | pearson |abs_pearson|")
        lines.append("|---|---:|---:|---|---:|---:|")
        for abs_value, row, metric_name, metric_value in top_rows:
            lines.append(
                f"| {row['model']} | {row['dimension']} | {row['n_movies']} "
                f"| {metric_name} | {metric_value:.4f} | {abs_value:.4f} |"
            )

    lines.append("")
    lines.append("## Full command")
    lines.append("")
    lines.append(f"`uv run plot-shift evaluate-models --db {db_path} --out-csv {eval_csv_path}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "report_md": str(report_path),
        "summary_csv": str(eval_csv_path),
        "groups_total": len(rows),
        "groups_after_min_movies_filter": len(filtered_rows),
    }
