-- KPI confort urbain
-- Source CSV: data/gold/gold_kpi_confort_urbain.csv

BEGIN;

CREATE TABLE IF NOT EXISTS fact_kpi_confort_quartier (
    arrondissement VARCHAR(2) NOT NULL,
    code_insee_quartier VARCHAR(7) NOT NULL,
    nom_quartier TEXT,
    surface_quartier_m2 NUMERIC(20,6),
    part_surface NUMERIC(20,10),
    incidents_estime NUMERIC(20,6),
    travaux_estime NUMERIC(20,6),
    gares_estime NUMERIC(20,6),
    risque_incidents_100 NUMERIC(20,6),
    score_confort_urbain_100 NUMERIC(20,6),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (code_insee_quartier)
);

-- COPY fact_kpi_confort_quartier (
--     arrondissement,
--     code_insee_quartier,
--     nom_quartier,
--     surface_quartier_m2,
--     part_surface,
--     incidents_estime,
--     travaux_estime,
--     gares_estime,
--     risque_incidents_100,
--     score_confort_urbain_100
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/gold/gold_kpi_confort_urbain.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');

COMMIT;
