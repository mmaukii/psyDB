from flask import Flask, request, jsonify
from database import db
from models import TermineRechnung
from datetime import datetime, timezone

app = Flask(__name__)

# --- Alle Zuordnungen ausgeben ---
@app.route("api/termine_rechnungen", methods=["GET"])
def get_all_termine_rechnungen():
    all_sr = TermineRechnung.query.all()
    result = [
        {"id": sr.id, "rechnung_id": sr.rechnung_id, "termin_id": sr.termin_id, "timestamp": sr.timestamp}
        for sr in all_sr
    ]
    return jsonify(result)

# --- Einzelne Zuordnung abrufen ---
@app.route("api/termine_rechnungen/<int:id>", methods=["GET"])
def get_termine_rechnung(id):
    sr = TermineRechnung.query.get_or_404(id)
    return jsonify({"id": sr.id, "rechnung_id": sr.rechnung_id, "termin_id": sr.termin_id, "timestamp": sr.timestamp})

# --- Neue Zuordnung erstellen --- -Wird von keiner Logik verwendet!!!
@app.route("api/termine_rechnungen", methods=["POST"])
def add_termine_rechnung():
    data = request.get_json()

    rechnung_id = data.get("rechnung_id")
    termin_id = data.get("termine_id")

    if not rechnung_id or not termin_id:
        return jsonify({"error": "rechnung_id und termine_id erforderlich"}), 400

    from datetime import datetime
    sr = TermineRechnung(
        rechnung_id=rechnung_id,
        termin_id=termin_id,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    db.session.add(sr)
    db.session.commit()
    print(f"timestamp nach Commit: {sr.timestamp}")
    return jsonify({"success": True, "id": sr.id}), 201

# --- Zuordnung aktualisieren ---
@app.route("/termine_rechnungen/<int:id>", methods=["PUT"])
def update_termine_rechnung(id):
    sr = TermineRechnung.query.get_or_404(id)
    data = request.get_json()
    
    sr.rechnung_id = data.get("rechnung_id", sr.rechnung_id)
    sr.termin_id = data.get("termine_id", sr.termin_id)

    db.session.commit()
    return jsonify({"success": True})

# --- Zuordnung löschen ---
@app.route("/termine_rechnungen/<int:id>", methods=["DELETE"])
def delete_termine_rechnung(id):
    sr = TermineRechnung.query.get_or_404(id)
    db.session.delete(sr)
    db.session.commit()
    return jsonify({"success": True})
