import os
from pathlib import Path

# Définition de la racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Chemins vers les dossiers de données
DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

# S'assurer que les dossiers existent
for d in [BRONZE_DIR, SILVER_DIR, GOLD_DIR]:
    d.mkdir(parents=True, exist_ok=True)