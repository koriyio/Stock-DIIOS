from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
import uuid
import datetime

app = Flask(__name__)
DB_PATH = 'inventario.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar Base de Datos por si no existe
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
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
    conn.close()

init_db()

def log_action(conn, diio_id, accion, detalle):
    conn.execute('INSERT INTO historial (diio_id, accion, detalle) VALUES (?, ?, ?)', (diio_id, accion, detalle))


# ---------------------------------------------------------
# RUTAS DE LA API REST
# ---------------------------------------------------------

@app.route('/api/diios', methods=['GET'])
def get_diios():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM diios ORDER BY inicio ASC")
        rows = c.fetchall()
        
        diios = []
        for row in rows:
            diios.append({
                'id': row['id'],
                'inicio': row['inicio'],
                'fin': row['fin'],
                'estado': row['estado'],
                'proveedor': row['proveedor'] or '',
                'fecha': row['fecha'] or '',
                'destinatario': row['destinatario'] or '',
                'rut': row['rut'] or '',
                'funcionario': row['funcionario'] or '',
                'cantidad': row['cantidad']
            })
        conn.close()
        return jsonify(diios), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/diios', methods=['POST'])
def create_diio():
    data = request.json
    if not data or 'inicio' not in data or 'fin' not in data or 'estado' not in data:
        return jsonify({"error": "Faltan datos obligatorios (inicio, fin, estado)"}), 400
    
    # Validar datos
    try:
        inicio = int(data['inicio'])
        fin = int(data['fin'])
    except ValueError:
        return jsonify({"error": "Inicio y fin deben ser numéricos"}), 400

    if inicio > fin:
        return jsonify({"error": "Inicio no puede ser mayor que fin"}), 400

    cantidad = fin - inicio + 1
    new_id = str(uuid.uuid4())

    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO diios (id, inicio, fin, estado, proveedor, fecha, destinatario, rut, funcionario, cantidad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_id, inicio, fin, data['estado'],
            data.get('proveedor', ''), data.get('fecha', ''),
            data.get('destinatario', ''), data.get('rut', ''),
            data.get('funcionario', ''), cantidad
        ))
        
        log_action(conn, new_id, 'CREAR', f"Rango {inicio}-{fin} creado ({data['estado']})")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "id": new_id, "message": "Rango creado exitosamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/diios/<diio_id>', methods=['PUT'])
def update_diio(diio_id):
    data = request.json
    if not data:
        return jsonify({"error": "No se proporcionaron datos para actualizar"}), 400
        
    try:
        conn = get_db_connection()
        # Verificar que existe
        row = conn.execute("SELECT * FROM diios WHERE id = ?", (diio_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Registro no encontrado"}), 404

        # Campos permitidos para actualizar
        update_fields = []
        update_values = []
        for field in ['inicio', 'fin', 'estado', 'proveedor', 'fecha', 'destinatario', 'rut', 'funcionario']:
            if field in data:
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])

        if 'inicio' in data or 'fin' in data:
            inicio = int(data.get('inicio', row['inicio']))
            fin = int(data.get('fin', row['fin']))
            cantidad = fin - inicio + 1
            update_fields.append("cantidad = ?")
            update_values.append(cantidad)

        if not update_fields:
            conn.close()
            return jsonify({"error": "No hay campos válidos para actualizar"}), 400

        update_values.append(diio_id)
        query = f"UPDATE diios SET {', '.join(update_fields)} WHERE id = ?"
        conn.execute(query, update_values)
        
        log_action(conn, diio_id, 'ACTUALIZAR', f"Actualizado: {data.get('estado', row['estado'])}")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Registro actualizado"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/diios/<diio_id>', methods=['DELETE'])
def delete_diio(diio_id):
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM diios WHERE id = ?", (diio_id,)).fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "Registro no encontrado"}), 404

        conn.execute("DELETE FROM diios WHERE id = ?", (diio_id,))
        # También eliminar o conservar historial? Por integridad relacional (si no es ON DELETE CASCADE),
        # puede fallar si no borramos historial. Asumimos borrar el historial asociado por simplicidad,
        # O MEJOR, marcarlo como inactivo. 
        # Ya que es SQLite, hacemos DELETE del historial para limpiar o desactivamos pragmas.
        conn.execute("DELETE FROM historial WHERE diio_id = ?", (diio_id,))
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Registro eliminado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/diios/consolidate', methods=['POST'])
def consolidate_diios():
    """
    Consolida rangos contiguos con el EXACTO mismo estado y campos base.
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM diios ORDER BY inicio ASC")
        rows = [dict(row) for row in c.fetchall()]
        
        if not rows:
            conn.close()
            return jsonify({"message": "No hay DIIOs para consolidar", "consolidated_count": 0}), 200

        consolidated = []
        current = rows[0]
        
        for next_item in rows[1:]:
            # Chequear si son contiguos
            if (current['fin'] + 1 == next_item['inicio'] and 
                current['estado'] == next_item['estado'] and
                current.get('rut') == next_item.get('rut') and
                current.get('destinatario') == next_item.get('destinatario') and
                current.get('proveedor') == next_item.get('proveedor')):
                
                # Consolidar
                current['fin'] = next_item['fin']
                current['cantidad'] = current['fin'] - current['inicio'] + 1
            else:
                consolidated.append(current)
                current = next_item
        consolidated.append(current)

        # Si hubo una reducción de elementos
        if len(consolidated) < len(rows):
            # Dropear todos y reinsertar
            c.execute("DELETE FROM historial")
            c.execute("DELETE FROM diios")
            for item in consolidated:
                new_id = str(uuid.uuid4())
                c.execute('''
                    INSERT INTO diios (id, inicio, fin, estado, proveedor, fecha, destinatario, rut, funcionario, cantidad)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    new_id, item['inicio'], item['fin'], item['estado'],
                    item.get('proveedor', ''), item.get('fecha', ''),
                    item.get('destinatario', ''), item.get('rut', ''),
                    item.get('funcionario', ''), item['cantidad']
                ))
            conn.commit()
            conn.close()
            return jsonify({
                "success": True, 
                "message": "Consolidación completa.", 
                "original_count": len(rows), 
                "consolidated_count": len(consolidated)
            }), 200
        else:
            conn.close()
            return jsonify({
                "success": True, 
                "message": "Ningún rango pudo ser consolidado (no hay contiguos del mismo estado).",
                "original_count": len(rows),
                "consolidated_count": len(consolidated)
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------
# SERVIR FRONTEND
# ---------------------------------------------------------

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    # Remover debug=True por seguridad
    app.run(host='127.0.0.1', port=5000)
