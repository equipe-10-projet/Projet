#!/usr/bin/env python3
"""
Script Python pour importer les données d'INFLATION et OPEC vers MySQL
- Table 1: inflation_categories (catégories en lignes × années en colonnes)
- Table 2: opec_prix_annuel (années en lignes × attributs en colonnes)
"""

import json
import sys
from pathlib import Path
import os

DATA_FOLDER = 'data'

# Essayer d'importer mysql.connector
try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️  Module mysql-connector-python non installé")
    print("   Installation: pip install mysql-connector-python --break-system-packages")

# Configuration de la base de données
DB_CONFIG = {
    'host': 'localhost',
    'database': 'economic_dashboard',
    'user': 'root',
    'password': 'pass_root'
}

def load_inflation_data(file_path):
    """Charger les données d'inflation depuis le JSON"""
    
    print(f"\n📖 Lecture du fichier JSON INFLATION: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"   ✓ {len(data)} catégories chargées")
        return data
    
    except FileNotFoundError:
        print(f"   ✗ Fichier non trouvé: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"   ✗ Erreur de décodage JSON: {e}")
        return None

def load_opec_data(file_path):
    """Charger les données OPEC depuis le JSON"""
    
    print(f"\n📖 Lecture du fichier JSON OPEC: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"   ✓ {len(data)} années chargées")
        return data
    
    except FileNotFoundError:
        print(f"   ✗ Fichier non trouvé: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"   ✗ Erreur de décodage JSON: {e}")
        return None

def load_pib_data(file_path):
    """Charger les données du PIB depuis le JSON"""
    
    print(f"\n📖 Lecture du fichier JSON PIB: {file_path.name}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"   ✓ {len(data)} secteurs chargés")
        return data
    
    except FileNotFoundError:
        print(f"   ✗ Fichier non trouvé: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"   ✗ Erreur de décodage JSON: {e}")
        return None

def analyze_pib_data(data):
    """Analyser les données du PIB"""
    
    if not data:
        return None
    
    # Extraire le PIB global (dernière ligne)
    pib_global = data[-1]
    
    # Extraire années et valeurs
    annees = []
    valeurs = []
    
    for key, value in pib_global.items():
        if key != "Secteur d'activité" and key.isdigit():
            annees.append(key)
            try:
                valeurs.append(float(value))
            except:
                valeurs.append(0)
    
    # Calculer statistiques
    moyenne = sum(valeurs) / len(valeurs) if valeurs else 0
    maximum = max(valeurs) if valeurs else 0
    minimum = min(valeurs) if valeurs else 0
    
    return {
        'annees': annees,
        'valeurs': valeurs,
        'moyenne': round(moyenne, 2),
        'maximum': round(maximum, 2),
        'minimum': round(minimum, 2),
        'first_year': annees[0] if annees else None,
        'last_year': annees[-1] if annees else None,
        'last_value': valeurs[-1] if valeurs else None,
        'total_years': len(annees)
    }

def analyze_secteurs():
    """Analyser les données par secteur"""
    data = load_pib_data()
    
    if not data:
        return []
    
    secteurs = []
    
    for item in data[:-1]:  # Exclure le PIB global
        secteur_name = item.get("Secteur d'activité", "Inconnu")
        
        # Calculer la moyenne du secteur
        valeurs = []
        for key, value in item.items():
            if key != "Secteur d'activité" and key.isdigit():
                try:
                    valeurs.append(float(value))
                except:
                    pass
        
        if valeurs:
            moyenne = sum(valeurs) / len(valeurs)
            secteurs.append({
                'nom': secteur_name,
                'moyenne': round(moyenne, 2),
                'max': round(max(valeurs), 2),
                'min': round(min(valeurs), 2),
                'derniere_valeur': round(valeurs[-1], 2)
            })
    
    # Trier par moyenne décroissante
    secteurs.sort(key=lambda x: x['moyenne'], reverse=True)
    
    return secteurs

def analyze_evolution_secteur(secteur_name):
    """Analyser l'évolution d'un secteur spécifique"""
    data = load_pib_data()
    
    if not data:
        return None
    
    # Trouver le secteur
    secteur_data = None
    for item in data:
        if item.get("Secteur d'activité") == secteur_name:
            secteur_data = item
            break
    
    if not secteur_data:
        return None
    
    # Extraire les données
    annees = []
    valeurs = []
    
    for key, value in secteur_data.items():
        if key != "Secteur d'activité" and key.isdigit():
            annees.append(key)
            try:
                valeurs.append(float(value))
            except:
                valeurs.append(0)
    
    return {
        'secteur': secteur_name,
        'annees': annees,
        'valeurs': valeurs
    }
def extract_years(data):
    """Extraire la liste des années du JSON inflation"""
    
    annees = set()
    for groupe_data in data:
        for key in groupe_data.keys():
            if key != 'groupe' and key.isdigit():
                annees.add(int(key))
    
    return sorted(annees)

def extract_pib_years(data):
    """Extraire la liste des années du JSON PIB"""
    
    annees = set()
    for secteur_data in data:
        for key in secteur_data.keys():
            if key != "Secteur d'activité" and key.isdigit():
                annees.add(int(key))
    
    return sorted(annees)

def create_connection():
    """Créer une connexion à MySQL"""
    
    if not MYSQL_AVAILABLE:
        print("\n✗ mysql-connector-python n'est pas installé")
        print("   Exécutez: pip install mysql-connector-python --break-system-packages")
        return None
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✓ Connecté à MySQL Server version {db_info}")
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            db_name = cursor.fetchone()
            print(f"✓ Base de données active: {db_name[0]}")
            cursor.close()
            return connection
    except Error as e:
        print(f"✗ Erreur de connexion à MySQL: {e}")
        print("\n💡 Vérifiez les paramètres de connexion dans DB_CONFIG:")
        print(f"   - Host: {DB_CONFIG['host']}")
        print(f"   - Database: {DB_CONFIG['database']}")
        print(f"   - User: {DB_CONFIG['user']}")
        return None

def create_inflation_table(connection, annees):
    """Créer la table inflation_categories avec colonnes dynamiques pour les années"""
    
    cursor = connection.cursor()
    
    try:
        print("\n🔨 Création de la table INFLATION...")
        
        # Supprimer la table si elle existe
        cursor.execute("DROP TABLE IF EXISTS inflation_categories")
        print("   ✓ Ancienne table supprimée (si existante)")
        
        # Créer les colonnes pour chaque année
        colonnes_annees = []
        for annee in annees:
            colonnes_annees.append(
                f"    annee_{annee} DECIMAL(10, 2) COMMENT 'Taux d\\'inflation en {annee}'"
            )
        
        create_table_query = f"""
        CREATE TABLE inflation_categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            categorie VARCHAR(255) NOT NULL UNIQUE COMMENT 'Nom de la catégorie d\\'inflation',
{','.join([chr(10) + col for col in colonnes_annees])},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_categorie (categorie)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_query)
        connection.commit()
        print(f"   ✓ Table 'inflation_categories' créée")
        print(f"   ✓ Structure: 1 colonne 'categorie' + {len(annees)} colonnes d'années")
        
    except Error as e:
        print(f"   ✗ Erreur lors de la création de la table: {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()

def create_opec_table(connection):
    """Créer la table opec_prix_annuel (années en lignes, attributs en colonnes)"""
    
    cursor = connection.cursor()
    
    try:
        print("\n🔨 Création de la table OPEC...")
        
        # Supprimer la table si elle existe
        cursor.execute("DROP TABLE IF EXISTS opec_prix_annuel")
        print("   ✓ Ancienne table supprimée (si existante)")
        
        create_table_query = """
        CREATE TABLE opec_prix_annuel (
            id INT AUTO_INCREMENT PRIMARY KEY,
            annee INT NOT NULL UNIQUE COMMENT 'Année',
            prix_moyen DECIMAL(10, 2) COMMENT 'Prix moyen annuel (USD/baril)',
            prix_min DECIMAL(10, 2) COMMENT 'Prix minimum de l\\'année',
            prix_max DECIMAL(10, 2) COMMENT 'Prix maximum de l\\'année',
            nb_jours INT COMMENT 'Nombre de jours de cotation',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_annee (annee)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_query)
        connection.commit()
        print(f"   ✓ Table 'opec_prix_annuel' créée")
        print(f"   ✓ Structure: années en LIGNES × attributs en COLONNES")
        
    except Error as e:
        print(f"   ✗ Erreur lors de la création de la table: {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()

def create_pib_table(connection, annees):
    """Créer la table pib_secteurs avec colonnes dynamiques pour les années"""
    
    cursor = connection.cursor()
    
    try:
        print("\n🔨 Création de la table PIB...")
        
        # Supprimer la table si elle existe
        cursor.execute("DROP TABLE IF EXISTS pib_secteurs")
        print("   ✓ Ancienne table supprimée (si existante)")
        
        # Créer les colonnes pour chaque année
        colonnes_annees = []
        for annee in annees:
            colonnes_annees.append(
                f"    annee_{annee} DECIMAL(10, 2) COMMENT 'PIB secteur en {annee} (%)'"
            )
        
        create_table_query = f"""
        CREATE TABLE pib_secteurs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            secteur VARCHAR(255) NOT NULL UNIQUE COMMENT 'Nom du secteur d\\'activité',
{','.join([chr(10) + col for col in colonnes_annees])},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_secteur (secteur)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_query)
        connection.commit()
        print(f"   ✓ Table 'pib_secteurs' créée")
        print(f"   ✓ Structure: 1 colonne 'secteur' + {len(annees)} colonnes d'années")
        
    except Error as e:
        print(f"   ✗ Erreur lors de la création de la table: {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()

def insert_inflation_data(connection, data, annees):
    """Insérer les données d'inflation"""
    
    cursor = connection.cursor()
    
    try:
        print("\n📊 Insertion des données d'INFLATION...")
        
        # Construire la requête d'insertion
        colonnes = ['categorie'] + [f'annee_{annee}' for annee in annees]
        colonnes_str = ', '.join(colonnes)
        placeholders = ', '.join(['%s'] * len(colonnes))
        
        insert_query = f"""
        INSERT INTO inflation_categories ({colonnes_str})
        VALUES ({placeholders})
        """
        
        total_inserted = 0
        
        for groupe_data in data:
            categorie = groupe_data['groupe']
            
            # Créer le tuple de valeurs
            values = [categorie]
            for annee in annees:
                valeur = groupe_data.get(str(annee))
                values.append(valeur)
            
            cursor.execute(insert_query, tuple(values))
            total_inserted += 1
            print(f"   ✓ {categorie}")
        
        connection.commit()
        print(f"\n✓ {total_inserted} catégories d'inflation insérées")
        
    except Error as e:
        print(f"\n✗ Erreur lors de l'insertion des données: {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()

def insert_opec_data(connection, data):
    """Insérer les données OPEC"""
    
    cursor = connection.cursor()
    
    try:
        print("\n📊 Insertion des données OPEC...")
        
        insert_query = """
        INSERT INTO opec_prix_annuel (annee, prix_moyen, prix_min, prix_max, nb_jours)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        total_inserted = 0
        
        for item in data:
            values = (
                item['annee'],
                item['prix_moyen'],
                item['prix_min'],
                item['prix_max'],
                item['nb_jours']
            )
            
            cursor.execute(insert_query, values)
            total_inserted += 1
            print(f"   ✓ {item['annee']}: ${item['prix_moyen']}/baril")
        
        connection.commit()
        print(f"\n✓ {total_inserted} années de prix OPEC insérées")
        
    except Error as e:
        print(f"\n✗ Erreur lors de l'insertion des données: {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()

def insert_pib_data(connection, data, annees):
    """Insérer les données du PIB"""
    
    cursor = connection.cursor()
    
    try:
        print("\n📊 Insertion des données du PIB...")
        
        # Construire la requête d'insertion
        colonnes = ['secteur'] + [f'annee_{annee}' for annee in annees]
        colonnes_str = ', '.join(colonnes)
        placeholders = ', '.join(['%s'] * len(colonnes))
        
        insert_query = f"""
        INSERT INTO pib_secteurs ({colonnes_str})
        VALUES ({placeholders})
        """
        
        total_inserted = 0
        
        for secteur_data in data:
            secteur_name = secteur_data.get('Secteur d\'activité', 'Secteur inconnu')
            
            # Préparer les valeurs pour chaque année
            values = [secteur_name]
            for annee in annees:
                valeur_str = secteur_data.get(str(annee), '0')
                try:
                    valeur = float(valeur_str) if valeur_str else 0.0
                except (ValueError, TypeError):
                    valeur = 0.0
                values.append(valeur)
            
            cursor.execute(insert_query, values)
            total_inserted += 1
            print(f"   ✓ {secteur_name}")
        
        connection.commit()
        print(f"\n✓ {total_inserted} secteurs du PIB insérés")
        
    except Error as e:
        print(f"\n✗ Erreur lors de l'insertion des données: {e}")
        connection.rollback()
        raise
    finally:
        cursor.close()

def verify_tables(connection):
    """Vérifier les données insérées dans les deux tables"""
    
    cursor = connection.cursor()
    
    try:
        print("\n" + "="*100)
        print("🔍 VÉRIFICATION DES DONNÉES")
        print("="*100)
        
        # Table inflation
        cursor.execute("SELECT COUNT(*) FROM inflation_categories")
        count_inflation = cursor.fetchone()[0]
        print(f"\n📊 Table INFLATION_CATEGORIES: {count_inflation} catégories")
        
        cursor.execute("SELECT categorie FROM inflation_categories LIMIT 3")
        print("   Exemples:")
        for row in cursor.fetchall():
            print(f"   - {row[0]}")
        
        # Table OPEC
        cursor.execute("SELECT COUNT(*) FROM opec_prix_annuel")
        count_opec = cursor.fetchone()[0]
        print(f"\n📊 Table OPEC_PRIX_ANNUEL: {count_opec} années")
        
        cursor.execute("""
            SELECT annee, prix_moyen, prix_min, prix_max 
            FROM opec_prix_annuel 
            ORDER BY annee DESC 
            LIMIT 5
        """)
        print("   Dernières années:")
        print(f"   {'Année':<8} {'Prix Moyen':<12} {'Min':<10} {'Max':<10}")
        print("   " + "-" * 50)
        for row in cursor.fetchall():
            print(f"   {row[0]:<8} ${row[1]:<11.2f} ${row[2]:<9.2f} ${row[3]:<9.2f}")
        
        # Table PIB
        cursor.execute("SELECT COUNT(*) FROM pib_secteurs")
        count_pib = cursor.fetchone()[0]
        print(f"\n📊 Table PIB_SECTEURS: {count_pib} secteurs")
        
        cursor.execute("SELECT secteur FROM pib_secteurs LIMIT 3")
        print("   Exemples:")
        for row in cursor.fetchall():
            print(f"   - {row[0]}")
        
    except Error as e:
        print(f"✗ Erreur: {e}")
    finally:
        cursor.close()

def display_sample_queries():
    """Afficher des exemples de requêtes SQL"""
    
    print("\n" + "="*100)
    print("💡 EXEMPLES DE REQUÊTES SQL")
    print("="*100)
    
    print("\n🔹 INFLATION:")
    print("-" * 100)
    print("""
-- Voir l'IPC Global
SELECT * FROM inflation_categories WHERE categorie = 'IPC GLOBAL';

-- Comparer 2020 vs 2023
SELECT categorie, annee_2020, annee_2023,
       ROUND(annee_2023 - annee_2020, 2) AS evolution
FROM inflation_categories
ORDER BY evolution DESC;
""")
    
    print("\n🔹 OPEC:")
    print("-" * 100)
    print("""
-- Voir toutes les années
SELECT * FROM opec_prix_annuel ORDER BY annee;

-- Prix moyen par décennie
SELECT 
    CASE 
        WHEN annee BETWEEN 2003 AND 2009 THEN '2003-2009'
        WHEN annee BETWEEN 2010 AND 2019 THEN '2010-2019'
        WHEN annee BETWEEN 2020 AND 2029 THEN '2020-2029'
    END AS decennie,
    ROUND(AVG(prix_moyen), 2) AS prix_moyen
FROM opec_prix_annuel
GROUP BY decennie;

-- Années avec prix > 100 USD
SELECT annee, prix_moyen
FROM opec_prix_annuel
WHERE prix_moyen > 100
ORDER BY annee DESC;
""")
    
    print("\n🔹 PIB:")
    print("-" * 100)
    print("""
-- Voir le PIB global
SELECT * FROM pib_secteurs WHERE secteur LIKE '%Produit Intérieur Brut%';

-- Évolution du PIB par secteur (2020-2024)
SELECT secteur, annee_2020, annee_2021, annee_2022, annee_2023, annee_2024
FROM pib_secteurs
ORDER BY annee_2024 DESC;

-- Secteurs avec croissance > 5% en 2024
SELECT secteur, annee_2024
FROM pib_secteurs
WHERE annee_2024 > 5
ORDER BY annee_2024 DESC;
""")
    
    print("\n🔹 ANALYSE COMBINÉE (Inflation × Prix Pétrole):")
    print("-" * 100)
    print("""
-- Corrélation Inflation vs Prix du Pétrole (2018-2025)
SELECT 
    o.annee,
    o.prix_moyen AS prix_petrole,
    i.annee_2018, i.annee_2019, i.annee_2020, i.annee_2021,
    i.annee_2022, i.annee_2023, i.annee_2024, i.annee_2025
FROM opec_prix_annuel o
CROSS JOIN inflation_categories i
WHERE i.categorie = 'IPC GLOBAL'
  AND o.annee >= 2018
ORDER BY o.annee;

-- Comparaison 2020 (COVID) vs 2022 (Guerre Ukraine)
SELECT 
    'Pétrole' AS indicateur,
    '2020' AS annee,
    prix_moyen AS valeur
FROM opec_prix_annuel WHERE annee = 2020
UNION ALL
SELECT 
    'Pétrole' AS indicateur,
    '2022' AS annee,
    prix_moyen AS valeur
FROM opec_prix_annuel WHERE annee = 2022
UNION ALL
SELECT 
    'Inflation' AS indicateur,
    '2020' AS annee,
    annee_2020 AS valeur
FROM inflation_categories WHERE categorie = 'IPC GLOBAL'
UNION ALL
SELECT 
    'Inflation' AS indicateur,
    '2022' AS annee,
    annee_2022 AS valeur
FROM inflation_categories WHERE categorie = 'IPC GLOBAL';
""")

def main():
    """Fonction principale"""
    
    print("="*100)
    print("🗄️  IMPORT DES DONNÉES ÉCONOMIQUES VERS MYSQL")
    print("   → Table 1: INFLATION (catégories en lignes × années en colonnes)")
    print("   → Table 2: OPEC (années en lignes × attributs en colonnes)")
    print("   → Table 3: PIB (secteurs en lignes × années en colonnes)")
    print("="*100)
    print()
    
    # Chemins des fichiers JSON
    script_dir = Path(__file__).parent
    inflation_file = script_dir / 'data' / 'inflation_annuelle_2004_2025.json'
    
    opec_file = script_dir / 'data' / 'opec_prix_annuel_complet.json'
    
    pib_file = script_dir / 'data' / 'pib_data.json'
    
    # Vérifier l'existence des fichiers
    if not inflation_file.exists():
        print(f"\n✗ Fichier INFLATION non trouvé: {inflation_file}")
        print("\n💡 Assurez-vous d'avoir le fichier 'inflation_annuelle_2004_2025.json' dans le dossier 'data'")
        return 1
    
    if not opec_file.exists():
        print(f"\n✗ Fichier OPEC non trouvé: {opec_file}")
        print("\n💡 Assurez-vous d'avoir le fichier 'opec_prix_annuel_complet.json' dans le dossier 'data'")
        return 1
    
    if not pib_file.exists():
        print(f"\n✗ Fichier PIB non trouvé: {pib_file}")
        print("\n💡 Assurez-vous d'avoir le fichier 'pib_data.json' dans le dossier 'data'")
        return 1
    
    # Charger les données
    inflation_data = load_inflation_data(inflation_file)
    opec_data = load_opec_data(opec_file)
    pib_data = load_pib_data(pib_file)
    
    if not inflation_data or not opec_data or not pib_data:
        print("\n✗ Erreur lors du chargement des données")
        return 1
    
    # Extraire les années
    inflation_annees = extract_years(inflation_data)
    pib_annees = extract_pib_years(pib_data)
    print(f"\n✓ Années INFLATION: {inflation_annees[0]} - {inflation_annees[-1]} ({len(inflation_annees)} années)")
    print(f"✓ Années OPEC: {opec_data[0]['annee']} - {opec_data[-1]['annee']} ({len(opec_data)} années)")
    print(f"✓ Années PIB: {pib_annees[0]} - {pib_annees[-1]} ({len(pib_annees)} années)")
    
    # Se connecter à MySQL
    print("\n🔌 Connexion à MySQL...")
    connection = create_connection()
    
    if not connection:
        print("\n⚠️  Impossible de se connecter à MySQL")
        print("\n📝 Vérifiez et modifiez les paramètres de connexion dans le script:")
        print("   DB_CONFIG = {")
        print(f"       'host': '{DB_CONFIG['host']}',")
        print(f"       'database': '{DB_CONFIG['database']}',")
        print(f"       'user': '{DB_CONFIG['user']}',")
        print(f"       'password': '{DB_CONFIG['password']}'")
        print("   }")
        return 1
    
    try:
        # Créer les tables
        create_inflation_table(connection, inflation_annees)
        create_opec_table(connection)
        create_pib_table(connection, pib_annees)
        
        # Insérer les données
        insert_inflation_data(connection, inflation_data, inflation_annees)
        insert_opec_data(connection, opec_data)
        insert_pib_data(connection, pib_data, pib_annees)
        
        # Vérifier les données
        verify_tables(connection)
        
        # Afficher des exemples de requêtes
        display_sample_queries()
        
        print("\n" + "="*100)
        print("✅ IMPORT TERMINÉ AVEC SUCCÈS!")
        print("="*100)
        print(f"\n📊 Tables créées:")
        print(f"   1. inflation_categories ({len(inflation_data)} catégories × {len(inflation_annees)} années)")
        print(f"   2. opec_prix_annuel ({len(opec_data)} années × 4 attributs)")
        print(f"   3. pib_secteurs ({len(pib_data)} secteurs × {len(pib_annees)} années)")
        print("\n💡 Vous pouvez maintenant interroger les tables avec les requêtes SQL ci-dessus")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if connection and connection.is_connected():
            connection.close()
            print("\n🔌 Connexion MySQL fermée")

if __name__ == '__main__':
    sys.exit(main())