
from flask import Blueprint, Flask, render_template, request, redirect, url_for, render_template_string, jsonify, make_response
import sqlite3
from datetime import date, datetime, timedelta, timezone
from database import db
import os
import signal
import shutil
import threading
import subprocess
import sys
from routes import kunden_bp, standorte_bp, termine_bp, rechnungen_bp, kalender_bp, gruppen_bp, gruppentermine_bp, gruppenkunden_bp ,  mahnungen_bp, programmvariablen_bp, dashboard_bp, druckvorlagen_bp
from services.backup_service import backup_sqlite_db
from config import DB_FILE, MAX_BACKUPS, set_passphrase, use_passphrase_mode, is_encryption_ready, verify_passphrase, is_passphrase_initialized, set_new_passphrase, should_force_passphrase_prompt, mark_passphrase_prompt_done  # <-- import aus ini
import time
from models import Rechnung, Mahnung, Termin, Kunde

app = Flask(__name__)


@app.before_request
def require_unlock():
    if not use_passphrase_mode():
        return
    if is_encryption_ready() and not should_force_passphrase_prompt():
        return
    if request.path.startswith("/static/"):
        return
    if request.path.startswith("/unlock"):
        return
    return redirect(url_for("unlock", next=request.path))

# SQLAlchemy konfigurieren
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_FILE}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()
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
    if not Programmvariable.query.filter_by(name='max_backups').first():
        db.session.add(Programmvariable(name='max_backups', bezeichnung='Maximale Backups', wert='10'))
    if not Programmvariable.query.filter_by(name='mahnspesen').first():
        db.session.add(Programmvariable(name='mahnspesen', bezeichnung='Mahnspesen', wert='5'))
    if not Programmvariable.query.filter_by(name='zahlungsziel_tage_rechnung').first():
        db.session.add(Programmvariable(name='zahlungsziel_tage_rechnung', bezeichnung='Zahlungsziel Tage', wert='14'))
    if not Programmvariable.query.filter_by(name='zahlungsziel_tage_mahnung').first():
        db.session.add(Programmvariable(name='zahlungsziel_tage_mahnung', bezeichnung='Zahlungsziel Tage Mahnung', wert='7'))
    if not Programmvariable.query.filter_by(name='verzugszinsen_proz').first():
        db.session.add(Programmvariable(name='verzugszinsen_proz', bezeichnung='Verzugszinsen Prozent', wert='4'))
    if not Programmvariable.query.filter_by(name='webdav_user').first():
        db.session.add(Programmvariable(name='webdav_user', bezeichnung='WebDAV Benutzer', wert=''))
    if not Programmvariable.query.filter_by(name='webdav_pfad').first():
        db.session.add(Programmvariable(name='webdav_pfad', bezeichnung='WebDAV Pfad', wert=''))
    if not Programmvariable.query.filter_by(name='db_passphrase_set').first():
        db.session.add(Programmvariable(name='db_passphrase_set', bezeichnung='DB Passwort gesetzt (0/1)', wert='0'))
    if not Programmvariable.query.filter_by(name='db_passphrase_check').first():
        db.session.add(Programmvariable(name='db_passphrase_check', bezeichnung='DB Passwort Prüftoken', wert=''))
    db.session.commit()
    # Bestehende aktualisieren, falls bezeichnung fehlen
    max_back = Programmvariable.query.filter_by(name='max_backups').first()
    if max_back and not max_back.bezeichnung:
        max_back.bezeichnung = 'Maximale Backups'
    mahn = Programmvariable.query.filter_by(name='mahnspesen').first()
    if mahn and not mahn.bezeichnung:
        mahn.bezeichnung = 'Mahnspesen'
    zahlungsziel = Programmvariable.query.filter_by(name='zahlungsziel_tage_rechnung').first()
    if zahlungsziel and not zahlungsziel.bezeichnung:
        zahlungsziel.bezeichnung = 'Zahlungsziel Tage'
    verzugszinsen = Programmvariable.query.filter_by(name='verzugszinsen_proz').first()
    if verzugszinsen and not verzugszinsen.bezeichnung:
        verzugszinsen.bezeichnung = 'Verzugszinsen Prozent'
    webdav_user = Programmvariable.query.filter_by(name='webdav_user').first()
    if webdav_user and not webdav_user.bezeichnung:
        webdav_user.bezeichnung = 'WebDAV Benutzer'
    webdav_pfad = Programmvariable.query.filter_by(name='webdav_pfad').first()
    if webdav_pfad and not webdav_pfad.bezeichnung:
        webdav_pfad.bezeichnung = 'WebDAV Pfad'
    db_passphrase_set = Programmvariable.query.filter_by(name='db_passphrase_set').first()
    if db_passphrase_set and not db_passphrase_set.bezeichnung:
        db_passphrase_set.bezeichnung = 'DB Passwort gesetzt (0/1)'
    db_passphrase_check = Programmvariable.query.filter_by(name='db_passphrase_check').first()
    if db_passphrase_check and not db_passphrase_check.bezeichnung:
        db_passphrase_check.bezeichnung = 'DB Passwort Prüftoken'
    db.session.commit()
    
    # Initialisiere WebDAV-Konfiguration
    from config import init_webdav_config
    init_webdav_config()

from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView



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
app.register_blueprint(dashboard_bp)                   # Dashboard
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
    app.run(debug=True, use_reloader=False)




