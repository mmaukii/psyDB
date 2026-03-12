from flask import Blueprint, request, jsonify
from database import db
from models import GruppenKunde, Kunde, Gruppe

gruppenkunden_bp = Blueprint("gruppenkunden", __name__)

# -------------------------------------------------
# Kunden einer Gruppe
# -------------------------------------------------
@gruppenkunden_bp.get("/gruppen/<int:gruppe_id>/kunden")
def get_kunden_einer_gruppe(gruppe_id):
    kunden = (
        db.session.query(
            Kunde.id,
            Kunde.vorname,
            Kunde.nachname,
            Kunde.email,
            Kunde.kuerzel,
            GruppenKunde.betrag
        )
        .join(GruppenKunde, GruppenKunde.kunde_id == Kunde.id)
        .filter(GruppenKunde.gruppe_id == gruppe_id)
        .order_by(Kunde.nachname)
        .all()
    )

    return jsonify([{
        "id": k.id,
        "vorname": k.vorname,
        "nachname": k.nachname,
        "email": k.email,
        "kuerzel": k.kuerzel,
        "betrag": k.betrag
    } for k in kunden])

# -------------------------------------------------
#  Gruppen kunden aktualisieren 
# -------------------------------------------------
@gruppenkunden_bp.put("/gruppen/<int:id>/kunden")
def update_gruppen_kunden(id):
    data = request.get_json()
    neue_kunden_ids = set(data.get("kunden_ids", []))  # Kundenliste vom Frontend

    # aktuelle Kunden aus DB
    aktuelle_kunden = {kc.kunde_id for kc in GruppenKunde.query.filter_by(gruppe_id=id).all()}

    # Kunden hinzufügen
    hinzuzufuegen = neue_kunden_ids - aktuelle_kunden
    for kunde_id in hinzuzufuegen:
        db.session.add(GruppenKunde(gruppe_id=id, kunde_id=kunde_id))

    # Kunden entfernen, die nicht mehr ausgewählt sind
    zu_entfernen = aktuelle_kunden - neue_kunden_ids
    if zu_entfernen:
        GruppenKunde.query.filter(
            GruppenKunde.gruppe_id == id,
            GruppenKunde.kunde_id.in_(zu_entfernen)
        ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({"success": True})


# -------------------------------------------------
# Kunde zu Gruppe hinzufügen
# -------------------------------------------------
@gruppenkunden_bp.post("/gruppen/<int:gruppe_id>/kunden")
def add_kunde_zu_gruppe(gruppe_id):
    data = request.get_json()

    gk = GruppenKunde(
        gruppe_id=gruppe_id,
        kunde_id=data["kunde_id"],
        betrag=data.get("betrag")
    )

    db.session.add(gk)
    db.session.commit()

    return jsonify({"success": True}), 201


# -------------------------------------------------
# Kunde in Gruppe ändern (z. B. Betrag)
# -------------------------------------------------
@gruppenkunden_bp.put("/gruppen/<int:gruppe_id>/kunden/<int:kunde_id>")
def update_kunde_in_gruppe(gruppe_id, kunde_id):
    gk = GruppenKunde.query.filter_by(
        gruppe_id=gruppe_id,
        kunde_id=kunde_id
    ).first_or_404()

    data = request.get_json()

    if "betrag" in data:
        gk.betrag = data["betrag"]

    db.session.commit()
    return jsonify({"success": True})


# -------------------------------------------------
# Kunde aus Gruppe entfernen
# -------------------------------------------------
@gruppenkunden_bp.delete("/gruppen/<int:gruppe_id>/kunden/<int:kunde_id>")
def delete_kunde_aus_gruppe(gruppe_id, kunde_id):
    gk = GruppenKunde.query.filter_by(
        gruppe_id=gruppe_id,
        kunde_id=kunde_id
    ).first_or_404()

    db.session.delete(gk)
    db.session.commit()

    return jsonify({"success": True})

# -------------------------------------------------
# Betrag eines Kunden in einer Gruppe auslesen
# -------------------------------------------------
@gruppenkunden_bp.get("/gruppen/<int:gruppe_id>/kunden/<int:kunde_id>/betrag")
def get_betrag_eines_kunden(gruppe_id, kunde_id):
    gk = GruppenKunde.query.filter_by(
        gruppe_id=gruppe_id,
        kunde_id=kunde_id
    ).first()

    if not gk:
        return jsonify({"error": "Kunde nicht in Gruppe"}), 404

    return jsonify({
        "gruppe_id": gruppe_id,
        "kunde_id": kunde_id,
        "betrag": gk.betrag
    })