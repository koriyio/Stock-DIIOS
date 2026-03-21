import sqlite3
import json
import os

DB_PATH = 'inventario.db'
JSON_PATH = 'datos_inventario.json'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tabla de DIIOs
    c.execute('''
        CREATE TABLE IF NOT EXISTS diios (
            id TEXT PRIMARY KEY,
            inicio INTEGER NOT NULL,
            fin INTEGER NOT NULL,
            estado TEXT NOT NULL,
            proveedor TEXT,
            fecha TEXT,
            destinatario TEXT,
            rut TEXT,
            funcionario TEXT,
            cantidad INTEGER NOT NULL
        )
    ''')
    
    # Tabla de Historial (Log de Auditoría)
    c.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diio_id TEXT,
            accion TEXT,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            detalle TEXT,
            FOREIGN KEY(diio_id) REFERENCES diios(id)
        )
    ''')
    
    conn.commit()
    return conn

def migrate_data():
    conn = init_db()
    
    if not os.path.exists(JSON_PATH):
        print(f"No {JSON_PATH} found. Starting fresh DB.")
        conn.close()
        return
        
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if isinstance(data, dict) and 'rangos_diio' in data:
                rangos = json.loads(data['rangos_diio'])
            elif isinstance(data, list):
                rangos = data
            else:
                rangos = []
        except Exception as e:
            print("Error parsing JSON:", e)
            conn.close()
            return

    c = conn.cursor()
    count = 0
    for item in rangos:
        # Avoid duplicates
        c.execute("SELECT id FROM diios WHERE id=?", (item.get('id'),))
        if not c.fetchone():
            c.execute('''
                INSERT INTO diios (id, inicio, fin, estado, proveedor, fecha, destinatario, rut, funcionario, cantidad)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('id'),
                item.get('inicio'),
                item.get('fin'),
                item.get('estado'),
                item.get('proveedor', ''),
                item.get('fecha', ''),
                item.get('destinatario', ''),
                item.get('rut', ''),
                item.get('funcionario', ''),
                item.get('cantidad', (item.get('fin', 0) - item.get('inicio', 0) + 1))
            ))
            
            # Record in history
            c.execute('''
                INSERT INTO historial (diio_id, accion, detalle)
                VALUES (?, ?, ?)
            ''', (
                item.get('id'),
                'MIGRACION',
                'Registro migrado desde datos_inventario.json'
            ))
            count += 1
            
    conn.commit()
    conn.close()
    print(f"¡Migrados {count} registros exitosamente a {DB_PATH}!")

if __name__ == '__main__':
    migrate_data()
