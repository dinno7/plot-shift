CREATE TABLE IF NOT EXISTS sentence_model_scores (
    imdb_id_int integer NOT NULL,
    from_segment_idx integer NOT NULL,
    to_segment_idx integer NOT NULL,
    model text NOT NULL,
    dimension text NOT NULL,
    score real NOT NULL,
    PRIMARY KEY (imdb_id_int, from_segment_idx, to_segment_idx, model, dimension)
);

CREATE INDEX IF NOT EXISTS idx_sentence_model_scores_lookup ON sentence_model_scores (imdb_id_int, model, dimension);

