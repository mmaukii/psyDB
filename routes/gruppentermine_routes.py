from flask import Blueprint, request, jsonify
from database import db
from models import Gruppentermin, Gruppe, Termin, GruppenKunde, Kunde
from datetime import datetime
from sqlalchemy import text
from routes.kalender_routes import push_termin

gruppentermine_bp = Blueprint("gruppentermine", __name__)

# --- Alle Gruppentermine ---
@gruppentermine_bp.get("/gruppentermine")
def get_all_gruppentermine():
    gs_list = Gruppentermin.query.order_by(Gruppentermin.datum, Gruppentermin.startzeit).all()
    return jsonify([{
        "id": gs.id,
        "gruppe_id": gs.gruppe_id,
        "datum": gs.datum,
        "startzeit": gs.startzeit,
        "endzeit": gs.endzeit,
        "beschreibung": gs.beschreibung,
        "kommentar": gs.kommentar,
        "betrag": gs.betrag,
        "entfallen": gs.entfallen,
        "timestamp": gs.timestamp,
        "changestamp": gs.changestamp,
        "doku": gs.doku
    } for gs in gs_list])

# --- Alle termine einer bestimmten Gruppe ---
@gruppentermine_bp.get("/gruppen/<int:gruppe_id>/termine")
def get_termine_fuer_gruppe(gruppe_id):
    termine = Gruppentermin.query.filter_by(gruppe_id=gruppe_id)\
        .order_by(Gruppentermin.datum, Gruppentermin.startzeit)\
        .all()

    return jsonify([{
        "id": gs.id,
        "gruppe_id": gs.gruppe_id,
        "datum": gs.datum,
        "startzeit": gs.startzeit,
        "endzeit": gs.endzeit,
        "beschreibung": gs.beschreibung,
        "kommentar": gs.kommentar,
        "betrag": gs.betrag,
        "entfallen": gs.entfallen,
        "timestamp": gs.timestamp,
        "changestamp": gs.changestamp,
        "doku": gs.doku
    } for gs in termine])

# --- Einzelne Gruppentermin ---
@gruppentermine_bp.get("/gruppentermine/<int:id>")
def get_gruppenstunde(id):
    gs = Gruppentermin.query.get_or_404(id)
    return jsonify({
        "id": gs.id,
        "gruppe_id": gs.gruppe_id,
        "datum": gs.datum,
        "startzeit": gs.startzeit,
        "endzeit": gs.endzeit,
        "beschreibung": gs.beschreibung,
        "kommentar": gs.kommentar,
        "betrag": gs.betrag,
        "entfallen": gs.entfallen,
        "timestamp": gs.timestamp,
        "changestamp": gs.changestamp,
        "doku": gs.doku
    })

#--- Gruppentermin löschen -----
@gruppentermine_bp.delete("/gruppentermine/<int:id>")
def delete_gruppenstunde(id):
    gs = Gruppentermin.query.get_or_404(id)

    try:
        db.session.delete(gs)
        db.session.commit()
        return jsonify({"success": True, "deleted_id": id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# --- Neue Gruppentermin ---
@gruppentermine_bp.post("/gruppentermine/<int:gruppe_id>")
def add_gruppenstunde(gruppe_id):
    data = request.get_json()
    
    gs = Gruppentermin(
        gruppe_id=gruppe_id,
        datum=data["datum"],
        startzeit=data["startzeit"],
        endzeit=data["endzeit"],
        beschreibung=data.get("beschreibung"),
        kommentar=data.get("kommentar"),
        betrag=data["betrag"],
        timestamp=datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    )
    db.session.add(gs)
    db.session.flush()  # ID erzeugen, bevor commit

    db.session.commit()

       # 🔄 Push direkt nach Anlage
    print(f"Neue Termin ID {gs.id} to calendar")
    push_termin({
        "gruppentermin_id": gs.id,
        "datum": gs.datum,
        "startzeit": gs.startzeit,
        "endzeit": gs.endzeit,
        "beschreibung": gs.beschreibung,
        "kommentar": gs.kommentar,
        "caldav_uid": None,
        "kuerzel":gs.gruppe.gruppenkuerzel
    })
    return jsonify({"success": True, "id": gs.id}), 201


# --- Gruppentermin ändern ---
@gruppentermine_bp.put("/gruppentermine/<int:id>")
def update_gruppenstunde(id):
    """
    Gruppentermin aktualisieren und alle zugehörigen Kundentermine synchronisieren
    """
    gs = Gruppentermin.query.get_or_404(id)
    data = request.get_json()

    # 1️⃣ Gruppentermin aktualisieren
    for field in ["datum", "startzeit", "endzeit", "beschreibung", "kommentar", "betrag", "entfallen","doku"]:
        if field in data:
            setattr(gs, field, data[field])
    gs.changestamp = datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    db.session.commit()

     # 🔄 Push nur, wenn data.push_termin vorhanden und == 1
    if data.get("push_termin") == 1:
        print(f"Neue Termin ID {gs.id} to calendar")
        push_termin({
            "gruppentermin_id": gs.id,
            "datum": gs.datum,
            "startzeit": gs.startzeit,
            "endzeit": gs.endzeit,
            "beschreibung": gs.beschreibung,
            "kommentar": gs.kommentar,
            "caldav_uid": None,
            "kuerzel": gs.gruppe.gruppenkuerzel
        })
    return jsonify({"success": True, "id": gs.id})

@gruppentermine_bp.get("/gruppentermine/<int:gruppe_id>/termine")
def get_gruppentermine(gruppe_id):
            termine = Gruppentermin.query.filter_by(gruppe_id=gruppe_id)\
                .order_by(Gruppentermin.datum, Gruppentermin.startzeit)\
                .all()

            result = []
            for gs in termine:

                # Teilnehmer: alle Kunden, die in GruppenKunde dieser Gruppe zugeordnet sind, mit Kürzel
                teilnehmer = []
                gruppenkunden = GruppenKunde.query.filter_by(gruppe_id=gs.gruppe_id).all()
                kunden = Kunde.query.all()
                for k in gruppenkunden:
                     print(k.__dict__)
                for k in kunden:
                    print(k.__dict__)
                kunden_ids = [k.id for k in kunden]
                kunden_map = {k.id: k.kuerzel for k in kunden}


                for gk in gruppenkunden:
                    if gk.kunde_id in kunden_ids:
                        teilnehmer.append({
                            "kunde_id": gk.kunde_id,
                            "kuerzel": kunden_map[gk.kunde_id]
                        })

                # Zusätzlich: alle Termine mit gleichem gruppentermin_id (gs.id)
                termine = Termin.query.filter_by(gruppentermin_id=gs.id).all()
                vorhandene_ids = {tn["kunde_id"] for tn in teilnehmer}
                for t in termine:
                    if t.kunde_id in kunden_ids and t.kunde_id not in vorhandene_ids:
                        teilnehmer.append({
                            "kunde_id": t.kunde_id,
                            "kuerzel": kunden_map[t.kunde_id]
                        })
                        vorhandene_ids.add(t.kunde_id)

                

                result.append({
                    "id": gs.id,
                    "gruppe_id": gs.gruppe_id,
                    "datum": gs.datum,
                    "startzeit": gs.startzeit,
                    "endzeit": gs.endzeit,
                    "beschreibung": gs.beschreibung,
                    "kommentar": gs.kommentar,
                    "betrag": gs.betrag,
                    "entfallen": gs.entfallen,
                    "timestamp": gs.timestamp,
                    "changestamp": gs.changestamp,
                    "teilnehmer": teilnehmer  # hier die Liste der Teilnehmer
                })

            return jsonify(result)