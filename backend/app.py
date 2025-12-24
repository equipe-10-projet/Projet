from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import json
import os
import re

app = Flask(__name__)
CORS(app)

# Configuration MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pass_root',
    'database': 'economic_dashboard'
}

DATA_FOLDER = '.'
os.makedirs(DATA_FOLDER, exist_ok=True)

# ========== UTILITAIRES ==========
def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"❌ Erreur MySQL: {e}")
        return None

def sanitize_name(name):
    name = str(name).strip().lower()
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    if not name or name[0].isdigit():
        name = 'col_' + name
    return name

def detect_type(value):
    if value is None:
        return "VARCHAR(255)"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT" if abs(value) > 2147483647 else "INT"
    if isinstance(value, float):
        return "DECIMAL(20, 4)"
    if isinstance(value, (list, dict)):
        return "JSON"
    length = len(str(value))
    return "TEXT" if length > 500 else "VARCHAR(500)"

def create_table_from_json(conn, table_name, columns):
    cursor = conn.cursor()
    cols_def = ["id INT AUTO_INCREMENT PRIMARY KEY"]
    
    for col_name, col_info in columns.items():
        cols_def.append(f"`{col_name}` {col_info['type']}")
    
    cols_def.append("created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(cols_def)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    
    try:
        cursor.execute(query)
        conn.commit()
        return True
    except Error as e:
        print(f"❌ Erreur création table: {e}")
        return False
    finally:
        cursor.close()

def insert_json_to_table(conn, table_name, data, columns):
    cursor = conn.cursor()
    
    if isinstance(data, dict):
        data = [data]
    
    col_names = list(columns.keys())
    col_originals = {col: columns[col]['original'] for col in col_names}
    
    placeholders = ', '.join(['%s'] * len(col_names))
    query = f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in col_names])}) VALUES ({placeholders})"
    
    inserted = 0
    for item in data:
        try:
            values = []
            for col in col_names:
                value = item.get(col_originals[col])
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                values.append(value)
            
            cursor.execute(query, values)
            inserted += 1
        except Error as e:
            print(f"⚠️ Erreur insertion: {e}")
    
    try:
        conn.commit()
        return inserted
    finally:
        cursor.close()

def analyze_json(data):
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

