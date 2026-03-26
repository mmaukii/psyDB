# routes/termine_routes.py

from flask import Blueprint, request, jsonify
from database import db
from datetime import datetime, timezone
from models import Termin, Kunde, TermineRechnung, Gruppentermin, Gruppe, Rechnung
from routes.kalender_routes import push_termin
from sqlalchemy import desc, asc




termine_bp = Blueprint("termine", __name__)

# --- Alle Termine die nicht nur offline gelöscht wurden ---
@termine_bp.get("/termine")
def get_all_termine():
    termine = Termin.query.filter(Termin.nur_offline_geloescht == 0).order_by(Termin.datum.desc(), Termin.utc_starttime).all()
    return jsonify([{
        "id": s.id,
        "kunde_id": s.kunde_id,
        "datum": s.datum,
        "utc_starttime": s.utc_starttime,
        "utc_endtime": s.utc_endtime,
        "beschreibung": s.beschreibung,
        "kommentar": s.kommentar,
        "betrag": s.betrag,
        "abgesagt": s.abgesagt,
        "timestamp": s.timestamp,
        "changestamp": s.changestamp,
        "gruppentermin_id": s.gruppentermin_id,
        "doku": s.doku,
        "pers_doku": s.pers_doku
    } for s in termine])

# --- Alle Termine die  nur offline gelöscht wurden ---
@termine_bp.get("/termine_nur_offline_geloescht")
def get_all_termine_nur_offline_geloescht():
    termine = Termin.query.filter(Termin.nur_offline_geloescht == 1).order_by(Termin.datum.desc(), Termin.utc_starttime).all()
    return jsonify([{
        "id": s.id,
        "kunde_id": s.kunde_id,
        "datum": s.datum,
        "utc_starttime": s.utc_starttime,
        "utc_endtime": s.utc_endtime,
        "beschreibung": s.beschreibung,
        "kommentar": s.kommentar,
        "betrag": s.betrag,
        "abgesagt": s.abgesagt,
        "timestamp": s.timestamp,
        "changestamp": s.changestamp,
        "gruppentermin_id": s.gruppentermin_id,
        "doku": s.doku,
        "pers_doku": s.pers_doku
    } for s in termine])

# --- Termine nach Kunde die nicht nur_offline_geloescht---
@termine_bp.get("/termine/kunde/<int:kunde_id>")
def get_termine_by_kunde(kunde_id):
    termine = Termin.query.filter_by(kunde_id=kunde_id).filter(Termin.nur_offline_geloescht == 0).order_by(Termin.datum.desc(), Termin.utc_starttime).all()
    return jsonify([{
        "id": s.id,
        "kunde_id": s.kunde_id,
        "datum": s.datum,
        "utc_starttime": s.utc_starttime,
        "utc_endtime": s.utc_endtime,
        "beschreibung": s.beschreibung,
        "kommentar": s.kommentar,
        "betrag": s.betrag,
        "abgesagt": s.abgesagt,
        "timestamp": s.timestamp,
        "changestamp": s.changestamp,
        "gruppentermin_id": s.gruppentermin_id,
        "doku": s.doku,
        "pers_doku": s.pers_doku
    } for s in termine])

# --- Einzelne Termin ---
@termine_bp.get("/termine/<int:id>")
def get_stunde(id):
    s = Termin.query.get_or_404(id)
    return jsonify({
        "id": s.id,
        "kunde_id": s.kunde_id,
        "datum": s.datum,
        "utc_starttime": s.utc_starttime,
        "utc_endtime": s.utc_endtime,
        "beschreibung": s.beschreibung,
        "kommentar": s.kommentar,
        "betrag": s.betrag,
        "abgesagt": s.abgesagt,
        "timestamp": s.timestamp,
        "changestamp": s.changestamp,
        "gruppentermin_id": s.gruppentermin_id,
        "doku": s.doku,
        "pers_doku": s.pers_doku
    })

