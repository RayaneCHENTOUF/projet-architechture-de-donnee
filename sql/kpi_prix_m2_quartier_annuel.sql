-- KPI prix m2 quartier annuel
-- Source CSV: data/gold/kpi_prix_m2_quartier_annuel.csv

BEGIN;

CREATE TABLE IF NOT EXISTS fact_kpi_prix_m2_quartier_annuel (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    code_insee_quartier VARCHAR(7) NOT NULL,
    prix_m2_median NUMERIC(20,6),
    prix_m2_moyen NUMERIC(20,6),
    nb_ventes INTEGER,
    nb_ventes_estime INTEGER,
    surface_quartier_m2 NUMERIC(20,6),
    part_surface NUMERIC(20,10),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, code_insee_quartier)
);

-- COPY fact_kpi_prix_m2_quartier_annuel (
--     annee,
--     arrondissement,
--     code_insee_quartier,
--     prix_m2_median,
--     prix_m2_moyen,
--     nb_ventes,
--     nb_ventes_estime,
--     surface_quartier_m2,
--     part_surface
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/gold/kpi_prix_m2_quartier_annuel.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

COMMIT;
