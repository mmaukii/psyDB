from flask import Blueprint, request, jsonify, render_template, current_app as app,  send_file
from database import db
from models import Mahnung, Rechnung, Termin, TermineRechnung, Kunde, Programmvariable  # Mahnung muss als Model existieren
import os
import subprocess
import qrcode
import pdfkit
from datetime import date, datetime, timedelta, timezone
import math

def get_mahnung_config():
    """Holt Mahnungskonfiguration aus Programmvariablen"""
    zahlungsziel_rechnung_var = Programmvariable.query.filter_by(name='zahlungsziel_tage_rechnung').first()
    zahlungsziel_mahnung_var = Programmvariable.query.filter_by(name='zahlungsziel_tage_mahnung').first()
    mahnspesen_var = Programmvariable.query.filter_by(name='mahnspesen').first()
    verzugszinsen_var = Programmvariable.query.filter_by(name='verzugszinsen_proz').first()
    
    zahlungsziel_tage_rechnung = int(zahlungsziel_rechnung_var.wert) if zahlungsziel_rechnung_var else 14
    zahlungsziel_tage_mahnung = int(zahlungsziel_mahnung_var.wert) if zahlungsziel_mahnung_var else 14
    mahnspesen = float(mahnspesen_var.wert) if mahnspesen_var else 5.0
    verzugszinsen_proz = float(verzugszinsen_var.wert) if verzugszinsen_var else 4.0
    
    return zahlungsziel_tage_rechnung, zahlungsziel_tage_mahnung, mahnspesen, verzugszinsen_proz



mahnungen_bp = Blueprint("mahnungen", __name__)

# --- Alle Mahnungen ---
@mahnungen_bp.get("/mahnungen")
def get_all_mahnungen():
    mahnungen = Mahnung.query.order_by(Mahnung.datum).all()
    return jsonify([{
        "id": m.id,
        "rechnung_id": m.rechnung_id,
        "datum": m.datum,
        "kommentar": m.kommentar,
        "timestamp": m.timestamp,
        "mahnungsnr": m.mahnungsnr,
        "verzugszinsenProz": m.verzugszinsenProz,
        "zahlungsziel_tage": m.zahlungsziel_tage,
        "mahnspesen": m.mahnspesen,
        "verzugszinsen": m.verzugszinsen
    } for m in mahnungen])

# --- Einzelne Mahnung ---
@mahnungen_bp.get("/mahnungen/<int:id>")
def get_mahnung(id):
    m = Mahnung.query.get_or_404(id)
    return jsonify({
        "id": m.id,
        "rechnung_id": m.rechnung_id,
        "datum": m.datum,
        "kommentar": m.kommentar,
        "timestamp": m.timestamp,
        "mahnungsnr": m.mahnungsnr,
        "verzugszinsenProz": m.verzugszinsenProz,
        "mahnspesen": m.mahnspesen,
        "verzugszinsen": m.verzugszinsen
    })

# --- Mahnung anlegen (automatisch Zinsen + Spesen) ---
@mahnungen_bp.post("/mahnungen")
def add_mahnung():
    data = request.get_json()
    
    # Rechnung laden
    rechnung = Rechnung.query.get_or_404(data.get("rechnung_id"))
    
    # Termine zur Rechnung laden
    termine = (
        db.session.query(Termin)
        .join(TermineRechnung, TermineRechnung.termin_id == Termin.id)
        .filter(TermineRechnung.rechnung_id == rechnung.id)
        .all()
    )
    
    # Gesamtbetrag der Rechnung berechnen
    gesamtbetrag = sum(s.betrag for s in termine)
    rechnung.gesamtbetrag = gesamtbetrag

    # Mahnungsnummer und Intervall
    mahnungsnr = data.get("mahnungsnr", 1)
    _, zahlungsziel_mahnung, mahnspesen, verzugszinsen_proz = get_mahnung_config()
    verzugszinsenProz = data.get("verzugszinsenProz", verzugszinsen_proz)

    # Verzugsbeginn = Rechnungsdatum + Zahlungsziel
    rechnungsdatum = datetime.strptime(rechnung.datum, "%Y-%m-%d")
    zahlungsziel_tage = rechnung.zahlungsziel_tage
    verzugsbeginn = rechnungsdatum + timedelta(days=zahlungsziel_tage)
    verzugsende = datetime.now()
    verzugstage = max((verzugsende - verzugsbeginn).days, 0)

    # Verzugszinsen berechnen (auf 2 Nachkommastelle abrunden)
    verzugszinsen = math.floor(gesamtbetrag * (verzugszinsenProz / 100) * (verzugstage / 365) * 100) / 100

    # Gesamtbetrag inkl. Zinsen + Spesen
    gesamtbetragMahnung = gesamtbetrag + verzugszinsen + mahnspesen

    # Mahnung erstellen
    m = Mahnung(
        rechnung_id=data.get("rechnung_id"),
        datum=data.get("datum"),
        timestamp=datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S"),
        kommentar=data.get("kommentar"),
        mahnungsnr=mahnungsnr,
        verzugszinsenProz=verzugszinsenProz,
        zahlungsziel_tage=zahlungsziel_tage,
        mahnspesen=mahnspesen,
        verzugszinsen=verzugszinsen
    )

    db.session.add(m)
    db.session.commit()

    return jsonify({"success": True, "id": m.id}), 201


