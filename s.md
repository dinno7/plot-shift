# Evaluation snapshot

- generated_at_utc: `2026-09-08T18:08:21.575786+00:00`
- db_path: `data/proceeded/data.db`
- evaluated_groups_total: `4`
- groups_with_n_movies_gte_2: `4`
- source_csv: `data/proceeded/eval_reversal_summary.csv`

## Top groups by strongest absolute Pearson correlation

| model | dimension | n_movies | strongest_metric | pearson |abs_pearson|
|---|---:|---:|---|---:|---:|
| vader | valence | 1129 | pearson_n_reversals_vs_rating | -0.0971 | 0.0971 |
| vad | valence | 1129 | pearson_n_reversals_vs_rating | -0.0724 | 0.0724 |
| vad | dominance | 1129 | pearson_mean_intensity_vs_rating | -0.0565 | 0.0565 |
| vad | arousal | 1129 | pearson_mean_intensity_vs_rating | -0.0356 | 0.0356 |

## Full command

`uv run plot-shift evaluate-models --db data/proceeded/data.db --out-csv data/proceeded/eval_reversal_summary.csv`
