-- Consolidated Gold tables for Urban Data Explorer
-- PostgreSQL reference DDL (Phase 2)

BEGIN;

-- KPI prix m2 arrondissement
CREATE TABLE IF NOT EXISTS fact_kpi_prix_m2_arrondissement (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    prix_m2_median NUMERIC(14,2),
    prix_m2_moyen NUMERIC(14,2),
    nb_transactions INTEGER,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, arrondissement)
);

-- KPI surete agrege arrondissement
CREATE TABLE IF NOT EXISTS fact_kpi_surete_arrondissement (
    annee INTEGER NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    score_surete_zone_moyen_100 NUMERIC(6,3),
    score_risque_zone_moyen_100 NUMERIC(6,3),
    nb_iris INTEGER,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, arrondissement)
);

-- KPI surete detail IRIS
CREATE TABLE IF NOT EXISTS fact_kpi_surete_iris (
    annee INTEGER NOT NULL,
    code_iris VARCHAR(9) NOT NULL,
    nom_iris TEXT,
    arrondissement VARCHAR(2),
    lat NUMERIC(10,7),
    lon NUMERIC(10,7),
    score_risque_delinq_100 NUMERIC(6,3),
    score_surete_delinq_100 NUMERIC(6,3),
    nb_cameras INTEGER,
    camera_risk_100 NUMERIC(6,3),
    dist_commissariat_km NUMERIC(8,4),
    commissariat_risk_100 NUMERIC(6,3),
    score_risque_final_100 NUMERIC(6,3),
    score_surete_final_100 NUMERIC(6,3),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (annee, code_iris)
);

-- KPI comparaison achat/location
CREATE TABLE IF NOT EXISTS fact_kpi_comparaison_achat_location (
    arrondissement VARCHAR(2) NOT NULL,
    prix_m2_median_2021 NUMERIC(14,2),
    prix_m2_median_2025 NUMERIC(14,2),
    loyer_reference_median_2021 NUMERIC(14,2),
    loyer_reference_median_2025 NUMERIC(14,2),
    kpi_comparaison_achat_location_2021 NUMERIC(14,6),
    kpi_comparaison_achat_location_2025 NUMERIC(14,6),
    evolution_achat_pct NUMERIC(14,6),
    evolution_loyer_pct NUMERIC(14,6),
    evolution_kpi_comparaison_pct NUMERIC(14,6),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (arrondissement)
);

-- KPI confort quartier
CREATE TABLE IF NOT EXISTS fact_kpi_confort_quartier (
    code_quartier INTEGER NOT NULL,
    code_insee_quartier VARCHAR(10) NOT NULL,
    code_postal_arr VARCHAR(5),
    nom_quartier TEXT NOT NULL,
    arrondissement VARCHAR(2) NOT NULL,
    surface_m2 NUMERIC(18,2),
    lat_q NUMERIC(10,7),
    lon_q NUMERIC(10,7),
    s1_proprete NUMERIC(6,3),
    s2_incivilites NUMERIC(6,3),
    s3_amenagement NUMERIC(6,3),
    s4_accessibilite NUMERIC(6,3),
    s5_transport NUMERIC(6,3),
    kpi_confort_urbain NUMERIC(6,3),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (code_quartier)
);

-- KPI confort agrege arrondissement
CREATE TABLE IF NOT EXISTS fact_kpi_confort_arrondissement (
    arrondissement VARCHAR(2) NOT NULL,
    nb_quartiers INTEGER NOT NULL,
    surface_m2_totale NUMERIC(18,2),
    s1_proprete_moyen NUMERIC(6,3),
    s2_incivilites_moyen NUMERIC(6,3),
    s3_amenagement_moyen NUMERIC(6,3),
    s4_accessibilite_moyen NUMERIC(6,3),
    s5_transport_moyen NUMERIC(6,3),
    kpi_confort_urbain_moyen NUMERIC(6,3),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (arrondissement)
);

COMMIT;
