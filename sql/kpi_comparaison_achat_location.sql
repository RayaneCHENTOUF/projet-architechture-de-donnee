-- KPI comparaison achat/location
-- Source CSVs:
--   data/gold/kpi_comparaison_achat_location_arrondissement.csv
--   data/gold/kpi_comparaison_achat_location_quartier_estime.csv

BEGIN;

CREATE TABLE IF NOT EXISTS fact_kpi_comparaison_achat_location_arrondissement (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    prix_m2_median NUMERIC(20,6),
    prix_m2_moyen NUMERIC(20,6),
    nb_transactions INTEGER,
    loyer_reference_median NUMERIC(20,6),
    loyer_reference_moyen NUMERIC(20,6),
    nb_observations INTEGER,
    kpi_comparaison_achat_location NUMERIC(20,6),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, arrondissement)
);

CREATE TABLE IF NOT EXISTS fact_kpi_comparaison_achat_location_quartier (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    code_insee_quartier VARCHAR(7) NOT NULL,
    prix_m2_median NUMERIC(20,6),
    prix_m2_moyen NUMERIC(20,6),
    nb_transactions INTEGER,
    loyer_reference_median NUMERIC(20,6),
    loyer_reference_moyen NUMERIC(20,6),
    nb_observations INTEGER,
    kpi_comparaison_achat_location NUMERIC(20,6),
    surface_quartier_m2 NUMERIC(20,6),
    part_surface NUMERIC(20,10),
    nb_transactions_estime INTEGER,
    nb_observations_estime INTEGER,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, code_insee_quartier)
);

-- COPY fact_kpi_comparaison_achat_location_arrondissement (
--     annee,
--     arrondissement,
--     prix_m2_median,
--     prix_m2_moyen,
--     nb_transactions,
--     loyer_reference_median,
--     loyer_reference_moyen,
--     nb_observations,
--     kpi_comparaison_achat_location
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/gold/kpi_comparaison_achat_location_arrondissement.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- COPY fact_kpi_comparaison_achat_location_quartier (
--     annee,
--     arrondissement,
--     code_insee_quartier,
--     prix_m2_median,
--     prix_m2_moyen,
--     nb_transactions,
--     loyer_reference_median,
--     loyer_reference_moyen,
--     nb_observations,
--     kpi_comparaison_achat_location,
--     surface_quartier_m2,
--     part_surface,
--     nb_transactions_estime,
--     nb_observations_estime
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/gold/kpi_comparaison_achat_location_quartier_estime.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

COMMIT;
