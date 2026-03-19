# routes/kunden_routes.py

from flask import Blueprint, request, jsonify
from database import db
from models import Kunde, GruppenKunde, Gruppe

kunden_bp = Blueprint("kunden", __name__)

# --- Alle Kunden ---
@kunden_bp.get("/kunden")
def get_all_kunden():
    kunden = Kunde.query.order_by(Kunde.nachname).all()
    return jsonify([{
        "id": k.id,
        "nachname": k.nachname,
        "vorname": k.vorname,
        "email": k.email,
        "adresse": k.adresse,
        "plz": k.plz,
        "ort": k.ort,
        "stundensatz": k.stundensatz,
        "kuerzel": k.kuerzel,
        "geschlecht": k.geschlecht,
        "gebdatum": k.gebdatum,
        "ust": k.ust,
        "rechnungTextObenVorgabe": k.rechnungTextObenVorgabe,
        "rechnungTextUntenVorgabe": k.rechnungTextUntenVorgabe,
        "doku": k.doku,
        "standort_id": k.standort_id,
        "druckvorlage_id": k.druckvorlage_id,
        "therapieform": k.therapieform,
        "aktiv": k.aktiv,
        "svnr": k.svnr,
        "krankenkasse": k.krankenkasse,
        "diagnose": k.diagnose
    } for k in kunden])

# --- aktive Kunden ---
@kunden_bp.get("/kunden/aktiv")
def get_aktive_kunden():
    kunden = Kunde.query.filter_by(aktiv=1).order_by(Kunde.nachname).all()
    return jsonify([{
        "id": k.id,
        "nachname": k.nachname,
        "vorname": k.vorname,
        "email": k.email,
        "adresse": k.adresse,
        "plz": k.plz,
        "ort": k.ort,
        "stundensatz": k.stundensatz,
        "kuerzel": k.kuerzel,
        "geschlecht": k.geschlecht,
        "gebdatum": k.gebdatum,
        "ust": k.ust,
        "rechnungTextObenVorgabe": k.rechnungTextObenVorgabe,
        "rechnungTextUntenVorgabe": k.rechnungTextUntenVorgabe,
        "doku": k.doku,
        "standort_id": k.standort_id,
        "druckvorlage_id": k.druckvorlage_id,
        "therapieform": k.therapieform,
        "aktiv": k.aktiv,
        "svnr": k.svnr,
        "krankenkasse": k.krankenkasse,
        "diagnose": k.diagnose
    } for k in kunden])

# --- inaktive Kunden ---
@kunden_bp.get("/kunden/inaktiv")
def get_inaktive_kunden():      
    kunden = Kunde.query.filter_by(aktiv=0).order_by(Kunde.nachname).all()
    return jsonify([{
        "id": k.id,
        "nachname": k.nachname,
        "vorname": k.vorname,
        "email": k.email,
        "adresse": k.adresse,
        "plz": k.plz,
        "ort": k.ort,
        "stundensatz": k.stundensatz,
        "kuerzel": k.kuerzel,
        "geschlecht": k.geschlecht,
        "gebdatum": k.gebdatum,
        "ust": k.ust,
        "rechnungTextObenVorgabe": k.rechnungTextObenVorgabe,
        "rechnungTextUntenVorgabe": k.rechnungTextUntenVorgabe,
        "doku": k.doku,
        "standort_id": k.standort_id,
        "druckvorlage_id": k.druckvorlage_id,
        "therapieform": k.therapieform,
        "aktiv": k.aktiv,
        "svnr": k.svnr,
        "krankenkasse": k.krankenkasse,
        "diagnose": k.diagnose
    } for k in kunden])

