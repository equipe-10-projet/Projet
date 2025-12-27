from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import json
import os
import re
from JSON_to_DB import import_ALL

app = Flask(__name__)
CORS(app)

# Importer toutes les données au démarrage
import_ALL.main()

# Configuration MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pass_root',
    'database': 'economic_dashboard'
}

DATA_FOLDER = 'data'
os.makedirs(DATA_FOLDER, exist_ok=True)

# ========== UTILITAIRES ==========
def sanitize_name(name):
    """Nettoyer un nom pour MySQL"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()

def get_db_connection():
    """Créer une connexion à MySQL"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"❌ Erreur MySQL: {e}")
        return None

def detect_type(value):
    """Détecter le type de données"""
    if value is None:
        return 'TEXT'
    if isinstance(value, bool):
        return 'BOOLEAN'
    if isinstance(value, int):
        return 'INT'
    if isinstance(value, float):
        return 'DECIMAL(10, 2)'
    if isinstance(value, (dict, list)):
        return 'JSON'
    return 'TEXT'

def analyze_json(data):
    """Analyser la structure d'un JSON"""
    if not data:
        return {}
    
    sample = data[0] if isinstance(data, list) else data
    if not isinstance(sample, dict):
        return {}
    
    columns = {}
    for key, value in sample.items():
        col_name = sanitize_name(key)
        columns[col_name] = {'original': key, 'type': detect_type(value)}
    
    return columns

def create_table_from_json(conn, table_name, columns):
    """Créer une table à partir d'une structure JSON"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        
        col_definitions = [f"`{col}` {info['type']}" for col, info in columns.items()]
        col_definitions.insert(0, "id INT AUTO_INCREMENT PRIMARY KEY")
        
        create_query = f"CREATE TABLE `{table_name}` ({', '.join(col_definitions)})"
        cursor.execute(create_query)
        conn.commit()
        return True
    except Error as e:
        print(f"Erreur création table: {e}")
        return False
    finally:
        cursor.close()

def insert_json_to_table(conn, table_name, data, columns):
    """Insérer des données JSON dans une table"""
    cursor = conn.cursor()
    try:
        col_names = list(columns.keys())
        placeholders = ", ".join(["%s"] * len(col_names))
        insert_query = f"INSERT INTO `{table_name}` ({', '.join([f'`{c}`' for c in col_names])}) VALUES ({placeholders})"
        
        inserted = 0
        for row in data if isinstance(data, list) else [data]:
            values = []
            for col in col_names:
                original_key = columns[col]['original']
                value = row.get(original_key)
                values.append(value)
            
            cursor.execute(insert_query, values)
            inserted += 1
        
        conn.commit()
        return inserted
    except Error as e:
        print(f"Erreur insertion: {e}")
        return 0
    finally:
        cursor.close()

# ========== INITIALISATION ==========
def init_db():
    """Initialiser la base de données"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        print("✅ Base de données prête")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"❌ Erreur init: {e}")

def auto_import_json():
    """Importer automatiquement les fichiers JSON du dossier data"""
    json_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.json')]
    
    if not json_files:
        print(f"ℹ️ Aucun fichier JSON dans '{DATA_FOLDER}/'")
        return
    
    print(f"\n📦 Import: {len(json_files)} fichier(s) JSON\n")
    
    conn = get_db_connection()
    if not conn:
        return
    
    for filename in json_files:
        filepath = os.path.join(DATA_FOLDER, filename)
        try:
            print(f"📄 {filename}")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            columns = analyze_json(data)
            if not columns:
                print("   ⚠️ Structure invalide\n")
                continue
            
            row_count = len(data) if isinstance(data, list) else 1
            print(f"   📊 {row_count} lignes, {len(columns)} colonnes")
            
            table_name = sanitize_name(os.path.splitext(filename)[0])
            
            if not create_table_from_json(conn, table_name, columns):
                continue
            
            inserted = insert_json_to_table(conn, table_name, data, columns)
            print(f"   ✅ {inserted} lignes → table '{table_name}'\n")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}\n")
    
    conn.close()

