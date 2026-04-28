import subprocess
import sys
import time
from pathlib import Path

def run_script(script_name):
    """Exécute un script python et gère l'affichage"""
    print(f"\n>>> Lancement de : {script_name}")
    start_time = time.time()
    try:
        # On lance le script dans un processus séparé
        result = subprocess.run([sys.executable, script_name], capture_output=True, text=True, check=True)
        print(result.stdout)
        duration = time.time() - start_time
        print(f"OK - Terminé en {duration:.2f}s")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERREUR lors de l'exécution de {script_name}")
        print(e.stderr)
        return False

def main():
    print("====================================================")
    print("   LANCEMENT DU PIPELINE DE NETTOYAGE (SILVER)      ")
    print("====================================================\n")
    
    # Liste des scripts dans l'ordre logique d'exécution
    scripts = [
        "clean_geographie.py",  # Référentiels de base
        "clean_immobilier.py",
        "clean_surete.py",
        "clean_confort.py"
    ]
    
    base_path = Path(__file__).parent
    results = {}
    
    for script in scripts:
        script_path = base_path / script
        if script_path.exists():
            success = run_script(str(script_path))
            results[script] = "SUCCÈS" if success else "ÉCHEC"
        else:
            print(f"Fichier introuvable : {script}")
            results[script] = "INTROUVABLE"

    print("\n" + "="*50)
    print("RÉSUMÉ DU NETTOYAGE :")
    for script, status in results.items():
        print(f" - {script:25} : {status}")
    print("="*50)

if __name__ == "__main__":
    main()