# ========== INITIALISATION ==========
def init_db():
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
        # Chercher la table de croissance du PIB
        cursor.execute("SHOW TABLES")
        tables = [row[list(row.keys())[0]] for row in cursor.fetchall()]
        
        print(f"📋 Tables trouvées: {tables}")
        
        pib_table = None
        for table in tables:
            if 'croissance' in table.lower() or 'pib' in table.lower():
                pib_table = table
                break
        
        if not pib_table:
            print(f"❌ Aucune table PIB. Tables disponibles: {tables}")
            return jsonify({
                'error': 'Table PIB non trouvée',
                'tables_disponibles': tables,
                'suggestion': 'Vérifiez que votre fichier JSON est dans le dossier data/'
            }), 404
        
        print(f"✅ Table PIB trouvée: {pib_table}")
        
        # Récupérer les données
        cursor.execute(f"SELECT * FROM `{pib_table}`")
        data = cursor.fetchall()
        
        if not data:
            return jsonify({'error': 'Table vide'}), 404
        
        print(f"📊 {len(data)} lignes dans la table")
        
        # Trouver la ligne "Produit Intérieur Brut"
        pib_row = None
        for row in data:
            for key, value in row.items():
                if value and 'produit' in str(value).lower() and ('brut' in str(value).lower() or 'interieur' in str(value).lower()):
                    pib_row = row
                    print(f"✅ Ligne PIB trouvée: {key} = {value}")
                    break
            if pib_row:
                break
        
        if not pib_row:
            # Si pas trouvé, prendre la dernière ligne non-vide
            print("⚠️ Ligne 'Produit Intérieur Brut' non trouvée, utilisation de la dernière ligne")
            pib_row = data[-1] if data else None
        
        if not pib_row:
            return jsonify({'error': 'Aucune donnée PIB trouvée'}), 404
        
        # Extraire années et valeurs
        result = {'annees': [], 'valeurs': []}
        
        for key, value in pib_row.items():
            # Si la clé ressemble à une année ou commence par underscore + chiffres
            if key not in ['id', 'created_at'] and any(c.isdigit() for c in key):
                try:
                    # Nettoyer le nom de la clé
                    annee = key.strip('_').replace('_', '')
                    # Extraire les 4 chiffres de l'année
                    import re
                    year_match = re.search(r'(19|20)\d{2}', annee)
                    if year_match:
                        annee = year_match.group()
                        valeur = float(str(value).replace(',', '.')) if value else 0
                        result['annees'].append(annee)
                        result['valeurs'].append(valeur)
                except Exception as e:
                    print(f"⚠️ Erreur colonne {key}: {e}")
                    pass
        
        if not result['annees']:
            return jsonify({
                'error': 'Aucune année détectée',
                'colonnes': list(pib_row.keys()),
                'suggestion': 'Vérifiez le format de vos colonnes'
            }), 404
        
        print(f"✅ Données extraites: {len(result['annees'])} années")
        return jsonify(result)
        
    except Error as e:
        print(f"❌ Erreur SQL: {e}")
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
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 3em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: white; border-radius: 20px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .card h2 { color: #2c3e50; margin-bottom: 15px; font-size: 1.3em; }
        .chart-container { background: white; border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .stat { display: flex; justify-content: space-between; align-items: center; margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 10px; }
        .stat-label { font-weight: 600; color: #555; }
        .stat-value { font-size: 1.5em; font-weight: bold; color: #667eea; }
        .loading { text-align: center; padding: 50px; color: white; font-size: 1.5em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Dashboard Économique d'Algérie</h1>
            <p>Analyse de la croissance du PIB</p>
        </div>
        
        <div id="loading" class="loading">⏳ Chargement des données...</div>
        
        <div id="content" style="display: none;">
            <div class="cards">
                <div class="card">
                    <h2>📈 Statistiques PIB</h2>
                    <div class="stat">
                        <span class="stat-label">Croissance Moyenne</span>
                        <span class="stat-value" id="moyenne">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Maximum</span>
                        <span class="stat-value" id="max">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Minimum</span>
                        <span class="stat-value" id="min">-</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>📅 Période</h2>
                    <div class="stat">
                        <span class="stat-label">Première année</span>
                        <span class="stat-value" id="firstYear">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Dernière année</span>
                        <span class="stat-value" id="lastYear">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Total années</span>
                        <span class="stat-value" id="totalYears">-</span>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🎯 Tendance</h2>
                    <div class="stat">
                        <span class="stat-label">Dernière valeur</span>
                        <span class="stat-value" id="lastValue">-</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Tendance générale</span>
                        <span class="stat-value" id="trend">-</span>
                    </div>
                </div>
            </div>
            
            <div class="chart-container">
                <h2 style="color: #2c3e50; margin-bottom: 20px; text-align: center;">
                    📊 Évolution de la Croissance Annuelle du PIB
                </h2>
                <canvas id="pibChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        async function loadData() {
            try {
                const response = await fetch('/api/query/croissance-pib');
                const data = await response.json();
                
                console.log('Données reçues:', data);
                
                if (data.error) {
                    document.getElementById('loading').innerHTML = 
                        '❌ Erreur: ' + data.error + 
                        (data.suggestion ? '<br><br>' + data.suggestion : '') +
                        (data.tables_disponibles ? '<br><br>Tables: ' + data.tables_disponibles.join(', ') : '');
                    return;
                }
                
                if (!data.annees || !data.valeurs || data.annees.length === 0) {
                    document.getElementById('loading').innerHTML = 
                        '❌ Aucune donnée trouvée. Vérifiez que votre fichier JSON est dans le dossier data/';
                    return;
                }
                
                // Calculer les statistiques
                const valeurs = data.valeurs;
                const moyenne = (valeurs.reduce((a, b) => a + b, 0) / valeurs.length).toFixed(2);
                const max = Math.max(...valeurs).toFixed(2);
                const min = Math.min(...valeurs).toFixed(2);
                
                // Afficher les stats
                document.getElementById('moyenne').textContent = moyenne + '%';
                document.getElementById('max').textContent = max + '%';
                document.getElementById('min').textContent = min + '%';
                document.getElementById('firstYear').textContent = data.annees[0];
                document.getElementById('lastYear').textContent = data.annees[data.annees.length - 1];
                document.getElementById('totalYears').textContent = data.annees.length;
                document.getElementById('lastValue').textContent = valeurs[valeurs.length - 1].toFixed(2) + '%';
                
                const trend = moyenne > 3 ? '📈 Positive' : moyenne > 0 ? '➡️ Stable' : '📉 Négative';
                document.getElementById('trend').textContent = trend;
                
                // Créer le graphique
                const ctx = document.getElementById('pibChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.annees,
                        datasets: [{
                            label: 'Croissance du PIB (%)',
                            data: valeurs,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 4,
                            pointBackgroundColor: '#667eea',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointHoverRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top',
                                labels: {
                                    font: { size: 14, weight: 'bold' },
                                    color: '#2c3e50'
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                titleFont: { size: 14 },
                                bodyFont: { size: 13 },
                                padding: 12,
                                displayColors: false,
                                callbacks: {
                                    label: function(context) {
                                        return 'Croissance: ' + context.parsed.y.toFixed(2) + '%';
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: { display: false },
                                ticks: { 
                                    color: '#666',
                                    font: { size: 11 },
                                    maxRotation: 45,
                                    minRotation: 45
                                }
                            },
                            y: {
                                beginAtZero: false,
                                grid: { color: 'rgba(0, 0, 0, 0.05)' },
                                ticks: {
                                    color: '#666',
                                    font: { size: 12 },
                                    callback: function(value) {
                                        return value.toFixed(1) + '%';
                                    }
                                }
                            }
                        }
                    }
                });
                
                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
                
            } catch (error) {
                alert('Erreur de chargement: ' + error.message);
            }
        }
        
        loadData();
    </script>
</body>
</html>
    ''')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DÉMARRAGE")
    print("="*60)
    
    print("\n📦 Initialisation MySQL...")
    init_db()
    
    print("\n🔄 Import JSON...")
    auto_import_json()
    
    print("\n" + "="*60)
    print("✅ SERVEUR PRÊT !")
    print("="*60)
    print("🌐 Dashboard : http://localhost:5000")
    print("📁 Dossier JSON : ./data/")
    print("📊 API : http://localhost:5000/api/query/croissance-pib\n")
    
    app.run(debug=True, port=5000)