from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid

app = Flask(__name__, static_folder='.', static_url_path='')

database_url = os.environ.get('DATABASE_URL', 'sqlite:///inventario.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class Rango(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    inicio = db.Column(db.Integer, nullable=False)
    fin = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(50), nullable=False)
    proveedor = db.Column(db.String(100), nullable=True)
    funcionario = db.Column(db.String(100), nullable=True)
    fecha = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'inicio': self.inicio,
            'fin': self.fin,
            'estado': self.estado,
            'proveedor': self.proveedor,
            'funcionario': self.funcionario,
            'fecha': self.fecha
        }

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre
        }

class Historial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accion = db.Column(db.String(100), nullable=False)
    detalle = db.Column(db.String(255), nullable=False)
    icono = db.Column(db.String(50), nullable=True)
    fecha = db.Column(db.String(50), nullable=False)
    hora = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'accion': self.accion,
            'detalle': self.detalle,
            'icono': self.icono,
            'fecha': self.fecha,
            'hora': self.hora
        }

# Ensure tables are created
with app.app_context():
    db.create_all()

# --- Routes - Pages ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_html(filename):
    if filename.endswith('.html'):
        return send_from_directory('.', filename)
    return send_from_directory('.', filename)

# --- Routes - API - Rangos ---
@app.route('/api/rangos', methods=['GET'])
def get_rangos():
    rangos = Rango.query.all()
    return jsonify([r.to_dict() for r in rangos])

@app.route('/api/rangos', methods=['POST'])
def create_rango():
    data = request.json
    rango = Rango(
        id=data.get('id', str(uuid.uuid4())),
        inicio=int(data['inicio']),
        fin=int(data['fin']),
        estado=data['estado'],
        proveedor=data.get('proveedor'),
        funcionario=data.get('funcionario'),
        fecha=data['fecha']
    )
    db.session.add(rango)
    db.session.commit()
    return jsonify(rango.to_dict()), 201

@app.route('/api/rangos/bulk', methods=['POST'])
def sync_rangos():
    # Sync all rangos (replaces existing completely)
    data = request.json
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list'}), 400
    
    Rango.query.delete()
    for item in data:
        rango = Rango(
            id=item.get('id', str(uuid.uuid4())),
            inicio=int(item['inicio']),
            fin=int(item['fin']),
            estado=item['estado'],
            proveedor=item.get('proveedor'),
            funcionario=item.get('funcionario'),
            fecha=item['fecha']
        )
        db.session.add(rango)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/rangos/<rango_id>', methods=['PUT'])
def update_rango(rango_id):
    rango = Rango.query.get_or_404(rango_id)
    data = request.json
    if 'inicio' in data: rango.inicio = int(data['inicio'])
    if 'fin' in data: rango.fin = int(data['fin'])
    if 'estado' in data: rango.estado = data['estado']
    if 'proveedor' in data: rango.proveedor = data['proveedor']
    if 'funcionario' in data: rango.funcionario = data['funcionario']
    if 'fecha' in data: rango.fecha = data['fecha']
    
    db.session.commit()
    return jsonify(rango.to_dict())

@app.route('/api/rangos/<rango_id>', methods=['DELETE'])
def delete_rango(rango_id):
    rango = Rango.query.get_or_404(rango_id)
    db.session.delete(rango)
    db.session.commit()
    return '', 204

# --- Routes - API - Funcionarios ---
@app.route('/api/funcionarios', methods=['GET'])
def get_funcionarios():
    funcs = Funcionario.query.all()
    # Retornamos solo los nombres para mantener compatibilidad con el frontend si es posible, o dicts
    return jsonify([f.nombre for f in funcs])

@app.route('/api/funcionarios', methods=['POST'])
def create_funcionario():
    data = request.json
    # Soporta recibir un string directo o un objeto
    nombre = data if isinstance(data, str) else data.get('nombre')
    
    if Funcionario.query.filter_by(nombre=nombre).first():
        return jsonify({'error': 'Funcionario ya existe'}), 400
        
    func = Funcionario(nombre=nombre)
    db.session.add(func)
    db.session.commit()
    return jsonify(func.to_dict()), 201

@app.route('/api/funcionarios/<nombre>', methods=['DELETE'])
def delete_funcionario(nombre):
    func = Funcionario.query.filter_by(nombre=nombre).first_or_404()
    db.session.delete(func)
    db.session.commit()
    return '', 204

@app.route('/api/funcionarios/bulk', methods=['POST'])
def sync_funcionarios():
    data = request.json
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list'}), 400
        
    Funcionario.query.delete()
    for nombre in data:
        func = Funcionario(nombre=nombre)
        db.session.add(func)
    db.session.commit()
    return jsonify({'status': 'success'})

# --- Routes - API - Historial ---
@app.route('/api/historial', methods=['GET'])
def get_historial():
    hist = Historial.query.order_by(Historial.timestamp.desc()).limit(50).all()
    return jsonify([h.to_dict() for h in hist])

@app.route('/api/historial', methods=['POST'])
def add_historial():
    data = request.json
    hist = Historial(
        accion=data['accion'],
        detalle=data['detalle'],
        icono=data.get('icono'),
        fecha=data['fecha'],
        hora=data['hora']
    )
    db.session.add(hist)
    
    # Mantener solo los últimos 50
    if Historial.query.count() > 50:
        oldest = Historial.query.order_by(Historial.timestamp.asc()).first()
        db.session.delete(oldest)
        
    db.session.commit()
    return jsonify(hist.to_dict()), 201

@app.route('/api/historial/bulk', methods=['POST'])
def sync_historial():
    data = request.json
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a list'}), 400
        
    Historial.query.delete()
    for item in data:
        hist = Historial(
            accion=item['accion'],
            detalle=item['detalle'],
            icono=item.get('icono'),
            fecha=item['fecha'],
            hora=item['hora']
        )
        db.session.add(hist)
    db.session.commit()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