# --- Mahnung ändern ---
@mahnungen_bp.put("/mahnungen/<int:id>")
def update_mahnung(id):
    m = Mahnung.query.get_or_404(id)
    data = request.get_json()
    for field in ["rechnung_id", "datum", "timestamp", "kommentar", "mahnungsnr", "verzugszinsenProz", "zahlungsziel_tage", "mahnspesen", "verzugszinsen"]:
        if field in data:
            setattr(m, field, data[field])
    # changestamp immer setzen
    m.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    db.session.commit()
    return jsonify({"success": True})

# --- Mahnung löschen ---
@mahnungen_bp.delete("/mahnungen/<int:id>")
def delete_mahnung(id):
    m = Mahnung.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    return jsonify({"success": True})

def generate_mahnung_pdf(mahnung_id):
    """Hilfsfunktion: erzeugt PDF + QR-Code für Mahnung und gibt die wichtigen Infos zurück"""
    mahnung = Mahnung.query.get_or_404(mahnung_id)
    rechnung = Rechnung.query.get_or_404(mahnung.rechnung_id)

    # Termine laden
    termine = (
        db.session.query(Termin)
        .join(TermineRechnung, TermineRechnung.termin_id == Termin.id)
        .filter(TermineRechnung.rechnung_id == rechnung.id)
        .order_by(Termin.datum.desc(), Termin.utc_starttime)
        .all()
    )
    termine_json = [{
        "termine_id": s.id,
        "kunde_id": s.kunde_id,
        "datum": s.datum,
        "utc_starttime": s.utc_starttime,
        "utc_endtime": s.utc_endtime,
        "beschreibung": s.beschreibung,
        "kommentar": s.kommentar,
        "betrag": s.betrag
    } for s in termine]

    # Kunde + Standort
    kunde = Kunde.query.get_or_404(termine_json[0]["kunde_id"]) if termine_json else None
    standort = kunde.standort if kunde else None

    # Zahlungsziel
    rechnungsdatum = datetime.strptime(rechnung.datum, "%Y-%m-%d")
    _, zahlungsziel_mahnung, mahnspesen, _ = get_mahnung_config()
    zahlungsziel = date.today() + timedelta(days=zahlungsziel_mahnung)
    zahlungsziel_str = zahlungsziel.strftime("%d.%m.%Y")

    # Gesamtbetrag + Verzugszinsen + Mahnspesen
    gesamtbetrag = sum(s["betrag"] for s in termine_json)
    rechnung.gesamtbetrag = gesamtbetrag
    verzugszinsen = mahnung.verzugszinsen
    gesamtbetragMahnung = gesamtbetrag + verzugszinsen + mahnspesen

    # Formatierter Gesamtbetrag für Template
    gesamtbetrag_formatted = f"{gesamtbetrag:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")

    # Lade Logo-Pfad
    from models import Programmvariable
    logo_var = Programmvariable.query.filter_by(name='logo_file').first()
    logo_filename = logo_var.wert if logo_var and logo_var.wert else "static/firmen_logo_fuer_schreiben.png"
    
    # Konvertiere zu absolutem Pfad für wkhtmltopdf
    # Entferne /static/ Prefix falls vorhanden
    if logo_filename.startswith('/static/'):
        logo_filename = logo_filename[8:]  # Entferne "/static/"
    elif logo_filename.startswith('static/'):
        logo_filename = logo_filename[7:]  # Entferne "static/"
    
    logo_absolute_path = os.path.join(app.root_path, 'static', logo_filename)
    
    # Übergebe absoluten Pfad an Template
    logo_path = f"file://{logo_absolute_path}"
    
    # QR-Code erstellen BEVOR Template gerendert wird
    rechnungs_nr = rechnung.rechnungsnr
    qr_filename = f"girocode_{mahnung.mahnungsnr}Mahnung_{rechnungs_nr}.png"
    qr_absolute_path = os.path.join(app.root_path, 'static/girocode', qr_filename)
    
    # Alten QR-Code löschen falls vorhanden
    if os.path.exists(qr_absolute_path):
        os.remove(qr_absolute_path)
    
    # QR-Daten vorbereiten (vor QR-Code-Erstellung)
    qr_data = f"""BCD
001
1
SCT
{standort.bic}
{standort.kontoName}
{standort.iban}
EUR{gesamtbetragMahnung}
ReNR:{rechnungs_nr}{mahnung.mahnungsnr}.Mahnung
"""
    
    # QR-Code erstellen
    qrcode.make(qr_data).save(qr_absolute_path)
    
    # QR-Code-Pfad zu absoluter URL konvertieren (NACH Erstellung)
    qr_path_file_url = f"file://{qr_absolute_path}" if os.path.exists(qr_absolute_path) else ""

    # HTML rendern (analog zu Rechnungen: Template aus /Vorlagen laden, falls nicht im templates-Ordner)
    from flask import render_template_string
    template_name = "DruckvorlageMahnung.html"
    templates_root = os.path.join(app.root_path, "templates")
    template_in_templates = os.path.join(templates_root, "Vorlagen", template_name)
    template_context = {
        "firma": standort,
        "kunde": kunde,
        "zahlungsziel": zahlungsziel_str,
        "verzugszinsen": verzugszinsen,
        "verzugstage": max((datetime.now() - rechnungsdatum).days, 0),
        "mahnspesen": mahnspesen,
        "rechnung": rechnung,
        "rechnungen": [rechnung],
        "mahnung": mahnung,
        "positionen": termine_json,
        "gesamtbetrag_formatted": gesamtbetrag_formatted,
        "logo_path": logo_path,
        "qr_code_path": qr_path_file_url
    }
    if os.path.exists(template_in_templates):
        html_content = render_template("Vorlagen/" + template_name, **template_context)
    else:
        candidate_paths = [
            os.path.join(app.root_path, "Vorlagen", template_name),
            os.path.join(app.root_path, "Vorlagen", "DruckvorlageMahnung.html"),
        ]
        template_file = next((p for p in candidate_paths if os.path.exists(p)), None)
        if not template_file:
            raise FileNotFoundError(f"Druckvorlage nicht gefunden: {template_name}")
        with open(template_file, "r", encoding="utf-8") as f:
            template_source = f.read()
        html_content = render_template_string(template_source, **template_context)

    # PDF-Dateiname
    now_str = datetime.now().strftime("%y%m%d_%H%M")
    nachname = kunde.nachname if kunde else "kunde"
    pdf_filename = f"Rechnung_Nr_{rechnungs_nr}_{mahnung.mahnungsnr}Mahnung_{now_str}_{nachname}.pdf"
    folder_path = os.path.join(app.root_path, "Rechnungen")
    os.makedirs(folder_path, exist_ok=True)
    pdf_path = os.path.join(folder_path, pdf_filename)


    # Footer HTML-Datei laden (optional, falls vorhanden)
    footer_file_path = os.path.join(app.root_path, "Vorlagen", "Druckvorlage_Footer.html")
    footer_html_rendered = None
    temp_footer_path = None
    if os.path.exists(footer_file_path):
        with open(footer_file_path, "r", encoding="utf-8") as f:
            footer_template_source = f.read()
        # Footer rendern (z.B. mit Firmeninfos, QR-Code, etc.)
        footer_html_rendered = render_template_string(
            footer_template_source,
            firma=standort,
            qr_code_path=qr_path_file_url
        )
        # Temporäre Footer-Datei speichern
        temp_footer_path = os.path.join(app.root_path, "Vorlagen", "footer_rendered_mahnung.html")
        with open(temp_footer_path, "w", encoding="utf-8") as f:
            f.write(footer_html_rendered)

    # PDFKit Optionen wie bei Rechnung
    options = {
        'enable-local-file-access': None,
        'margin-top': '20mm',
        'margin-bottom': '35mm',
        'margin-left': '20mm',
        'margin-right': '20mm',
    }
    if temp_footer_path:
        options['footer-html'] = "file:///" + temp_footer_path.replace("\\", "/")
        options['footer-spacing'] = '5'

    pdfkit.from_string(html_content, pdf_path, options=options)

    return pdf_path, kunde, rechnungs_nr, nachname, zahlungsziel_str, mahnung.mahnungsnr


