SELECT
    mm.imdb_id_int,
    mm.average_rating,
    rf.n_reversals,
    rf.scorer_name,
    rf.dimension
FROM
    reversal_features rf
    JOIN movies_meta mm ON rf.imdb_id_int = mm.imdb_id_int
GROUP BY
    mm.imdb_id_int,
    scorer_name,
    dimension;

