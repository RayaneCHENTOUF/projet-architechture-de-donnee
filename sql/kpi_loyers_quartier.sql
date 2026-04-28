-- KPI loyers quartier
-- Source CSV: data/gold/kpi_loyers_quartier.csv

BEGIN;

CREATE TABLE IF NOT EXISTS fact_kpi_loyers_quartier (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    code_insee_quartier VARCHAR(7) NOT NULL,
    loyer_reference_median NUMERIC(20,6),
    loyer_reference_moyen NUMERIC(20,6),
    nb_observations INTEGER,
    loyer_reference_majore_median NUMERIC(20,6),
    loyer_reference_minore_median NUMERIC(20,6),
    nombre_pieces_median NUMERIC(20,6),
    nom_quartier TEXT,
    type_location_mode TEXT,
    epoque_construction_mode TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, code_insee_quartier)
);

-- COPY fact_kpi_loyers_quartier (
--     annee,
--     arrondissement,
--     code_insee_quartier,
--     loyer_reference_median,
--     loyer_reference_moyen,
--     nb_observations,
--     loyer_reference_majore_median,
--     loyer_reference_minore_median,
--     nombre_pieces_median,
--     nom_quartier,
--     type_location_mode,
--     epoque_construction_mode
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/gold/kpi_loyers_quartier.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

COMMIT;