@mahnungen_bp.get("/mahnungen/mail/<int:mahnung_id>")
def mahnung_mail(mahnung_id):
    pdf_path, kunde, rechnungs_nr, nachname, zahlungsziel_str, mahnungsnr = generate_mahnung_pdf(mahnung_id)

    if kunde:
        geschlecht = getattr(kunde, "geschlecht", "").lower()
        if geschlecht == "m":
            anrede = f"Hallo Herr {nachname},"
        elif geschlecht == "w":
            anrede = f"Hallo Frau {nachname},"
        else:
            anrede = f"Hallo {kunde.vorname} {nachname},"

        subject = f"Mahnung Rechnung {rechnungs_nr}"
        
        # Text aus Programmvariable holen
        from models import Programmvariable
        email_text_var = Programmvariable.query.filter_by(name='mahnung_text_email').first()
        if email_text_var and email_text_var.wert:
            body = f"{anrede}\n\n{email_text_var.wert}"
        else:
            body = anrede

        cmd = [
            "thunderbird",
            "-compose",
            f"to='{kunde.email}',subject='{subject}',body='{body}',attachment='{pdf_path}'"
        ]
        subprocess.Popen(cmd)

    return jsonify({"success": True, "pdf_path": pdf_path})

@mahnungen_bp.get("/mahnungen/pdf/<int:mahnung_id>")
def mahnung_pdf(mahnung_id):
    pdf_path, _, _, _, _, _ = generate_mahnung_pdf(mahnung_id)
    return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)

