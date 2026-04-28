-- KPI repartition logements sociaux
-- Source CSV: data/gold/kpi_repartition_logements_sociaux.csv

BEGIN;

CREATE TABLE IF NOT EXISTS fact_kpi_repartition_logements_sociaux (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    code_insee_quartier VARCHAR(7) NOT NULL,
    nom_quartier TEXT,
    logements_finances_total NUMERIC(20,6),
    logements_finances_moyen NUMERIC(20,6),
    nb_programmes INTEGER,
    nb_bailleurs INTEGER,
    nb_pla_i_total NUMERIC(20,6),
    nb_plus_total NUMERIC(20,6),
    nb_plus_cd_total NUMERIC(20,6),
    nb_pls_total NUMERIC(20,6),
    latitude_moyenne NUMERIC(20,6),
    longitude_moyenne NUMERIC(20,6),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, arrondissement, code_insee_quartier)
);

-- COPY fact_kpi_repartition_logements_sociaux (
--     annee,
--     arrondissement,
--     code_insee_quartier,
--     nom_quartier,
--     logements_finances_total,
--     logements_finances_moyen,
--     nb_programmes,
--     nb_bailleurs,
--     nb_pla_i_total,
--     nb_plus_total,
--     nb_plus_cd_total,
--     nb_pls_total,
--     latitude_moyenne,
--     longitude_moyenne
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/gold/kpi_repartition_logements_sociaux.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

COMMIT;
