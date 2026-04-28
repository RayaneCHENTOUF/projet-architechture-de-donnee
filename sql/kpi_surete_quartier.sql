-- KPI surete quartier
-- Source CSV: data/gold/kpi_score_surete_quartier_estime_depuis_iris.csv

BEGIN;

CREATE TABLE IF NOT EXISTS fact_kpi_surete_quartier (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    code_insee_quartier VARCHAR(7) NOT NULL,
    score_surete_quartier_moyen_100 NUMERIC(20,6),
    score_risque_quartier_moyen_100 NUMERIC(20,6),
    score_surete_iris_min_100 NUMERIC(20,6),
    score_surete_iris_max_100 NUMERIC(20,6),
    score_surete_iris_std_100 NUMERIC(20,6),
    score_risque_iris_min_100 NUMERIC(20,6),
    score_risque_iris_max_100 NUMERIC(20,6),
    score_risque_iris_std_100 NUMERIC(20,6),
    nb_iris_rattaches INTEGER,
    codes_iris_rattaches TEXT,
    noms_iris_rattaches TEXT,
    dist_commissariat_km_moyenne NUMERIC(20,6),
    nb_cameras_arrondissement INTEGER,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, code_insee_quartier)
);

-- COPY fact_kpi_surete_quartier (
--     annee,
--     arrondissement,
--     code_insee_quartier,
--     score_surete_quartier_moyen_100,
--     score_risque_quartier_moyen_100,
--     score_surete_iris_min_100,
--     score_surete_iris_max_100,
--     score_surete_iris_std_100,
--     score_risque_iris_min_100,
--     score_risque_iris_max_100,
--     score_risque_iris_std_100,
--     nb_iris_rattaches,
--     codes_iris_rattaches,
--     noms_iris_rattaches,
--     dist_commissariat_km_moyenne,
--     nb_cameras_arrondissement
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/gold/kpi_score_surete_quartier_estime_depuis_iris.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

COMMIT;
