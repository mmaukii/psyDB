from flask import Flask, request, jsonify
from database import db
from models import TermineRechnung

app = Flask(__name__)

# --- Alle Zuordnungen ausgeben ---
@app.route("api/termine_rechnungen", methods=["GET"])
def get_all_termine_rechnungen():
    all_sr = TermineRechnung.query.all()
    result = [
        {"id": sr.id, "rechnung_id": sr.rechnung_id, "termine_id": sr.termine_id}
        for sr in all_sr
    ]
    return jsonify(result)

# --- Einzelne Zuordnung abrufen ---
@app.route("api/termine_rechnungen/<int:id>", methods=["GET"])
def get_termine_rechnung(id):
    sr = TermineRechnung.query.get_or_404(id)
    return jsonify({"id": sr.id, "rechnung_id": sr.rechnung_id, "termine_id": sr.termine_id})

# --- Neue Zuordnung erstellen ---
@app.route("api/termine_rechnungen", methods=["POST"])
def add_termine_rechnung():
    data = request.get_json()
    rechnung_id = data.get("rechnung_id")
    termine_id = data.get("termine_id")

    if not rechnung_id or not termine_id:
        return jsonify({"error": "rechnung_id und termine_id erforderlich"}), 400

    sr = TermineRechnung(rechnung_id=rechnung_id, termine_id=termine_id)
    db.session.add(sr)
    db.session.commit()
    return jsonify({"success": True, "id": sr.id}), 201

# --- Zuordnung aktualisieren ---
@app.route("/termine_rechnungen/<int:id>", methods=["PUT"])
def update_termine_rechnung(id):
    sr = TermineRechnung.query.get_or_404(id)
    data = request.get_json()
    
    sr.rechnung_id = data.get("rechnung_id", sr.rechnung_id)
    sr.termine_id = data.get("termine_id", sr.termine_id)

    db.session.commit()
    return jsonify({"success": True})

# --- Zuordnung löschen ---
@app.route("/termine_rechnungen/<int:id>", methods=["DELETE"])
def delete_termine_rechnung(id):
    sr = TermineRechnung.query.get_or_404(id)
    db.session.delete(sr)
    db.session.commit()
    return jsonify({"success": True})
