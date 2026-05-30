
from flask import Blueprint, Flask, render_template, request, redirect, url_for, render_template_string, jsonify, make_response, send_from_directory
import sqlite3
from datetime import date, datetime, timedelta, timezone
from database import db
import os
import logging
import signal
import shutil
import threading
import subprocess
import sys
from logging.handlers import TimedRotatingFileHandler
from routes import kunden_bp, standorte_bp, termine_bp, rechnungen_bp, kalender_bp, gruppen_bp, gruppentermine_bp, gruppenkunden_bp ,  mahnungen_bp, programmvariablen_bp, dashboard_bp, druckvorlagen_bp, doku_bp, leistungen_bp
from routes.auswertung_routes import auswertung_bp
from services.backup_service import backup_sqlite_db
from config import DB_FILE, MAX_BACKUPS, set_passphrase, use_passphrase_mode, is_encryption_ready, verify_passphrase, is_passphrase_initialized, set_new_passphrase, should_force_passphrase_prompt, mark_passphrase_prompt_done  # <-- import aus ini
import time
from models import Rechnung, Mahnung, Termin, Kunde, Leistung, Druckvorlage

app = Flask(__name__)


def configure_logging(flask_app):
    # Hinweis: Konkrete Log-Ausgaben (info/warning/error) in den jeweiligen Ablaufen noch erganzen.
    handler = TimedRotatingFileHandler(
        "app.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    if not any(isinstance(existing_handler, TimedRotatingFileHandler) for existing_handler in flask_app.logger.handlers):
        flask_app.logger.addHandler(handler)
    flask_app.logger.setLevel(logging.INFO)


configure_logging(app)


@app.before_request
def require_unlock():
    if not use_passphrase_mode():
        return
    if is_encryption_ready() and not should_force_passphrase_prompt():
        return
    if request.path.startswith("/static/"):
        return
    if request.path in ("/favicon.ico", "/psyDB.ico"):
        return
    if request.path.startswith("/unlock"):
        return
    return redirect(url_for("unlock", next=request.path))

# SQLAlchemy konfigurieren
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_FILE}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


