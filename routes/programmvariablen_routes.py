# routes/programmvariablen_routes.py

from flask import Blueprint, request, jsonify
from database import db
from models import Programmvariable
from config import use_passphrase_mode, verify_passphrase, set_passphrase, set_new_passphrase
import keyring
from datetime import datetime, timezone
import os
from werkzeug.utils import secure_filename

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
            "checkbox": v.checkbox
        }
        for v in vars if v.name != "db_passphrase_check" and v.sort is not None
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
        "checkbox": v.checkbox
    })

# --- Programmvariable nach Name ---
@programmvariablen_bp.get("/programmvariablen/by-name/<string:name>")
def get_programmvariable_by_name(name):
    v = Programmvariable.query.filter_by(name=name).first_or_404()
    return jsonify({
        "id": v.id,
        "name": v.name,
        "bezeichnung": v.bezeichnung,
        "wert": v.wert
    })

# --- Programmvariable aktualisieren ---
@programmvariablen_bp.put("/programmvariablen/<int:id>")
def update_programmvariable(id):
    v = Programmvariable.query.get_or_404(id)
    data = request.get_json()
    wert_changed = False
    checkbox_changed = False
    if 'wert' in data and data['wert'] != v.wert:
        v.wert = data['wert']
        wert_changed = True
    if 'checkbox' in data and data['checkbox'] != v.checkbox:
        v.checkbox = data['checkbox']
        checkbox_changed = True
    if wert_changed or checkbox_changed:
        v.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        print(f"Programmvariable '{v.name}' aktualisiert: wert={v.wert}, checkbox={v.checkbox}, changestamp={v.changestamp}")
    else:
        print(f"Programmvariable '{v.name}' keine Änderung: wert={v.wert}, checkbox={v.checkbox}")
    db.session.commit()
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
    #print(new_password)
    #print("Payloads für Passphrase-Änderung gesammelt:", [(type(r).__name__, v) for r, v in payloads])
    set_new_passphrase(new_password)
    for record, values in payloads:
        for field, value in values.items():
            #print(f"[DEBUG] Vor setattr: {type(record).__name__} id={getattr(record, 'id', '?')} field={field} value={repr(value)[:80]}")
            setattr(record, field, value)
    db.session.commit()

    set_new_passphrase(new_password)
    return jsonify({"message": "Passwort geändert"})

# --- Programmvariable anlegen ---
@programmvariablen_bp.post("/programmvariablen")
def add_programmvariable():
    data = request.get_json()
    v = Programmvariable(name=data['name'], bezeichnung=data.get('bezeichnung', ''), wert=data.get('wert', ''))
    db.session.add(v)
    db.session.commit()
    return jsonify({"id": v.id}), 201

# --- WebDAV Passwort setzen ---
@programmvariablen_bp.post("/webdav-password")
def set_webdav_password():
    data = request.get_json()
    password = data.get('password')
    if password:
        keyring.set_password("webdav", "user", password)
        return jsonify({"message": "Passwort gespeichert"})
    return jsonify({"error": "Kein Passwort angegeben"}), 400

# --- WebDAV Passwort abrufen ---
@programmvariablen_bp.get("/webdav-password")
def get_webdav_password():
    password = keyring.get_password("webdav", "user")
    return jsonify({"password": password})

# --- Logo-Datei hochladen ---
@programmvariablen_bp.post("/upload-logo")
def upload_logo():
    """
    Hochladen einer Logo-Datei.
    Speichert die Datei in /static/images/ und aktualisiert logo_file Variable.
    """
    print("🔍 Upload-Anfrage erhalten")
    
    if 'file' not in request.files:
        print("❌ Keine Datei im Request")
        return jsonify({"error": "Keine Datei angegeben"}), 400
    
    file = request.files['file']
    print(f"📁 Datei: {file.filename}, Size: {file.content_length}")
    
    if file.filename == '':
        return jsonify({"error": "Keine Datei ausgewählt"}), 400
    
    # Nur Bilddateien erlaubt
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        return jsonify({"error": f"Nur Bilddateien erlaubt (erlaubte: {allowed_extensions})"}), 400
    
    try:
        # Bestimme Pfad zur Static-Datei
        # Der aktuelle Pfad ist: /home/damaurer/Nextcloud/Aktuelles/Datenbank2/routes/programmvariablen_routes.py
        # Wir wollen: /home/damaurer/Nextcloud/Aktuelles/Datenbank2/static/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_dir = os.path.join(base_dir, 'static')
        
        print(f"📂 Static-Verzeichnis: {static_dir}")
        
        # Erstelle Verzeichnis falls nicht vorhanden
        os.makedirs(static_dir, exist_ok=True)
        print(f"✅ Verzeichnis existiert/erstellt")
        
        # Sichere Dateinamen
        filename = secure_filename(file.filename)
        filepath = os.path.join(static_dir, filename)
        
        print(f"💾 Speichere zu: {filepath}")
        
        # Speichere Datei
        file.save(filepath)
        print(f"✅ Datei gespeichert")
        
        # Überprüfe ob Datei existiert
        if os.path.exists(filepath):
            print(f"✅ Datei existiert: {os.path.getsize(filepath)} bytes")
        else:
            print(f"❌ Datei nicht gefunden nach Save!")
            return jsonify({"error": "Datei konnte nicht gespeichert werden"}), 500
        
        # Aktualisiere logo_file Variable in DB
        logo_var = Programmvariable.query.filter_by(name='logo_file').first()
        if not logo_var:
            # Erstelle Variable falls nicht vorhanden
            logo_var = Programmvariable(
                name='logo_file',
                bezeichnung='Logo-Datei für Schreiben',
                wert=''
            )
            db.session.add(logo_var)
            print(f"📚 Neue logo_file Variable erstellt")
        
        # Speichere relativen Pfad
        relative_path = f"/static/{filename}"
        logo_var.wert = relative_path
        db.session.commit()
        print(f"✅ DB aktualisiert: {relative_path}")
        
        return jsonify({
            "success": True,
            "path": relative_path,
            "message": "Logo erfolgreich hochgeladen"
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Fehler beim Upload: {e}")
        print(traceback.format_exc())
        return jsonify({"error": f"Upload fehlgeschlagen: {str(e)}"}), 500