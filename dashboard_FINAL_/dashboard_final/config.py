"""Configuration"""

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pass_root',
    'database': 'economic_dashboard'
}

FLASK_CONFIG = {
    'DEBUG': True,
    'HOST': '0.0.0.0',
    'PORT': 5000,
    'STATIC_FOLDER': 'frontend/static',
    'TEMPLATE_FOLDER': 'frontend/templates'
}
