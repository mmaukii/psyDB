# routes/standorte_routes.py

from flask import Blueprint, request, jsonify
from database import db
from models import Standort
from datetime import datetime, timezone

standorte_bp = Blueprint("standorte", __name__)

# --- Alle Standorte ---
@standorte_bp.get("/standorte")
def get_all_standorte():
    standorte = Standort.query.order_by(Standort.name).all()
    return jsonify([{
        "id": s.id,
        "name": s.name,
        "adresse": s.adresse,
        "plz": s.plz,
        "ort": s.ort,
        "email": s.email,
        "kuerzel": s.kuerzel,
        "bic": s.bic,
        "iban": s.iban,
        "kontoName": s.kontoName,
        "bankname": s.bankname,
        "standard": bool(s.standard) if s.standard is not None else False
    } for s in standorte])

# --- Einzelner Standort ---
@standorte_bp.get("/standorte/<int:id>")
def get_standort(id):
    s = Standort.query.get_or_404(id)
    return jsonify({
        "id": s.id,
        "name": s.name,
        "adresse": s.adresse,
        "plz": s.plz,
        "ort": s.ort,
        "email": s.email,
        "kuerzel": s.kuerzel,
        "bic": s.bic,
        "iban": s.iban,
        "kontoName": s.kontoName,
        "bankname": s.bankname,
        "standard": bool(s.standard) if s.standard is not None else False
    })

# --- Standort anlegen ---
@standorte_bp.post("/standorte")
def add_standort():
    data = request.get_json()

    s = Standort(
        name=data["name"],
        adresse=data.get("adresse"),
        plz=data.get("plz"),
        ort=data.get("ort"),
        email=data.get("email"),
        kuerzel=data["kuerzel"],
        bic=data.get("bic"),
        iban=data.get("iban"),
        kontoName=data.get("kontoName"),
        bankname=data.get("bankname"),
        standard=int(data.get("standard", 0)),
        timestamp=datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"),
    )

    db.session.add(s)
    db.session.commit()
    return jsonify({"success": True, "id": s.id}), 201

# --- Standort ändern ---
@standorte_bp.put("/standorte/<int:id>")
def update_standort(id):
    s = Standort.query.get_or_404(id)
    data = request.get_json()

    for field in [
        "name", "adresse", "plz", "ort",
        "email", "kuerzel", "bic", "iban", "kontoName", "bankname", "standard"
    ]:
        if field in data:
            if field == "standard":
                setattr(s, field, int(data[field]))
            else:
                setattr(s, field, data[field])

    s.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    db.session.commit()
    return jsonify({"success": True})

# --- Standort löschen ---
@standorte_bp.delete("/standorte/<int:id>")
def delete_standort(id):
    s = Standort.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"success": True})
