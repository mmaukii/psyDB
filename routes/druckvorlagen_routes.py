from flask import Blueprint, request, jsonify
from database import db
from models import Druckvorlage
from datetime import datetime, timezone


druckvorlagen_bp = Blueprint("druckvorlagen", __name__)


@druckvorlagen_bp.get("/druckvorlagen")
def get_all_druckvorlagen():
    vorlagen = Druckvorlage.query.order_by(Druckvorlage.name).all()
    return jsonify([
        {
            "id": v.id,
            "name": v.name,
            "pfad": v.pfad,
            "kuerzel": v.kuerzel,
        }
        for v in vorlagen
    ])


@druckvorlagen_bp.get("/druckvorlagen/<int:id>")
def get_druckvorlage(id):
    v = Druckvorlage.query.get_or_404(id)
    return jsonify({
        "id": v.id,
        "name": v.name,
        "pfad": v.pfad,
        "kuerzel": v.kuerzel,
    })


@druckvorlagen_bp.post("/druckvorlagen")
def add_druckvorlage():
    data = request.get_json()

    v = Druckvorlage(
        name=data.get("name"),
        pfad=data.get("pfad"),
        kuerzel=data.get("kuerzel"),
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )

    db.session.add(v)
    db.session.commit()
    return jsonify({"success": True, "id": v.id}), 201


@druckvorlagen_bp.put("/druckvorlagen/<int:id>")
def update_druckvorlage(id):
    v = Druckvorlage.query.get_or_404(id)
    data = request.get_json()

    for field in ["name", "pfad", "kuerzel"]:
        if field in data:
            setattr(v, field, data[field])
    v.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    db.session.commit()
    return jsonify({"success": True})


@druckvorlagen_bp.delete("/druckvorlagen/<int:id>")
def delete_druckvorlage(id):
    v = Druckvorlage.query.get_or_404(id)
    db.session.delete(v)
    db.session.commit()
    return jsonify({"success": True})
