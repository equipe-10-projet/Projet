"""Import automatique des données dans MySQL"""
import mysql.connector
import json

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pass_root',
    'database': 'economic_dashboard'
}

def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except:
        return None

def import_data():
    """Importer toutes les données dans MySQL (recrée la DB à chaque fois)"""
    print("\n=== Import données ===")
    
    try:
        # Détruire et recréer la DB
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='pass_root'
        )
        cursor = conn.cursor()
        cursor.execute("DROP DATABASE IF EXISTS economic_dashboard")
        print("✓ Ancienne base supprimée")
        cursor.execute("CREATE DATABASE economic_dashboard")
        print("✓ Nouvelle base créée")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erreur création DB: {e}")
        return False
    
    conn = get_db()
    if not conn:
        print("Erreur connexion MySQL")
        return False
    
    cursor = conn.cursor()
    
    try:
        # INFLATION
        with open('data/inflation_annuelle_2004_2025.json', 'r', encoding='utf-8') as f:
            inflation_data = json.load(f)
        
        cursor.execute("DROP TABLE IF EXISTS inflation")
        cursor.execute("""
            CREATE TABLE inflation (
                id INT AUTO_INCREMENT PRIMARY KEY,
                annee INT,
                valeur DECIMAL(10,2)
            )
        """)
        
        ipc_global = [d for d in inflation_data if d['groupe'] == 'IPC GLOBAL'][0]
        for year in range(2004, 2026):
            if str(year) in ipc_global:
                cursor.execute(
                    "INSERT INTO inflation (annee, valeur) VALUES (%s, %s)",
                    (year, ipc_global[str(year)])
                )
        print("✓ Inflation")
        
        # OPEC
        with open('data/opec_prix_annuel_complet.json', 'r', encoding='utf-8') as f:
            opec_data = json.load(f)
        
        cursor.execute("DROP TABLE IF EXISTS opec")
        cursor.execute("""
            CREATE TABLE opec (
                id INT AUTO_INCREMENT PRIMARY KEY,
                annee INT,
                valeur DECIMAL(10,2)
            )
        """)
        
        for row in opec_data:
            cursor.execute(
                "INSERT INTO opec (annee, valeur) VALUES (%s, %s)",
                (row['annee'], row['prix_moyen'])
            )
        print("✓ OPEC")
        
        # PIB
        with open('data/pib_data.json', 'r', encoding='utf-8') as f:
            pib_data = json.load(f)
        
        pib_global = pib_data[-1]
        
        cursor.execute("DROP TABLE IF EXISTS croissance_pib")
        cursor.execute("""
            CREATE TABLE croissance_pib (
                id INT AUTO_INCREMENT PRIMARY KEY,
                annee INT,
                valeur DECIMAL(10,2)
            )
        """)
        
        for year in range(2002, 2025):
            if str(year) in pib_global:
                cursor.execute(
                    "INSERT INTO croissance_pib (annee, valeur) VALUES (%s, %s)",
                    (year, float(pib_global[str(year)]))
                )
        print("✓ PIB")
        
        # PIB SECTEURS
        cursor.execute("DROP TABLE IF EXISTS pib_secteurs")
        
        annees = [str(y) for y in range(2002, 2025)]
        cols = ", ".join([f"annee_{y} DECIMAL(10,2)" for y in annees])
        
        cursor.execute(f"""
            CREATE TABLE pib_secteurs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                secteur VARCHAR(255),
                {cols}
            )
        """)
        
        for secteur_data in pib_data[:-1]:
            secteur_name = secteur_data.get("Secteur d'activité", "Inconnu")
            valeurs = [secteur_data.get(str(y), 0) for y in range(2002, 2025)]
            
            placeholders = ", ".join(["%s"] * (len(annees) + 1))
            cursor.execute(
                f"INSERT INTO pib_secteurs (secteur, {', '.join([f'annee_{y}' for y in annees])}) VALUES ({placeholders})",
                [secteur_name] + valeurs
            )
        print("✓ Secteurs")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Import terminé\n")
        return True
        
    except Exception as e:
        print(f"Erreur import: {e}")
        return False
