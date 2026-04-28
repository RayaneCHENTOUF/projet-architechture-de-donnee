-- Geographic reference tables
-- Source CSVs:
--   data/silver/commun/arrondissements_clean.csv
--   data/silver/commun/iris_clean.csv
--   data/silver/commun/quartiers_clean.csv

BEGIN;

CREATE TABLE IF NOT EXISTS dim_geo_arrondissements (
    identifiant_sequentiel_de_l_arrondissement BIGINT,
    numero_d_arrondissement INTEGER,
    numero_d_arrondissement_insee VARCHAR(10),
    nom_de_l_arrondissement TEXT,
    nom_officiel_de_l_arrondissement TEXT,
    n_sq_co BIGINT,
    surface NUMERIC(20,6),
    perimetre NUMERIC(20,6),
    geometry_x_y TEXT,
    geometry TEXT,
    arrondissement VARCHAR(2),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (numero_d_arrondissement_insee)
);

CREATE TABLE IF NOT EXISTS dim_geo_iris (
    insee_com VARCHAR(10),
    code_iris VARCHAR(10) NOT NULL,
    nom_iris TEXT,
    geo_point TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (code_iris)
);

CREATE TABLE IF NOT EXISTS dim_geo_quartier_paris (
    arrondissement VARCHAR(2),
    code_quartier_id INTEGER,
    code_insee_quartier VARCHAR(7) NOT NULL,
    nom_quartier TEXT,
    surface_quartier_m2 NUMERIC(20,6),
    geometry_xy TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (code_insee_quartier)
);

-- COPY dim_geo_arrondissements (
--     identifiant_sequentiel_de_l_arrondissement,
--     numero_d_arrondissement,
--     numero_d_arrondissement_insee,
--     nom_de_l_arrondissement,
--     nom_officiel_de_l_arrondissement,
--     n_sq_co,
--     surface,
--     perimetre,
--     geometry_x_y,
--     geometry,
--     arrondissement
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/silver/commun/arrondissements_clean.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- COPY dim_geo_iris (
--     insee_com,
--     code_iris,
--     nom_iris,
--     geo_point
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/silver/commun/iris_clean.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- COPY dim_geo_quartier_paris (
--     arrondissement,
--     code_quartier_id,
--     code_insee_quartier,
--     nom_quartier,
--     surface_quartier_m2,
--     geometry_xy
-- )
-- FROM 'C:/Users/rayan/Desktop/efrei/projet-data-dev/data/silver/commun/quartiers_clean.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

COMMIT;