def migrate_rechnungsnr_to_text_if_needed():
    """Migriert rechnungsnr auf TEXT, damit führende Nullen erhalten bleiben."""
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rechnungen'")
        if not cur.fetchone():
            return

        cur.execute("PRAGMA table_info(rechnungen)")
        columns = cur.fetchall()
        rechnungsnr_info = next((col for col in columns if col[1] == "rechnungsnr"), None)
        if not rechnungsnr_info:
            return

        rechnungsnr_type = str(rechnungsnr_info[2] or "").strip().lower()
        if "text" in rechnungsnr_type or "char" in rechnungsnr_type:
            return

        cur.execute("PRAGMA foreign_keys=OFF")
        conn.execute("BEGIN")

        cur.execute(
            """
            CREATE TABLE rechnungen_new (
                id INTEGER NOT NULL PRIMARY KEY,
                datum VARCHAR,
                betrag FLOAT,
                rechnungsnr TEXT UNIQUE,
                bezahlt INTEGER,
                rechnungTextOben VARCHAR,
                rechnungTextUnten VARCHAR,
                kommentar VARCHAR,
                timestamp VARCHAR,
                changestamp VARCHAR,
                zahlungsziel_tage INTEGER,
                zahlungsverweis VARCHAR
            )
            """
        )

        cur.execute(
            """
            SELECT
                id, datum, betrag, rechnungsnr, bezahlt,
                rechnungTextOben, rechnungTextUnten, kommentar,
                timestamp, changestamp, zahlungsziel_tage, zahlungsverweis
            FROM rechnungen
            """
        )
        rows = cur.fetchall()

        insert_sql = (
            "INSERT INTO rechnungen_new "
            "(id, datum, betrag, rechnungsnr, bezahlt, rechnungTextOben, rechnungTextUnten, kommentar, "
            "timestamp, changestamp, zahlungsziel_tage, zahlungsverweis) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )

        for row in rows:
            nr = row[3]
            nr_text = None
            if nr is not None:
                nr_text = str(nr).strip()
                if nr_text.isdigit() and len(nr_text) < 5:
                    nr_text = nr_text.zfill(5)

            cur.execute(insert_sql, (
                row[0], row[1], row[2], nr_text, row[4],
                row[5], row[6], row[7], row[8], row[9], row[10], row[11]
            ))

        cur.execute("DROP TABLE rechnungen")
        cur.execute("ALTER TABLE rechnungen_new RENAME TO rechnungen")

        conn.commit()
        cur.execute("PRAGMA foreign_keys=ON")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

with app.app_context():
    db.create_all()
    migrate_rechnungsnr_to_text_if_needed()
    # Initiale Programmvariablen einfügen, falls nicht vorhanden
    from models import Programmvariable
    from models import Standort
    # Dummy-Standort anlegen, falls keiner existiert
    if not Standort.query.first():
        dummy = Standort(
            name='Dummy',
            adresse='xx',
            plz='xx',
            ort='xx',
            email='dummy@example.com',
            kuerzel='XX',
            bic='xx',
            iban='xx',
            kontoName='dummy',
            bankname='dummy',
            timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            standard=1
        )
        db.session.add(dummy)
        db.session.commit()
    programmvariable_defaults = [
        {'name': 'webdav_pfad', 'wert': '', 'bezeichnung': 'Pfad für Webdav', 'sort': 204, 'checkbox': False},
        {'name': 'webdav_user', 'wert': '', 'bezeichnung': 'WebDAV Benutzer', 'sort': 205, 'checkbox': False},
        {'name': 'mahnspesen', 'wert': '5', 'bezeichnung': 'Mahnspesen', 'sort': 102, 'checkbox': False},
        {'name': 'verzugszinsen_proz', 'wert': '4', 'bezeichnung': 'Verzugszinsen in %', 'sort': 103, 'checkbox': False},
        {'name': 'zahlungsziel_tage_rechnung', 'wert': '14', 'bezeichnung': 'Zahlungsziel Tage für Rechnungen', 'sort': 100, 'checkbox': False},
        {'name': 'zahlungsziel_tage_mahnung', 'wert': '14', 'bezeichnung': 'Zahlungsziel Tage für Mahnungen', 'sort': 101, 'checkbox': False},
        {'name': 'termine_kalender', 'wert': 'praxis', 'bezeichnung': 'Webdav Kalender für Termine', 'sort': 202, 'checkbox': False},
        {'name': 'andere_kalender', 'wert': 'Personal', 'bezeichnung': 'weitere Webdav Kalender, bei mehreren mit ";" trennen', 'sort': 203, 'checkbox': False},
        {'name': 'logo_file', 'wert': '/static/firmen_neu.png', 'bezeichnung': 'Pfad zur Logodatei', 'sort': 401, 'checkbox': False},
        {'name': 'rechnungs_pfad', 'wert': '', 'bezeichnung': 'Ordner für automatische Rechnungsablage bei email-Versand. Wenn leer keine Ablage', 'sort': 104, 'checkbox': False},
        {'name': 'einzel_betrag', 'wert': '83', 'bezeichnung': 'Standardpreis Einzeltherapie €', 'sort': 80, 'checkbox': False},
        {'name': 'paar_betrag', 'wert': '90', 'bezeichnung': 'Standardpreis Paartherapie €', 'sort': 81, 'checkbox': False},
        {'name': 'einzel_zeit', 'wert': '50', 'bezeichnung': 'Standarddauer Einzeltherapie min', 'sort': 90, 'checkbox': False},
        {'name': 'paar_zeit', 'wert': '90', 'bezeichnung': 'Standarddauer Paartherapie min', 'sort': 91, 'checkbox': False},
        {'name': 'db_passphrase_set', 'wert': '0', 'bezeichnung': 'DB Passwort gesetzt (0/1)', 'sort': None, 'checkbox': False},
        #{'name': 'db_passphrase_check', 'wert': '', 'bezeichnung': 'DB Passwort Prüftoken', 'sort': None, 'checkbox': False},
        {'name': 'rechnung_text_oben', 'wert': 'Sehr geehrte Damen und Herren,\nanbei erhalten Sie Ihre aktuelle Rechnung.', 'bezeichnung': 'Standardtext Rechnung oben', 'sort': 100, 'checkbox': False},
        {'name': 'rechnung_text_unten', 'wert': 'Vielen Dank für Ihr Vertrauen.\nBitte überweisen Sie den Betrag innerhalb der angegebenen Frist.', 'bezeichnung': 'Standardtext Rechnung unten', 'sort': 101, 'checkbox': False},
        {'name': 'email_text_nach_anrede', 'wert': 'anbei erhalten Sie Ihre aktuelle Rechnung als PDF.', 'bezeichnung': 'Standardtext E-Mail nach Anrede', 'sort': 110, 'checkbox': False},
        {'name': 'supervision_zeit', 'wert': '55', 'bezeichnung': 'Standarddauer Supervision min', 'sort': 92, 'checkbox': False},
        {'name': 'supervision_betrag', 'wert': '90', 'bezeichnung': 'Standardpreis Supervision €', 'sort': 82, 'checkbox': False},
        {'name': 'max_backups', 'wert': '10', 'bezeichnung': 'Maximale Backups', 'sort': 101, 'checkbox': False},
        {'name': 'auto_kuerzel_kunden', 'wert': '1', 'bezeichnung': 'Kürzel bei Kunden automatisch erstellen', 'sort': 102, 'checkbox': True},
        {'name': 'rechnungsnummer_jahr_vorne', 'wert': '1', 'bezeichnung': 'Jahreszahl bei Rechnungsnummer vorne', 'sort': 103, 'checkbox': True},
        {'name': 'letzte_kalender_sync', 'wert': '', 'bezeichnung': None, 'sort': None, 'checkbox': False},
        {'name': 'kalender_sync', 'wert': '0', 'bezeichnung': 'Kalender synchronisieren', 'sort': 190, 'checkbox': True},
        {'name': 'kalender_sync_nur_zum_server', 'wert': '1', 'bezeichnung': 'Kalender nur zum Server synchronisieren', 'sort': 191, 'checkbox': True},
        {'name': 'kalender_sync_abfragen', 'wert': '0', 'bezeichnung': 'Fragen bevor Änderung vom Onlinekalender übernommen werden', 'sort': 192, 'checkbox': True},
    ]

    for defaults in programmvariable_defaults:
        programmvariable = Programmvariable.query.filter_by(name=defaults['name']).first()
        if not programmvariable:
            programmvariable = Programmvariable(**defaults)
            db.session.add(programmvariable)
            continue

        if not programmvariable.bezeichnung and defaults['bezeichnung'] is not None:
            programmvariable.bezeichnung = defaults['bezeichnung']
        if programmvariable.sort is None and defaults['sort'] is not None:
            programmvariable.sort = defaults['sort']
        if programmvariable.checkbox is None:
            programmvariable.checkbox = defaults['checkbox']

    if not Leistung.query.first():
        standard_leistungen = [
            {'id': 1, 'value': 1, 'bezeichnung': 'Einzeltherapie', 'dauer_min': 52, 'betrag': 80, 'gruppe': 0},
            {'id': 2, 'value': 2, 'bezeichnung': 'Paartherapie', 'dauer_min': 60, 'betrag': 120, 'gruppe': 0},
            {'id': 3, 'value': 3, 'bezeichnung': 'Familientherapie', 'dauer_min': 75, 'betrag': 140, 'gruppe': None},
            {'id': 4, 'value': 4, 'bezeichnung': 'Gruppentherapie', 'dauer_min': 90, 'betrag': 50, 'gruppe': 1},
            {'id': 5, 'value': 5, 'bezeichnung': 'Einzelsupervision', 'dauer_min': 55, 'betrag': 90, 'gruppe': None},
            {'id': 6, 'value': 6, 'bezeichnung': 'Gruppensupervision', 'dauer_min': 90, 'betrag': 60, 'gruppe': 1},
            {'id': 7, 'value': 7, 'bezeichnung': 'Einzelselbsterfahrung', 'dauer_min': 50, 'betrag': 80, 'gruppe': None},
            {'id': 8, 'value': 8, 'bezeichnung': 'Gruppenselbsterfahrung', 'dauer_min': 90, 'betrag': 50, 'gruppe': 1},
            {'id': 9, 'value': 9, 'bezeichnung': 'Coaching', 'dauer_min': 60, 'betrag': 100, 'gruppe': None},
        ]
        db.session.add_all(Leistung(**leistung) for leistung in standard_leistungen)

    
    db.session.commit()
    
    # Initialisiere WebDAV-Konfiguration
    from config import init_webdav_config
    init_webdav_config()



seiten_bp = Blueprint("seiten", __name__)


@app.route("/unlock", methods=["GET", "POST"])
def unlock():
    setup_mode = not is_passphrase_initialized()
    if request.method == "POST":
        passphrase = request.form.get("passphrase", "")
        confirm = request.form.get("passphrase_confirm", "")
        if setup_mode:
            if not passphrase:
                return render_template("unlock.html", error="Passwort erforderlich", setup_mode=setup_mode)
            if passphrase != confirm:
                return render_template("unlock.html", error="Passwörter stimmen nicht überein", setup_mode=setup_mode)
            set_new_passphrase(passphrase)
            next_url = request.args.get("next") or url_for("seiten.kunden_seite")
            return redirect(next_url)
        if passphrase and verify_passphrase(passphrase):
            mark_passphrase_prompt_done()
            next_url = request.args.get("next") or url_for("seiten.kunden_seite")
            return redirect(next_url)
        return render_template("unlock.html", error="Passwort falsch", setup_mode=setup_mode)
    return render_template("unlock.html", setup_mode=setup_mode)

@app.get("/psyDB.ico")
def psydb_favicon():
    return send_from_directory(app.root_path, "psyDB.ico", mimetype="image/x-icon")

@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.root_path, "psyDB.ico", mimetype="image/x-icon")

