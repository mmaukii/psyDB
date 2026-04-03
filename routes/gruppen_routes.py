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
    g = Gruppe(
        gruppenname=data["gruppenname"],
        standardbetrag=data.get("standardbetrag"),
        dauer_min=data.get("dauer_min"),
        gruppenkuerzel=gruppenkuerzel,
        rechnungstext=data.get("rechnungstext"),
        doku=data.get("doku"),
        aktiv=data.get("aktiv", 1),
        therapieform=data.get("therapieform"),
        ust=data.get("ust"),
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
    for field in ["gruppenname", "standardbetrag", "dauer_min", "gruppenkuerzel", "rechnungstext", "doku", "aktiv", "therapieform", "ust"]:
        if field in data:
            setattr(g, field, data[field])
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

