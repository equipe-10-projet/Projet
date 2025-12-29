"""Dashboard Économique d'Algérie"""
from flask import Flask, jsonify, render_template
from flask_cors import CORS
from config import FLASK_CONFIG
from utils import query
from import_auto import import_data

# Flask App
app = Flask(__name__, 
            static_folder=FLASK_CONFIG['STATIC_FOLDER'],
            template_folder=FLASK_CONFIG['TEMPLATE_FOLDER'])
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tables', methods=['GET'])
def get_tables():
    data = query("SHOW TABLES")
    if not data:
        return jsonify({'error': 'Connexion DB'}), 500
    tables = [list(row.values())[0] for row in data]
    return jsonify(tables)

@app.route('/api/table/<table_name>', methods=['GET'])
def get_table_data(table_name):
    data = query(f"SELECT * FROM `{table_name}`")
    return jsonify(data or [])

@app.route('/api/query/croissance-pib')
def get_pib():
    data = query("SELECT annee, valeur FROM croissance_pib ORDER BY annee")
    if not data:
        return jsonify({'error': 'Pas de données'}), 500
    return jsonify({
        'annees': [str(r['annee']) for r in data],
        'valeurs': [float(r['valeur']) for r in data]
    })

@app.route('/api/query/inflation')
def get_inflation():
    data = query("SELECT annee, valeur FROM inflation ORDER BY annee")
    if not data:
        return jsonify({'error': 'Pas de données'}), 500
    return jsonify({
        'annees': [str(r['annee']) for r in data],
        'valeurs': [float(r['valeur']) for r in data]
    })

@app.route('/api/query/opec')
def get_opec():
    data = query("SELECT annee, valeur FROM opec ORDER BY annee")
    if not data:
        return jsonify({'error': 'Pas de données'}), 500
    return jsonify({
        'annees': [str(r['annee']) for r in data],
        'valeurs': [float(r['valeur']) for r in data]
    })

@app.route('/api/query/pib-secteurs')
def get_pib_secteurs():
    data = query("SELECT * FROM pib_secteurs ORDER BY secteur")
    return jsonify(data or [])

@app.route('/api/stats/pib')
def stats_pib():
    stats = query("""
        SELECT COUNT(*) as count, AVG(valeur) as moyenne, 
               MIN(valeur) as minimum, MAX(valeur) as maximum
        FROM croissance_pib
    """, fetch='one')
    
    last = query("SELECT annee, valeur FROM croissance_pib ORDER BY annee DESC LIMIT 1", fetch='one')
    
    if not stats:
        return jsonify({'error': 'Pas de données'}), 500
    
    return jsonify({
        'nombre_annees': stats['count'],
        'moyenne': round(float(stats['moyenne']), 2),
        'minimum': round(float(stats['minimum']), 2),
        'maximum': round(float(stats['maximum']), 2),
        'derniere_annee': last['annee'] if last else None,
        'derniere_valeur': round(float(last['valeur']), 2) if last else None
    })

@app.route('/api/stats/inflation')
def stats_inflation():
    stats = query("""
        SELECT COUNT(*) as count, AVG(valeur) as moyenne, 
               MIN(valeur) as minimum, MAX(valeur) as maximum
        FROM inflation
    """, fetch='one')
    
    last = query("SELECT annee, valeur FROM inflation ORDER BY annee DESC LIMIT 1", fetch='one')
    
    if not stats:
        return jsonify({'error': 'Pas de données'}), 500
    
    return jsonify({
        'nombre_annees': stats['count'],
        'moyenne': round(float(stats['moyenne']), 2),
        'minimum': round(float(stats['minimum']), 2),
        'maximum': round(float(stats['maximum']), 2),
        'derniere_annee': last['annee'] if last else None,
        'derniere_valeur': round(float(last['valeur']), 2) if last else None
    })

@app.route('/api/stats/opec')
def stats_opec():
    stats = query("""
        SELECT COUNT(*) as count, AVG(valeur) as moyenne, 
               MIN(valeur) as minimum, MAX(valeur) as maximum
        FROM opec
    """, fetch='one')
    
    last = query("SELECT annee, valeur FROM opec ORDER BY annee DESC LIMIT 1", fetch='one')
    
    if not stats:
        return jsonify({'error': 'Pas de données'}), 500
    
    return jsonify({
        'nombre_annees': stats['count'],
        'moyenne': round(float(stats['moyenne']), 2),
        'minimum': round(float(stats['minimum']), 2),
        'maximum': round(float(stats['maximum']), 2),
        'derniere_annee': last['annee'] if last else None,
        'derniere_valeur': round(float(last['valeur']), 2) if last else None
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  DASHBOARD ÉCONOMIQUE D'ALGÉRIE")
    print("="*50)
    
    # Import systématique au démarrage
    print("\nImport des données...")
    import_data()
    
    print(f"\n→ Dashboard: http://localhost:{FLASK_CONFIG['PORT']}\n")
    print("="*50 + "\n")
    
    app.run(
        debug=False, 
        host=FLASK_CONFIG['HOST'], 
        port=FLASK_CONFIG['PORT']
    )