@seiten_bp.get("/kunden")
def kunden_seite():
    return render_template("kunden.html")


@seiten_bp.get("/termine")
def termine_seite():
    return render_template("termine.html")

@seiten_bp.get("/rechnungen")
def rechnungen_seite():
    return render_template("rechnungen.html")

@seiten_bp.get("/kalender")
def kalender_seite():
    return render_template("kalender.html")

@seiten_bp.get("/einstellungen")
def einstellungen_seite():
    return render_template("einstellungen.html")

@seiten_bp.get("/dokumentation")
def dokumentation_seite():
    return render_template("dokumentation.html")    


@seiten_bp.get("/gruppen")
def gruppen_seite():
    return render_template("gruppen.html")

# Auswertungsseite
@seiten_bp.get("/auswertung")
def auswertung_seite():
    return render_template("auswertung.html")

@seiten_bp.get("/mahnungen")
def mahnungen_seite():
    return render_template("mahnungen.html")

# Hilfeseite
@seiten_bp.get("/hilfe")
def hilfe_seite():
    return render_template("hilfe.html")

# ✅ Blueprints registrieren
app.register_blueprint(kunden_bp, url_prefix="/api")  # API-Routen
app.register_blueprint(standorte_bp, url_prefix="/api")
app.register_blueprint(termine_bp, url_prefix="/api")
app.register_blueprint(rechnungen_bp, url_prefix="/api")
app.register_blueprint(kalender_bp, url_prefix="/api")
app.register_blueprint(gruppen_bp, url_prefix="/api")  # Gruppen-Routen
app.register_blueprint(gruppenkunden_bp, url_prefix="/api")  # Gruppen-Kunden-Routen
app.register_blueprint(gruppentermine_bp, url_prefix="/api")  # Gruppentermine-Routen
app.register_blueprint(mahnungen_bp, url_prefix="/api")      # Mahnungen Seite
app.register_blueprint(programmvariablen_bp, url_prefix="/api")  # Programmvariablen
app.register_blueprint(druckvorlagen_bp, url_prefix="/api")  # Druckvorlagen
app.register_blueprint(leistungen_bp, url_prefix="/api")  # Leistungen API
app.register_blueprint(doku_bp, url_prefix="/api")   # Doku-API
app.register_blueprint(dashboard_bp)                   # Dashboard
app.register_blueprint(auswertung_bp)                 # Auswertungs-API
app.register_blueprint(seiten_bp)                    # HTML-Seiten




# Funktion zum Browser öffnen
def open_browser():
    url = "http://127.0.0.1:5000/"
    if sys.platform.startswith('linux'):
        subprocess.Popen(['xdg-open', url])
    elif sys.platform.startswith('win'):
        subprocess.Popen(['start', url], shell=True)
    elif sys.platform.startswith('darwin'):
        subprocess.Popen(['open', url])


@app.route("/shutdown")
def shutdown():
    def stop_server():
        import time
        time.sleep(1)  # gibt dem Browser Zeit, die Seite anzuzeigen
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=stop_server).start()
    return "<h1>Datenbank beendet</h1>"

if __name__ == "__main__":
    # Backup erstellen
    backup_sqlite_db(DB_FILE, MAX_BACKUPS)

    # Browser nur im Hauptprozess öffnen
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.0, open_browser).start()

    # Flask starten
    app.run(debug=True, use_reloader=True)




