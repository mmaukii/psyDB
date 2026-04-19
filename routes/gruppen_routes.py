from flask import Blueprint, request, jsonify
from database import db
from models import Gruppe
from datetime import datetime, timezone

gruppen_bp = Blueprint("gruppen", __name__)

# --- Alle Gruppen ---
@gruppen_bp.get("/gruppen")
def get_all_gruppen():
    gruppen = Gruppe.query.order_by(Gruppe.gruppenname).all()
    return jsonify([{
        "id": g.id,
        "gruppenname": g.gruppenname,
        "standardbetrag": g.standardbetrag,
        "dauer_min": g.dauer_min,
        "gruppenkuerzel": g.gruppenkuerzel,
        "rechnungstext": g.rechnungstext,
        "doku": g.doku,
        "aktiv": g.aktiv,
        "therapieform": getattr(g, "therapieform", None),
        "ust": getattr(g, "ust", None)
    } for g in gruppen])

# --- Einzelne Gruppe ---
@gruppen_bp.get("/gruppen/<int:id>")
def get_gruppe(id):
    g = Gruppe.query.get_or_404(id)
    return jsonify({
        "id": g.id,
        "gruppenname": g.gruppenname,
        "standardbetrag": g.standardbetrag,
        "dauer_min": g.dauer_min,
        "gruppenkuerzel": g.gruppenkuerzel,
        "rechnungstext": g.rechnungstext,
        "doku": g.doku,
        "aktiv": g.aktiv,
        "therapieform": getattr(g, "therapieform", None),
        "ust": getattr(g, "ust", None)
    })

# --- aktive Gruppen ----
@gruppen_bp.get("/gruppen/aktiv")
def get_aktive_gruppen():
    gruppen = Gruppe.query.filter_by(aktiv=1).order_by(Gruppe.gruppenname).all()
    return jsonify([{
        "id": g.id,
        "gruppenname": g.gruppenname,
        "standardbetrag": g.standardbetrag,
        "dauer_min": g.dauer_min,
        "gruppenkuerzel": g.gruppenkuerzel,
        "rechnungstext": g.rechnungstext,
        "doku": g.doku,
        "aktiv": g.aktiv,
        "therapieform": g.therapieform,
        "ust": g.ust
    } for g in gruppen])

# --- inaktive Gruppen ----
@gruppen_bp.get("/gruppen/inaktiv")
def get_inaktive_gruppen(): 
    gruppen = Gruppe.query.filter_by(aktiv=0).order_by(Gruppe.gruppenname).all()
    return jsonify([{
        "id": g.id,
        "gruppenname": g.gruppenname,
        "standardbetrag": g.standardbetrag,
        "dauer_min": g.dauer_min,
        "gruppenkuerzel": g.gruppenkuerzel,
        "rechnungstext": g.rechnungstext,
        "doku": g.doku,
        "aktiv": g.aktiv,
        "therapieform": getattr(g, "therapieform", None),
        "ust": getattr(g, "ust", None)
    } for g in gruppen])    

# --- Gruppe anlegen ---
@gruppen_bp.post("/gruppen")
def add_gruppe():
    data = request.get_json()
    gruppenkuerzel = data.get("gruppenkuerzel")
    if not gruppenkuerzel:
        return jsonify({"success": False, "error": "Gruppenkuerzel ist erforderlich"}), 400
    # Validation for NOT NULL fields
    if data.get("therapieform") is None:
        return jsonify({"success": False, "error": "therapieform ist erforderlich"}), 400
    ust = data.get("ust")
    if ust is None:
        ust = 0
    aktiv = data.get("aktiv")
    if aktiv is None:
        aktiv = 1
    g = Gruppe(
        gruppenname=data["gruppenname"],
        standardbetrag=data.get("standardbetrag"),
        dauer_min=data.get("dauer_min"),
        gruppenkuerzel=gruppenkuerzel,
        rechnungstext=data.get("rechnungstext"),
        doku=data.get("doku"),
        aktiv=aktiv,
        therapieform=data["therapieform"],
        ust=ust,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    db.session.add(g)
    db.session.commit()
    return jsonify({"success": True, "id": g.id}), 201

# --- Gruppe ändern ---
@gruppen_bp.put("/gruppen/<int:id>")
def update_gruppe(id):
    g = Gruppe.query.get_or_404(id)
    data = request.get_json()
    if "gruppenkuerzel" in data:
        if not data["gruppenkuerzel"]:
            return jsonify({"success": False, "error": "Gruppenkuerzel ist erforderlich"}), 400
    # Set and validate fields, enforce NOT NULL and defaults
    for field in ["gruppenname", "standardbetrag", "dauer_min", "gruppenkuerzel", "rechnungstext", "doku"]:
        if field in data:
            setattr(g, field, data[field])
    if "aktiv" in data:
        g.aktiv = data["aktiv"] if data["aktiv"] is not None else 1
    if "therapieform" in data:
        if data["therapieform"] is None:
            return jsonify({"success": False, "error": "therapieform ist erforderlich"}), 400
        g.therapieform = data["therapieform"]
    if "ust" in data:
        g.ust = data["ust"] if data["ust"] is not None else 0
    g.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    db.session.commit()
    return jsonify({"success": True})

# --- Gruppe löschen ---
@gruppen_bp.delete("/gruppen/<int:id>")
def delete_gruppe(id):
    g = Gruppe.query.get_or_404(id)
    db.session.delete(g)
    db.session.commit()
    return jsonify({"success": True})

