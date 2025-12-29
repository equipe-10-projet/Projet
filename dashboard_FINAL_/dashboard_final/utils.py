"""Utilitaires MySQL"""
import mysql.connector
from config import DB_CONFIG

def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Erreur MySQL: {e}")
        return None

def query(sql, params=None, fetch='all'):
    conn = get_db()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        
        if fetch == 'all':
            result = cursor.fetchall()
        elif fetch == 'one':
            result = cursor.fetchone()
        else:
            conn.commit()
            result = cursor.rowcount
        
        return result
    except Exception as e:
        print(f"Erreur SQL: {e}")
        return None
    finally:
        cursor.close()
        conn.close()
