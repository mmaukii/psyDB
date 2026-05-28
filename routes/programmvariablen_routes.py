# routes/programmvariablen_routes.py

from datetime import datetime, timezone
import os

from flask import Blueprint, request, jsonify, send_file
import keyring

from config import use_passphrase_mode, verify_passphrase, set_new_passphrase, refresh_webdav_config
from database import db
from models import Programmvariable


programmvariablen_bp = Blueprint("programmvariablen", __name__)


# --- Alle Programmvariablen ---
@programmvariablen_bp.get("/programmvariablen")
def get_all_programmvariablen():
    vars = Programmvariable.query.order_by(Programmvariable.sort.asc(), Programmvariable.id.asc()).all()
    return jsonify([
        {
            "id": v.id,
            "name": v.name,
            "bezeichnung": v.bezeichnung,
            "wert": v.wert,
            "sort": v.sort,
            "checkbox": v.checkbox,
        }
        for v in vars
        if v.name != "db_passphrase_check" and v.sort is not None
    ])


# --- Einzelne Programmvariable ---
@programmvariablen_bp.get("/programmvariablen/<int:id>")
def get_programmvariable(id):
    v = Programmvariable.query.get_or_404(id)
    return jsonify({
        "id": v.id,
        "name": v.name,
        "bezeichnung": v.bezeichnung,
        "wert": v.wert,
        "checkbox": v.checkbox,
    })


# --- Programmvariable nach Name ---
@programmvariablen_bp.get("/programmvariablen/by-name/<string:name>")
def get_programmvariable_by_name(name):
    v = Programmvariable.query.filter_by(name=name).first_or_404()
    return jsonify({
        "id": v.id,
        "name": v.name,
        "bezeichnung": v.bezeichnung,
        "wert": v.wert,
    })


# --- Programmvariable aktualisieren ---
@programmvariablen_bp.put("/programmvariablen/<int:id>")
def update_programmvariable(id):
    v = Programmvariable.query.get_or_404(id)
    data = request.get_json() or {}
    wert_changed = False
    checkbox_changed = False

    if "wert" in data and data["wert"] != v.wert:
        v.wert = data["wert"]
        wert_changed = True

    if "checkbox" in data and data["checkbox"] != v.checkbox:
        v.checkbox = data["checkbox"]
        checkbox_changed = True

    if wert_changed or checkbox_changed:
        v.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        print(f"Programmvariable '{v.name}' aktualisiert: wert={v.wert}, checkbox={v.checkbox}, changestamp={v.changestamp}")
    else:
        print(f"Programmvariable '{v.name}' keine Änderung: wert={v.wert}, checkbox={v.checkbox}")

    db.session.commit()

    if v.name in {"webdav_user", "webdav_pfad"}:
        refresh_webdav_config()

    return jsonify({"message": "Aktualisiert"})


def _collect_encrypted_payloads():
    from models import Kunde, Gruppe, Termin, Gruppentermin

    payloads = []

    for k in Kunde.query.all():
        payloads.append((k, {
            "nachname": k.nachname,
            "vorname": k.vorname,
            "email": k.email,
            "adresse": k.adresse,
            "ort": k.ort,
            "doku": k.doku,
        }))

    for g in Gruppe.query.all():
        payloads.append((g, {
            "doku": g.doku,
        }))

    for t in Termin.query.all():
        payloads.append((t, {
            "doku": t.doku,
            "pers_doku": t.pers_doku,
        }))

    for gt in Gruppentermin.query.all():
        payloads.append((gt, {
            "doku": gt.doku,
            "pers_doku": gt.pers_doku,
        }))

    return payloads


@programmvariablen_bp.post("/passphrase")
def change_passphrase():
    if not use_passphrase_mode():
        return jsonify({"error": "Passwortmodus ist deaktiviert"}), 400

    data = request.get_json() or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "Aktuelles und neues Passwort erforderlich"}), 400

    if not verify_passphrase(current_password):
        return jsonify({"error": "Aktuelles Passwort ist falsch"}), 403

    payloads = _collect_encrypted_payloads()
    set_new_passphrase(new_password)

    for record, values in payloads:
        for field, value in values.items():
            setattr(record, field, value)

    db.session.commit()
    set_new_passphrase(new_password)

    return jsonify({"message": "Passwort geändert"})


