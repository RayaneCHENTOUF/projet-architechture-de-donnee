import json
import random
import mysql.connector

def create_mock_data():
    # 1. Read GeoJSON to get quartiers
    with open('Front/public/data/exports/nosql/quartiers.geojson', 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    
    quartiers = geojson.get('features', [])
    print(f"Loaded {len(quartiers)} quartiers from GeoJSON.")
    
    # 2. Connect to MySQL
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="dbl2025",
        database="urban_data"
    )
    cursor = conn.cursor()
    
    # 3. Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fact_kpi_confort_quartier (
        arrondissement VARCHAR(2) NOT NULL,
        code_insee_quartier VARCHAR(10) NOT NULL,
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
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fact_kpi_surete_quartier (
        annee INTEGER NOT NULL,
        arrondissement VARCHAR(2) NOT NULL,
        code_insee_quartier VARCHAR(10) NOT NULL,
        score_surete_quartier_moyen_100 NUMERIC(10,3),
        score_risque_quartier_moyen_100 NUMERIC(10,3),
        score_surete_iris_min_100 NUMERIC(10,3),
        score_surete_iris_max_100 NUMERIC(10,3),
        score_surete_iris_std_100 NUMERIC(10,3),
        score_risque_iris_min_100 NUMERIC(10,3),
        score_risque_iris_max_100 NUMERIC(10,3),
        score_risque_iris_std_100 NUMERIC(10,3),
        nb_iris_rattaches INTEGER,
        codes_iris_rattaches TEXT,
        noms_iris_rattaches TEXT,
        dist_commissariat_km_moyenne NUMERIC(10,3),
        nb_cameras_arrondissement INTEGER,
        source_file TEXT,
        loaded_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (annee, code_insee_quartier)
    )
    """)
    
    # 4. Insert mock data
    cursor.execute("TRUNCATE TABLE fact_kpi_confort_quartier")
    cursor.execute("TRUNCATE TABLE fact_kpi_surete_quartier")
    
    for feature in quartiers:
        props = feature.get('properties', {})
        code_insee = str(props.get('c_quinsee', ''))
        nom = props.get('l_qu', '')
        arr = str(props.get('c_ar', ''))
        
        # Confort
        score_confort = random.uniform(30, 95)
        cursor.execute("""
            INSERT INTO fact_kpi_confort_quartier 
            (arrondissement, code_insee_quartier, nom_quartier, score_confort_urbain_100)
            VALUES (%s, %s, %s, %s)
        """, (arr, code_insee, nom, score_confort))
        
        # Surete
        score_surete = random.uniform(40, 90)
        cursor.execute("""
            INSERT INTO fact_kpi_surete_quartier 
            (annee, arrondissement, code_insee_quartier, score_surete_quartier_moyen_100, score_risque_quartier_moyen_100)
            VALUES (%s, %s, %s, %s, %s)
        """, (2023, arr, code_insee, score_surete, 100 - score_surete))
        
    conn.commit()
    cursor.close()
    conn.close()
    print("Mock data successfully inserted into MySQL!")

if __name__ == '__main__':
    create_mock_data()