# ========== API ==========
@app.route('/api/tables')
def get_tables():
    """Lister toutes les tables"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erreur connexion'}), 500
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return jsonify(tables)

@app.route('/api/table/<table_name>')
def get_table_data(table_name):
    """Récupérer les données d'une table"""
    table_name = sanitize_name(table_name)
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erreur connexion'}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT * FROM `{table_name}`")
        data = cursor.fetchall()
        
        for row in data:
            for key, value in row.items():
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    try:
                        row[key] = json.loads(value)
                    except:
                        pass
        
        return jsonify(data)
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/query/croissance-pib')
def query_croissance_pib():
    """Récupère les données de croissance du PIB par année"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erreur connexion'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Chercher la table pib_secteurs
        cursor.execute("SHOW TABLES")
        tables = [row[list(row.keys())[0]] for row in cursor.fetchall()]
        
        print(f"📋 Tables trouvées: {tables}")
        
        # Chercher la table pib_secteurs
        pib_table = None
        for table in tables:
            if 'pib' in table.lower() and 'secteur' in table.lower():
                pib_table = table
                break
        
        if not pib_table:
            print(f"❌ Table pib_secteurs non trouvée. Tables disponibles: {tables}")
            return jsonify({
                'error': 'Table pib_secteurs non trouvée',
                'tables_disponibles': tables,
                'suggestion': 'Assurez-vous que import_ALL.main() a été exécuté correctement'
            }), 404
        
        print(f"✅ Table PIB trouvée: {pib_table}")
        
        # Récupérer la structure de la table
        cursor.execute(f"DESCRIBE `{pib_table}`")
        columns_info = cursor.fetchall()
        column_names = [col['Field'] for col in columns_info]
        
        print(f"📊 Colonnes de la table: {column_names}")
        
        # Récupérer la ligne du PIB global
        cursor.execute(f"SELECT * FROM `{pib_table}` WHERE secteur LIKE '%Produit Intérieur Brut%'")
        pib_row = cursor.fetchone()
        
        if not pib_row:
            # Si pas trouvé, essayer avec la dernière ligne
            print("⚠️ PIB Global non trouvé, utilisation de la dernière ligne")
            cursor.execute(f"SELECT * FROM `{pib_table}` ORDER BY id DESC LIMIT 1")
            pib_row = cursor.fetchone()
        
        if not pib_row:
            return jsonify({'error': 'Aucune donnée PIB trouvée'}), 404
        
        print(f"✅ Données PIB trouvées: {pib_row.get('secteur', 'N/A')}")
        
        # Extraire années et valeurs
        result = {'annees': [], 'valeurs': []}
        
        for key, value in pib_row.items():
            # Chercher les colonnes qui commencent par "annee_"
            if key.startswith('annee_') and value is not None:
                try:
                    # Extraire l'année du nom de colonne
                    annee = key.replace('annee_', '')
                    valeur = float(value) if value else 0
                    
                    result['annees'].append(annee)
                    result['valeurs'].append(valeur)
                except Exception as e:
                    print(f"⚠️ Erreur colonne {key}: {e}")
        
        if not result['annees']:
            return jsonify({
                'error': 'Aucune année détectée',
                'colonnes': column_names,
                'suggestion': 'Vérifiez que les colonnes commencent par "annee_"'
            }), 404
        
        print(f"✅ Données extraites: {len(result['annees'])} années")
        return jsonify(result)
        
    except Error as e:
        print(f"❌ Erreur SQL: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/query/inflation')
def query_inflation():
    """Récupère les données d'inflation IPC Global"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erreur connexion'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Récupérer l'IPC Global
        cursor.execute("SELECT * FROM inflation_categories WHERE categorie = 'IPC GLOBAL'")
        ipc_row = cursor.fetchone()
        
        if not ipc_row:
            return jsonify({'error': 'IPC GLOBAL non trouvé'}), 404
        
        # Extraire années et valeurs
        result = {'annees': [], 'valeurs': []}
        
        for key, value in ipc_row.items():
            if key.startswith('annee_') and value is not None:
                annee = key.replace('annee_', '')
                result['annees'].append(annee)
                result['valeurs'].append(float(value))
        
        return jsonify(result)
        
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/query/opec')
def query_opec():
    """Récupère les données de prix OPEC"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Erreur connexion'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT annee, prix_moyen FROM opec_prix_annuel ORDER BY annee")
        data = cursor.fetchall()
        
        result = {
            'annees': [str(row['annee']) for row in data],
            'valeurs': [float(row['prix_moyen']) for row in data]
        }
        
        return jsonify(result)
        
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ========== DASHBOARD ==========
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Économique</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 3em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .card h2 { color: #2c3e50; margin-bottom: 15px; font-size: 1.3em; }
        .chart-container { background: white; border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); margin-bottom: 20px; }
        .stat { display: flex; justify-content: space-between; align-items: center; margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 10px; }
        .stat-label { font-weight: 600; color: #555; }
        .stat-value { font-size: 1.5em; font-weight: bold; color: #667eea; }
        .loading { text-align: center; padding: 50px; color: white; font-size: 1.5em; }
        .error { background: #ff6b6b; color: white; padding: 20px; border-radius: 10px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Dashboard Économique d'Algérie</h1>
            <p>Analyse de la croissance du PIB, Inflation et Prix du Pétrole</p>
        </div>
        
        <div id="loading" class="loading">⏳ Chargement des données...</div>
        <div id="error" class="error" style="display: none;"></div>
        
        <div id="content" style="display: none;">
            <div class="cards">
                <div class="card">
                    <h2>📈 Statistiques PIB</h2>
                    <div class="stat">
                        <span class="stat-label">Croissance Moyenne</span>
                        <span class="stat-value" id="pib_moyenne">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Maximum</span>
                        <span class="stat-value" id="pib_max">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Dernière année</span>
                        <span class="stat-value" id="pib_last">-</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>📊 Inflation (IPC)</h2>
                    <div class="stat">
                        <span class="stat-label">Moyenne</span>
                        <span class="stat-value" id="inf_moyenne">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Maximum</span>
                        <span class="stat-value" id="inf_max">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Dernière année</span>
                        <span class="stat-value" id="inf_last">-</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🛢️ Prix Pétrole (OPEC)</h2>
                    <div class="stat">
                        <span class="stat-label">Prix Moyen</span>
                        <span class="stat-value" id="opec_moyenne">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Maximum</span>
                        <span class="stat-value" id="opec_max">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Dernière année</span>
                        <span class="stat-value" id="opec_last">-</span>
                    </div>
                </div>
            </div>
            
            <div class="chart-container">
                <h2 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">
                    📊 Évolution de la Croissance Annuelle du PIB
                </h2>
                <canvas id="pibChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h2 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">
                    📈 Inflation et Prix du Pétrole
                </h2>
                <canvas id="multiChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            try {
                // Charger PIB
                const pibResp = await fetch('/api/query/croissance-pib');
                const pibData = await pibResp.json();
                
                if (pibData.error) {
                    throw new Error('PIB: ' + pibData.error);
                }
                
                // Charger Inflation
                const infResp = await fetch('/api/query/inflation');
                const infData = await infResp.json();
                
                // Charger OPEC
                const opecResp = await fetch('/api/query/opec');
                const opecData = await opecResp.json();
                
                // Calculer statistiques PIB
                const pibVals = pibData.valeurs;
                document.getElementById('pib_moyenne').textContent = (pibVals.reduce((a,b) => a+b) / pibVals.length).toFixed(2) + '%';
                document.getElementById('pib_max').textContent = Math.max(...pibVals).toFixed(2) + '%';
                document.getElementById('pib_last').textContent = pibVals[pibVals.length-1].toFixed(2) + '%';
                
                // Calculer statistiques Inflation
                if (!infData.error) {
                    const infVals = infData.valeurs;
                    document.getElementById('inf_moyenne').textContent = (infVals.reduce((a,b) => a+b) / infVals.length).toFixed(2) + '%';
                    document.getElementById('inf_max').textContent = Math.max(...infVals).toFixed(2) + '%';
                    document.getElementById('inf_last').textContent = infVals[infVals.length-1].toFixed(2) + '%';
                }
                
                // Calculer statistiques OPEC
                if (!opecData.error) {
                    const opecVals = opecData.valeurs;
                    document.getElementById('opec_moyenne').textContent = '$' + (opecVals.reduce((a,b) => a+b) / opecVals.length).toFixed(2);
                    document.getElementById('opec_max').textContent = '$' + Math.max(...opecVals).toFixed(2);
                    document.getElementById('opec_last').textContent = '$' + opecVals[opecVals.length-1].toFixed(2);
                }
                
                // Graphique PIB
                const ctx1 = document.getElementById('pibChart').getContext('2d');
                new Chart(ctx1, {
                    type: 'line',
                    data: {
                        labels: pibData.annees,
                        datasets: [{
                            label: 'Croissance du PIB (%)',
                            data: pibVals,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { display: true }
                        },
                        scales: {
                            y: {
                                beginAtZero: false,
                                ticks: {
                                    callback: function(value) {
                                        return value.toFixed(1) + '%';
                                    }
                                }
                            }
                        }
                    }
                });
                
                // Graphique multi (Inflation + OPEC)
                if (!infData.error && !opecData.error) {
                    const ctx2 = document.getElementById('multiChart').getContext('2d');
                    
                    // Trouver les années communes
                    const commonYears = pibData.annees.filter(y => infData.annees.includes(y) && opecData.annees.includes(y));
                    const infFiltered = commonYears.map(y => infData.valeurs[infData.annees.indexOf(y)]);
                    const opecFiltered = commonYears.map(y => opecData.valeurs[opecData.annees.indexOf(y)]);
                    
                    new Chart(ctx2, {
                        type: 'line',
                        data: {
                            labels: commonYears,
                            datasets: [
                                {
                                    label: 'Inflation (%)',
                                    data: infFiltered,
                                    borderColor: '#ff6b6b',
                                    yAxisID: 'y',
                                    tension: 0.4
                                },
                                {
                                    label: 'Prix Pétrole ($/baril)',
                                    data: opecFiltered,
                                    borderColor: '#51cf66',
                                    yAxisID: 'y1',
                                    tension: 0.4
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            interaction: {
                                mode: 'index',
                                intersect: false
                            },
                            scales: {
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    title: { display: true, text: 'Inflation (%)' }
                                },
                                y1: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    title: { display: true, text: 'Prix Pétrole ($)' },
                                    grid: { drawOnChartArea: false }
                                }
                            }
                        }
                    });
                }
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
                
            } catch (error) {
                console.error('Erreur:', error);
                document.getElementById('loading').style.display = 'none';
                const errorDiv = document.getElementById('error');
                errorDiv.textContent = '❌ Erreur: ' + error.message;
                errorDiv.style.display = 'block';
            }
        }
        
        loadData();
    </script>
</body>
</html>
    ''')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE DU DASHBOARD ÉCONOMIQUE")
    print("="*60)
    
    print("\n📦 Initialisation MySQL...")
    init_db()
    
    print("\n" + "="*60)
    print("✅ SERVEUR PRÊT !")
    print("="*60)
    print("🌐 Dashboard : http://localhost:5000")
    print("📊 API PIB    : http://localhost:5000/api/query/croissance-pib")
    print("📊 API Inflation : http://localhost:5000/api/query/inflation")
    print("📊 API OPEC   : http://localhost:5000/api/query/opec")
    print("📋 Tables     : http://localhost:5000/api/tables\n")
    
    app.run(debug=True, port=5000)