# --- Einzelner Kunde ---
@kunden_bp.get("/kunden/<int:id>")
def get_kunde(id):
    k = Kunde.query.get_or_404(id)
    return jsonify({
        "id": k.id,
        "nachname": k.nachname,
        "vorname": k.vorname,
        "email": k.email,
        "adresse": k.adresse,
        "plz": k.plz,
        "ort": k.ort,
        "stundensatz": k.stundensatz,
        "kuerzel": k.kuerzel,
        "geschlecht": k.geschlecht,
        "gebdatum": k.gebdatum,
        "ust": k.ust,
        "rechnungTextObenVorgabe": k.rechnungTextObenVorgabe,
        "rechnungTextUntenVorgabe": k.rechnungTextUntenVorgabe,
        "doku": k.doku,
        "standort_id": k.standort_id,
        "druckvorlage_id": k.druckvorlage_id,
        "therapieform": k.therapieform,
        "aktiv": k.aktiv,
        "svnr": k.svnr,
        "krankenkasse": k.krankenkasse,
        "diagnose": k.diagnose
    })

# --- Kunde anlegen ---
@kunden_bp.post("/kunden")
def add_kunde():
    data = request.get_json()

    kuerzel = data.get("kuerzel")
    if not kuerzel:
        return jsonify({"success": False, "error": "Kürzel ist erforderlich"}), 400
    exists = Kunde.query.filter_by(kuerzel=kuerzel).first()
    if exists:
        return jsonify({"success": False, "error": "Kürzel bereits vergeben"}), 409

    from datetime import datetime
    k = Kunde(
        nachname=data["nachname"],
        vorname=data.get("vorname"),
        email=data.get("email"),
        adresse=data.get("adresse"),
        plz=data.get("plz"),
        ort=data.get("ort"),
        stundensatz=data.get("stundensatz"),
        kuerzel=kuerzel,
        geschlecht=data.get("geschlecht"),
        gebdatum=data.get("gebdatum"),
        ust=data.get("ust", 0),
        rechnungTextObenVorgabe=data.get("rechnungTextObenVorgabe"),
        rechnungTextUntenVorgabe=data.get("rechnungTextUntenVorgabe"),
        doku=data.get("doku"),
        standort_id=data["standort_id"],
        druckvorlage_id=data.get("druckvorlage_id"),
        therapieform=data["therapieform"],
        aktiv=data.get("aktiv", 1),
        svnr=data.get("svnr"),
        krankenkasse=data.get("krankenkasse"),
        diagnose=data.get("diagnose"),
        timestamp=datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    )

    db.session.add(k)
    db.session.commit()
    return jsonify({"success": True, "id": k.id}), 201

# --- Kunde ändern ---
@kunden_bp.put("/kunden/<int:id>")
def update_kunde(id):
    k = Kunde.query.get_or_404(id)
    data = request.get_json()

    if "kuerzel" in data:
        kuerzel = data.get("kuerzel")
        if not kuerzel:
            return jsonify({"success": False, "error": "Kürzel ist erforderlich"}), 400
        if kuerzel != k.kuerzel:
            exists = Kunde.query.filter_by(kuerzel=kuerzel).first()
            if exists:
                return jsonify({"success": False, "error": "Kürzel bereits vergeben"}), 409

    for field in [
        "nachname","vorname","email","adresse","plz","ort",
        "stundensatz","kuerzel","geschlecht","gebdatum","ust",
        "rechnungTextObenVorgabe","rechnungTextUntenVorgabe",
        "doku","standort_id","druckvorlage_id","therapieform","aktiv",
        "svnr","krankenkasse","diagnose"
    ]:
        if field in data:
            setattr(k, field, data[field])

    db.session.commit()
    return jsonify({"success": True})