# --- Termin anlegen ---
@termine_bp.post("/termine")
def add_stunde():
    data = request.get_json()
    print("Termin anlegen:", data)

    s = Termin(
        kunde_id=data["kunde_id"],
        datum=data["datum"],
        utc_starttime=data.get("utc_starttime"),
        utc_endtime=data.get("utc_endtime"),
        beschreibung=data.get("beschreibung"),
        kommentar=data.get("kommentar"),
        betrag=data["betrag"],
        abgesagt=data.get("abgesagt"),
        timestamp=datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"),
        gruppentermin_id=data.get("gruppentermin_id"),
    )

    db.session.add(s)
    db.session.commit()
    return jsonify({"success": True, "id": s.id}), 201

# --- Termine anlegen mit Kunden-ID ---
@termine_bp.post("/termine/<int:kunde_id>")
def add_stunde_mit_kunde(kunde_id):
    data = request.get_json()
    print("Termin anlegen mit Kunde ID:", kunde_id)


    s = Termin(
        kunde_id=kunde_id,
        datum=data["datum"],
        utc_starttime=data.get("utc_starttime"),
        utc_endtime=data.get("utc_endtime"),
        beschreibung=data.get("beschreibung"),
        kommentar=data.get("kommentar"),
        betrag=data["betrag"],
        timestamp=datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"),
        gruppentermin_id=data.get("gruppentermin_id"),
        nur_offline_vorhanden=0
    )

    db.session.add(s)
    db.session.commit()

    print(f"Neuer Termin ID {s.id} to calendar")
    event = {
        "id": s.id,
        "title": f"{s.kunde.kuerzel}",
        "start": f"{s.datum}T{s.utc_starttime}",
        "end": f"{s.datum}T{s.utc_endtime}",
        "beschreibung": s.beschreibung,
        "kommentar": s.kommentar,
        "abgesagt": s.abgesagt,
        "caldav_uid": None
    }

    try:
        push_termin({
            "termin_id": s.id,
            "datum": s.datum,
            "utc_starttime": s.utc_starttime,
            "utc_endtime": s.utc_endtime,
            "beschreibung": s.beschreibung,
            "kommentar": s.kommentar,
            "abgesagt": s.abgesagt,
            "caldav_uid": None,
            "kuerzel": s.kunde.kuerzel
        })
    except Exception as e:
        print(f"Push Termin fehlgeschlagen, nur_offline_vorhanden wird auf 1 gesetzt: {e}")
        s.nur_offline_vorhanden = 1
        db.session.commit()

    return jsonify(event), 201


