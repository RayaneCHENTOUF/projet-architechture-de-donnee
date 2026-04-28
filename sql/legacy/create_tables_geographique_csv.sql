-- Geographic CSV tables (bronze/commun)
-- PostgreSQL DDL
-- One table per geographic CSV file.

BEGIN;

CREATE TABLE IF NOT EXISTS dim_geo_arrondissements (
    identifiant_sequentiel_arrondissement BIGINT,
    numero_arrondissement VARCHAR(4),
    numero_arrondissement_insee VARCHAR(10),
    nom_arrondissement TEXT,
    nom_officiel_arrondissement TEXT,
    n_sq_co BIGINT,
    surface NUMERIC(20,6),
    perimetre NUMERIC(20,6),
    geometry_xy TEXT,
    geometry_geojson TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (numero_arrondissement_insee)
);

CREATE TABLE IF NOT EXISTS dim_geo_iris (
    geo_shape TEXT,
    dep VARCHAR(3),
    insee_com VARCHAR(10),
    nom_com TEXT,
    iris VARCHAR(10),
    code_iris VARCHAR(9),
    nom_iris TEXT,
    typ_iris VARCHAR(30),
    geo_point TEXT,
    id TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (code_iris)
);

CREATE TABLE IF NOT EXISTS dim_geo_quartier_paris (
    n_sq_qu BIGINT,
    c_qu INTEGER,
    c_quinsee VARCHAR(10),
    l_qu TEXT,
    c_ar VARCHAR(4),
    n_sq_ar BIGINT,
    perimetre NUMERIC(20,6),
    surface NUMERIC(20,6),
    geometry_xy TEXT,
    geometry_geojson TEXT,
    st_area_shape NUMERIC(20,6),
    st_perimeter_shape NUMERIC(20,6),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (c_quinsee)
);

COMMIT;

-- --------------------------------------------------
-- COPY examples (adapt absolute paths if needed)
-- --------------------------------------------------
-- All bronze/commun CSV files use ';' delimiter.

-- COPY dim_geo_arrondissements (
--     identifiant_sequentiel_arrondissement,
--     numero_arrondissement,
--     numero_arrondissement_insee,
--     nom_arrondissement,
--     nom_officiel_arrondissement,
--     n_sq_co,
--     surface,
--     perimetre,
--     geometry_xy,
--     geometry_geojson
-- )
-- FROM '/absolute/path/data/bronze/commun/arrondissements.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');

-- COPY dim_geo_iris (
--     geo_shape, dep, insee_com, nom_com, iris,
--     code_iris, nom_iris, typ_iris, geo_point, id
-- )
-- FROM '/absolute/path/data/bronze/commun/iris.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');

-- COPY dim_geo_quartier_paris (
--     n_sq_qu, c_qu, c_quinsee, l_qu, c_ar, n_sq_ar,
--     perimetre, surface, geometry_xy, geometry_geojson,
--     st_area_shape, st_perimeter_shape
-- )
-- FROM '/absolute/path/data/bronze/commun/quartier_paris.csv'
-- WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');