# --- Kunde löschen ---
@kunden_bp.delete("/kunden/<int:id>")
def delete_kunde(id):
    k = Kunde.query.get_or_404(id)
    from models import Termin, Rechnung, TermineRechnung
    # Alle zugehörigen Termine finden
    termine = Termin.query.filter_by(kunde_id=k.id).all()
    termin_ids = [t.id for t in termine]

    # Alle Zuordnungen in TermineRechnung löschen und Rechnungen sammeln
    rechnungs_ids = set()
    for termin_id in termin_ids:
        zuordnungen = TermineRechnung.query.filter_by(termin_id=termin_id).all()
        for z in zuordnungen:
            rechnungs_ids.add(z.rechnung_id)
            db.session.delete(z)

    # Alle Termine löschen
    for t in termine:
        db.session.delete(t)

    # Rechnungen löschen, die nur noch mit gelöschten Terminen verknüpft sind
    from models import Mahnung
    for rid in rechnungs_ids:
        # Prüfe, ob noch Zuordnungen zu anderen Terminen existieren
        rest = TermineRechnung.query.filter_by(rechnung_id=rid).count()
        if rest == 0:
            r = Rechnung.query.get(rid)
            if r:
                # Mahnungen zur Rechnung löschen
                Mahnung.query.filter_by(rechnung_id=rid).delete(synchronize_session=False)
                db.session.delete(r)

    db.session.delete(k)
    db.session.commit()
    return jsonify({"success": True})

# --- Kunden einer Gruppe ---
@kunden_bp.get("/kunden/<int:gruppe_id>/gruppe")
def get_kunden_einer_gruppe(gruppe_id):
    kunden = (
        db.session.query(
            Kunde.id,
            Kunde.vorname,
            Kunde.nachname,
            Kunde.kuerzel,
            GruppenKunde.betrag
        )
        .join(GruppenKunde, GruppenKunde.kunde_id == Kunde.id)
        .filter(GruppenKunde.gruppe_id == gruppe_id)
        .all()
    )

    return jsonify([
        {
            "id": k.id,
            "vorname": k.vorname,
            "nachname": k.nachname,
            "kuerzel": k.kuerzel,
            "betrag": k.betrag
        }
        for k in kunden
    ])

# --- Gruppen eines Kunden ---
@kunden_bp.get("/kunden/<int:kunde_id>/gruppen")
def get_gruppen_eines_kunden(kunde_id):
    gruppen = (
        db.session.query(
            Gruppe.id,
            Gruppe.gruppenname,
            Gruppe.gruppenkuerzel,
            GruppenKunde.betrag
        )
        .join(GruppenKunde, GruppenKunde.gruppe_id == Gruppe.id)
        .filter(GruppenKunde.kunde_id == kunde_id)
        .all()
    )

    return jsonify([
        {
            "id": g.id,
            "gruppenname": g.gruppenname,
            "gruppenkuerzel": g.gruppenkuerzel,
            "betrag": g.betrag
        }
        for g in gruppen
    ])

# -------------------------------------------------
# Kunden-Gruppen für einen Kunden aktualisieren
# -------------------------------------------------
@kunden_bp.put("/kunden/<int:kunde_id>/gruppen")
def update_kunden_gruppen(kunde_id):
    """
    Erwartet JSON:
    {
        "gruppen_ids": [1, 2, 3]  # alle Gruppen, in denen der Kunde sein soll
    }
    """
    data = request.get_json()
    neue_gruppen_ids = set(data.get("gruppen_ids", []))

    # Aktuelle Gruppen des Kunden
    aktuelle_gruppen = {gk.gruppe_id for gk in GruppenKunde.query.filter_by(kunde_id=kunde_id).all()}

    # Gruppen hinzufügen, in denen Kunde noch nicht ist
    hinzuzufuegen = neue_gruppen_ids - aktuelle_gruppen
    for gruppe_id in hinzuzufuegen:
        db.session.add(GruppenKunde(kunde_id=kunde_id, gruppe_id=gruppe_id))

    # Gruppen entfernen, aus denen Kunde raus soll
    zu_entfernen = aktuelle_gruppen - neue_gruppen_ids
    if zu_entfernen:
        GruppenKunde.query.filter(
            GruppenKunde.kunde_id == kunde_id,
            GruppenKunde.gruppe_id.in_(zu_entfernen)
        ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({"success": True})