# --- Termin ändern ---
@termine_bp.put("/termine/<int:id>")
def update_stunde(id):
    s = Termin.query.get_or_404(id)
    data = request.get_json()
    print(f"Received data for updating Termin ID {id}: {data}")
    for field in [
        "kunde_id", "datum", "utc_starttime", "utc_endtime",
        "beschreibung", "kommentar", "betrag",
        "abgesagt", "timestamp", "changestamp", "gruppentermin_id","doku","pers_doku"
    ]:
        if field in data:
            #print(f"Updating field {field} to {data[field]}")
            setattr(s, field, data[field])

    # changestamp immer setzen
    print("zeitpunkt aus Funktion", datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"))

    s.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    print("zeitpunkt changestamp:", s.changestamp)
    print("zeitpunkt aus Funktion", datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"))

    db.session.commit()

    # 🔄 Push direkt nach Anlage
     # 🔄 Push nur, wenn data.push_termin vorhanden und == 1
    if data.get("push_termin") == 1:
        print(f"Pushing updated Termin ID {s.id} to calendar")
        push_termin({
            "termin_id": s.id,
            "datum": s.datum,
            "utc_starttime": s.utc_starttime,
            "utc_endtime": s.utc_endtime,
            "beschreibung": s.beschreibung,
            "kommentar": s.kommentar,
            "abgesagt": s.abgesagt,
            "caldav_uid": None,
            "kuerzel":s.kunde.kuerzel
        })

    return jsonify({"success": True})

# --- Termin löschen ---
@termine_bp.delete("/termine/<int:id>")
def delete_stunde(id):
    s = Termin.query.get_or_404(id)
    # Event im Kalender löschen, falls vorhanden
    online_delete_ok = True
    if s.caldav_uid:
        try:
            from routes.kalender_routes import get_termin_calendar
            cal = get_termin_calendar()
            event = cal.event_by_uid(s.caldav_uid)
            event.delete()
            print(f"✅ Event {s.caldav_uid} aus WebDAV gelöscht")
        except Exception as e:
            print(f"⚠️ Event {s.caldav_uid} nicht im WebDAV gefunden (oder Fehler beim Löschen): {str(e)}")
            online_delete_ok = False

    if online_delete_ok:
        db.session.delete(s)
        db.session.commit()
        return jsonify({"success": True})
    else:
        s.nur_offline_geloescht = 1
        db.session.commit()
        return jsonify({"success": False, "error": "Konnte online nicht gelöscht werden, nur_offline_geloescht=1"})

# --- Termine mit aktivem Kunden, nicht abgesagt und nicht in Rechnung ---
@termine_bp.get("/termine/nicht-abgesagt-aktive-kunde-nicht-in-rechnung")
def get_termine_nicht_in_rechnung_nicht_abgesagt_kunde_aktiv():
    result = (
        db.session.query(
            Termin.id,
            Termin.datum,
            Termin.utc_starttime,
            Termin.utc_endtime,
            Termin.betrag,
            Termin.gruppentermin_id,
            Termin.beschreibung,
            Kunde.vorname,
            Kunde.nachname,
            Kunde.kuerzel,
            Kunde.id.label("kundeId"),
            Gruppe.gruppenkuerzel
        )
        .join(Kunde, Termin.kunde_id == Kunde.id)

        # ⬇️ WICHTIG: OUTER JOIN statt JOIN
        .outerjoin(Gruppentermin, Termin.gruppentermin_id == Gruppentermin.id)
        .outerjoin(Gruppe, Gruppentermin.gruppe_id == Gruppe.id)

        .outerjoin(
            TermineRechnung,
            TermineRechnung.termin_id == Termin.id
        )
        .filter(Kunde.aktiv == 1)
        .filter((Termin.abgesagt == 0) | (Termin.abgesagt.is_(None)))
        .filter(TermineRechnung.id.is_(None))
        .order_by(Termin.datum.desc(), Termin.utc_starttime)
        .all()
    )

    return jsonify([
        {
            "id": r.id,
            "datum": r.datum,
            "utc_starttime": r.utc_starttime,
            "utc_endtime": r.utc_endtime,
            "betrag": r.betrag,
            "vorname": r.vorname,
            "nachname": r.nachname,
            "kuerzel": r.kuerzel,
            "kundeId": r.kundeId,
            "gruppentermin_id": r.gruppentermin_id,
            "beschreibung": r.beschreibung,
            "gruppenkuerzel": r.gruppenkuerzel or ""
        }
        for r in result
    ])

# --- Termine mit aktivem Kunden,  abgesagt und nicht abgesagte und nicht in Rechnung ---
@termine_bp.get("/termine/aktive-kunde-nicht-in-rechnung")
def get_termine_nicht_in_rechnung_kunde_aktiv():
    result = (
        db.session.query(
            Termin.id,
            Termin.datum,
            Termin.utc_starttime,
            Termin.utc_endtime,
            Termin.betrag,
            Termin.gruppentermin_id,
            Termin.beschreibung,
            Termin.abgesagt,
            Kunde.vorname,
            Kunde.nachname,
            Kunde.kuerzel,
            Kunde.id.label("kundeId"),
            Gruppe.gruppenkuerzel
        )
        .join(Kunde, Termin.kunde_id == Kunde.id)

        # ⬇️ WICHTIG: OUTER JOIN statt JOIN
        .outerjoin(Gruppentermin, Termin.gruppentermin_id == Gruppentermin.id)
        .outerjoin(Gruppe, Gruppentermin.gruppe_id == Gruppe.id)

        .outerjoin(
            TermineRechnung,
            TermineRechnung.termin_id == Termin.id
        )

        .filter(Kunde.aktiv == 1)
        .filter(TermineRechnung.id.is_(None))
        .order_by(Termin.datum.desc(), Termin.utc_starttime)
        .all()
    )

    return jsonify([
        {
            "id": r.id,
            "datum": r.datum,
            "utc_starttime": r.utc_starttime,
            "utc_endtime": r.utc_endtime,
            "betrag": r.betrag,
            "vorname": r.vorname,
            "nachname": r.nachname,
            "kuerzel": r.kuerzel,
            "kundeId": r.kundeId,
            "gruppentermin_id": r.gruppentermin_id,
            "beschreibung": r.beschreibung,
            "gruppenkuerzel": r.gruppenkuerzel or "",
            "abgesagt": r.abgesagt
        }
        for r in result
    ])


# --- Termine mit aktivem Kunden, nicht abgesagt und nicht in Rechnung ---
@termine_bp.get("/termine/nicht-abgesagt-aktive-kunde")
def get_termine_nicht_abgesagt_kunde_aktiv():
    result = (
        db.session.query(
            Termin.id,
            Termin.datum,
            Termin.utc_starttime,
            Termin.utc_endtime,
            Termin.betrag,
            Termin.beschreibung,
            Termin.gruppentermin_id,
            Kunde.vorname,
            Kunde.nachname,
            Kunde.kuerzel,
            Kunde.id.label("kundeId")
        )
        .join(Kunde, Termin.kunde_id == Kunde.id)
        .outerjoin(
            TermineRechnung,
            TermineRechnung.termin_id == Termin.id
        )
        .filter(Kunde.aktiv == 1)
        .filter((Termin.abgesagt == 0) | (Termin.abgesagt.is_(None)))
        .order_by(desc(Termin.datum), desc(Termin.utc_starttime))
        .all()
    )

    return jsonify([
        {
            "id": r.id,
            "datum": r.datum,
            "utc_starttime": r.utc_starttime,
            "utc_endtime": r.utc_endtime,
            "betrag": r.betrag,
            "beschreibung": r.beschreibung,
            "vorname": r.vorname,
            "nachname": r.nachname,
            "kuerzel": r.kuerzel,
            "kundeId": r.kundeId,
            "gruppentermin_id": r.gruppentermin_id
        }
        for r in result
    ])

# --- Termine mit  Kunden und rechnungsnummer
@termine_bp.get("/termine/kunde_rnr/<int:kunde_id>")
def get_termine_kunde_rnr(kunde_id):
    result = (
        db.session.query(
            Termin.id,
            Termin.datum,
            Termin.utc_starttime,
            Termin.utc_endtime,
            Termin.betrag,
            Termin.beschreibung,
            Termin.gruppentermin_id,
            Termin.abgesagt,
            Termin.changestamp,
            Termin.timestamp,
            Kunde.vorname,
            Kunde.nachname,
            Kunde.kuerzel,
            Kunde.id.label("kundeId"),
            Rechnung.rechnungsnr
        )
        .join(Kunde, Termin.kunde_id == Kunde.id)
        .outerjoin(TermineRechnung, TermineRechnung.termin_id == Termin.id)
        .outerjoin(Rechnung, Rechnung.id == TermineRechnung.rechnung_id)
        .filter(Termin.kunde_id == kunde_id)
        .filter(Termin.nur_offline_geloescht == 0)
        .order_by(desc(Termin.datum), desc(Termin.utc_starttime))
        .all()
    )

    return jsonify([
        {
            "id": r.id,
            "kundeId": r.kundeId,
            "datum": r.datum,
            "utc_starttime": r.utc_starttime,
            "utc_endtime": r.utc_endtime,
            "betrag": r.betrag,
            "abgesagt": r.abgesagt,
            "changesstamp": r.changestamp,
            "timestamp": r.timestamp,
            "beschreibung": r.beschreibung,
            "vorname": r.vorname,
            "nachname": r.nachname,
            "kuerzel": r.kuerzel,
            "kundeId": r.kundeId,
            "gruppentermin_id": r.gruppentermin_id,
            "rechnungsnr": r.rechnungsnr
        }
        for r in result
    ])