# --- Programmvariable anlegen ---
@programmvariablen_bp.post("/programmvariablen")
def add_programmvariable():
    data = request.get_json() or {}
    v = Programmvariable(name=data["name"], bezeichnung=data.get("bezeichnung", ""), wert=data.get("wert", ""))
    db.session.add(v)
    db.session.commit()
    return jsonify({"id": v.id}), 201


# --- WebDAV Passwort setzen ---
@programmvariablen_bp.post("/webdav-password")
def set_webdav_password():
    data = request.get_json() or {}
    password = data.get("password")

    if password:
        keyring.set_password("webdav", "user", password)
        refresh_webdav_config()
        return jsonify({"message": "Passwort gespeichert"})

    return jsonify({"error": "Kein Passwort angegeben"}), 400


# --- WebDAV Passwort abrufen ---
@programmvariablen_bp.get("/webdav-password")
def get_webdav_password():
    password = keyring.get_password("webdav", "user")
    return jsonify({"password": password})


# --- Aktuelles Logo als Bild ausliefern ---
@programmvariablen_bp.get("/logo-file")
def get_logo_file():
    logo_var = Programmvariable.query.filter_by(name="logo_file").first()
    if not logo_var or not logo_var.wert:
        return jsonify({"error": "Kein Logo hinterlegt"}), 404

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    normalized_path = logo_var.wert.replace("\\", "/").lstrip("/")
    absolute_path = os.path.abspath(os.path.join(base_dir, normalized_path))

    # Schützt vor Pfadmanipulation außerhalb des Projektordners.
    if not absolute_path.startswith(base_dir):
        return jsonify({"error": "Ungültiger Logo-Pfad"}), 400

    if not os.path.exists(absolute_path):
        return jsonify({"error": "Logo-Datei nicht gefunden"}), 404

    return send_file(absolute_path)


# --- Logo-Datei hochladen ---
@programmvariablen_bp.post("/upload-logo")
def upload_logo():
    if "file" not in request.files:
        return jsonify({"error": "Keine Datei angegeben"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Keine Datei ausgewählt"}), 400

    allowed_extensions = {"png", "jpg", "jpeg", "jpe"}
    file_ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if file_ext not in allowed_extensions:
        return jsonify({"error": "Nur PNG oder JPEG erlaubt"}), 400

    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vorlagen_dir = os.path.join(base_dir, "Vorlagen")
        os.makedirs(vorlagen_dir, exist_ok=True)

        target_filename = "logo_praxis.png" if file_ext == "png" else "logo_praxis.jpeg"
        target_path = os.path.join(vorlagen_dir, target_filename)
        alternate_path = os.path.join(
            vorlagen_dir,
            "logo_praxis.jpeg" if target_filename.endswith(".png") else "logo_praxis.png",
        )

        file.save(target_path)
        if not os.path.exists(target_path):
            return jsonify({"error": "Datei konnte nicht gespeichert werden"}), 500

        if os.path.exists(alternate_path):
            os.remove(alternate_path)

        logo_var = Programmvariable.query.filter_by(name="logo_file").first()
        if not logo_var:
            logo_var = Programmvariable(
                name="logo_file",
                bezeichnung="Logo-Datei für Schreiben",
                wert="",
            )
            db.session.add(logo_var)

        relative_path = f"Vorlagen/{target_filename}"
        logo_var.wert = relative_path
        logo_var.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        db.session.commit()

        return jsonify({
            "success": True,
            "path": relative_path,
            "message": "Logo erfolgreich hochgeladen",
        })

    except Exception as e:
        return jsonify({"error": f"Upload fehlgeschlagen: {str(e)}"}), 500
