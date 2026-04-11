from flask import Blueprint, request, jsonify
from models import Leistung
from database import db

leistungen_bp = Blueprint('leistungen', __name__)

@leistungen_bp.route('/leistungen', methods=['GET'])
def get_leistungen():
    leistungen = Leistung.query.all()
    return jsonify([
        {
            'id': l.id,
            'value': l.value,
            'bezeichnung': l.bezeichnung,
            'dauer_min': l.dauer_min,
            'betrag': l.betrag,
            'gruppe': l.gruppe
        } for l in leistungen
    ])


# Neue Route: Einzelne Leistung per ID abfragen
@leistungen_bp.route('/leistungen/<int:id>', methods=['GET'])
def get_leistung_by_id(id):
    leistung = Leistung.query.get_or_404(id)
    return jsonify({
        'id': leistung.id,
        'value': leistung.value,
        'bezeichnung': leistung.bezeichnung,
        'dauer_min': leistung.dauer_min,
        'betrag': leistung.betrag,
        'gruppe': leistung.gruppe
    })

@leistungen_bp.route('/leistungen', methods=['POST'])
def add_leistung():
    data = request.json
    # Wert automatisch setzen, falls nicht übergeben
    value = data.get('value')
    if value is None:
        max_value = db.session.query(db.func.max(Leistung.value)).scalar()
        value = (max_value or 0) + 1
    leistung = Leistung(
        value=value,
        bezeichnung=data.get('bezeichnung'),
        dauer_min=data.get('dauer_min'),
        betrag=data.get('betrag'),
        gruppe=data.get('gruppe')
    )
    db.session.add(leistung)
    db.session.commit()
    return jsonify({'id': leistung.id}), 201

@leistungen_bp.route('/leistungen/<int:id>', methods=['PUT'])
def update_leistung(id):
    leistung = Leistung.query.get_or_404(id)
    data = request.json
    leistung.value = data.get('value', leistung.value)
    leistung.bezeichnung = data.get('bezeichnung', leistung.bezeichnung)
    leistung.dauer_min = data.get('dauer_min', leistung.dauer_min)
    leistung.betrag = data.get('betrag', leistung.betrag)
    leistung.gruppe = data.get('gruppe', leistung.gruppe)
    db.session.commit()
    return jsonify({'success': True})

@leistungen_bp.route('/leistungen/<int:id>', methods=['DELETE'])
def delete_leistung(id):
    leistung = Leistung.query.get_or_404(id)
    db.session.delete(leistung)
    db.session.commit()
    return jsonify({'success': True})
