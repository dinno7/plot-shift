CREATE TABLE IF NOT EXISTS sentence_model_scores (
    imdb_id_int integer NOT NULL,
    sentence_idx integer NOT NULL,
    model text NOT NULL,
    dimension text NOT NULL,
    score real NOT NULL,
    PRIMARY KEY (imdb_id_int, sentence_idx, model, dimension)
);

CREATE INDEX IF NOT EXISTS idx_sentence_model_scores_lookup ON sentence_model_scores (imdb_id_int, model, dimension);

