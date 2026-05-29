from flask import Blueprint, request, jsonify, current_app as app, send_file
from database import db
from models import Mahnung, Rechnung, Termin, TermineRechnung, Kunde, Programmvariable  # Mahnung muss als Model existieren
import os
import subprocess
import sys
from urllib.parse import quote
import qrcode
from datetime import date, datetime, timedelta, timezone
import math
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _format_currency(value):
    return f"{float(value or 0):.2f}".replace(".", ",")


def _append_multiline_paragraphs(story, text, style, space_after=2):
    if not text:
        return
    for line in str(text).splitlines():
        if line.strip():
            story.append(Paragraph(escape(line.strip()), style))
            story.append(Spacer(1, space_after * mm))


def _ps_single_quote(value):
    """Escapes text for PowerShell single-quoted string literals."""
    return "'" + str(value).replace("'", "''") + "'"


def open_windows_mail_with_attachment(recipient, subject, body, attachment_path):
    """Öffnet unter Windows eine neue Outlook-Mail mit Anhang."""
    abs_attachment = os.path.abspath(attachment_path)

    try:
        import win32com.client  # type: ignore

        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = recipient
        mail.Subject = subject
        mail.Body = body
        mail.Attachments.Add(abs_attachment)
        mail.Display()
        return True
    except Exception:
        pass

    try:
        ps_script = (
            "$ol = New-Object -ComObject Outlook.Application; "
            "$mail = $ol.CreateItem(0); "
            f"$mail.To = {_ps_single_quote(recipient)}; "
            f"$mail.Subject = {_ps_single_quote(subject)}; "
            f"$mail.Body = {_ps_single_quote(body)}; "
            f"$mail.Attachments.Add({_ps_single_quote(abs_attachment)}); "
            "$mail.Display()"
        )
        subprocess.Popen([
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            ps_script,
        ])
        return True
    except Exception:
        return False

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
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
        .order_by(Termin.datum.desc(), Termin.startzeit)
        .all()
    )
    termine_json = [{
        "termine_id": s.id,
        "kunde_id": s.kunde_id,
        "datum": s.datum,
        "startzeit": s.startzeit,
        "endzeit": s.endzeit,
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

    # Lade Logo-Pfad
    logo_var = Programmvariable.query.filter_by(name='logo_file').first()
    logo_filename = logo_var.wert if logo_var and logo_var.wert else "static/firmen_logo_fuer_schreiben.png"
    logo_absolute_path = os.path.join(app.root_path, logo_filename.lstrip('/'))
    
    # QR-Code erstellen BEVOR Template gerendert wird
    rechnungs_nr = rechnung.rechnungsnr
    qr_filename = f"girocode_{mahnung.mahnungsnr}Mahnung_{rechnungs_nr}.png"
    qr_absolute_path = os.path.join(app.root_path, 'static/girocode', qr_filename)
    os.makedirs(os.path.dirname(qr_absolute_path), exist_ok=True)
    
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
ReNR:{rechnungs_nr}_{mahnung.mahnungsnr}.Mahnung
"""
    
    # QR-Code erstellen
    qrcode.make(qr_data).save(qr_absolute_path)
    
    # PDF-Dateiname
    now_str = datetime.now().strftime("%y%m%d_%H%M")
    nachname = kunde.nachname if kunde else "kunde"
    pdf_filename = f"Rechnung_Nr_{rechnungs_nr}_{mahnung.mahnungsnr}Mahnung_{now_str}_{nachname}.pdf"
    folder_path = os.path.join(app.root_path, "Rechnungen")
    os.makedirs(folder_path, exist_ok=True)
    pdf_path = os.path.join(folder_path, pdf_filename)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="Body", parent=styles["Normal"], fontSize=10, leading=13))
    styles.add(ParagraphStyle(name="Heading", parent=styles["Heading2"], fontSize=14, leading=16, spaceAfter=6))

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
    )
    story = []

    firma_name = standort.name if standort else ""
    firma_ort = f"{standort.plz or ''} {standort.ort or ''}".strip() if standort else ""
    header_left = [Paragraph(escape(firma_name), styles["Body"]) if firma_name else Paragraph("", styles["Body"]) ]
    if standort and standort.adresse:
        header_left.append(Paragraph(escape(standort.adresse), styles["BodySmall"]))
    if firma_ort:
        header_left.append(Paragraph(escape(firma_ort), styles["BodySmall"]))
    if standort and standort.email:
        header_left.append(Paragraph(escape(standort.email), styles["BodySmall"]))

    logo_cell = ""
    if os.path.exists(logo_absolute_path):
        logo = Image(logo_absolute_path)
        logo.drawHeight = 18 * mm
        logo.drawWidth = 55 * mm
        logo.hAlign = "RIGHT"
        logo_cell = logo

    header_table = Table([[header_left, logo_cell]], colWidths=[120 * mm, 50 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(f"{escape(str(mahnung.mahnungsnr))}. Mahnung zu Rechnung {escape(str(rechnungs_nr))}", styles["Heading"]))
    story.append(Paragraph(f"Mahndatum: {escape(str(mahnung.datum or ''))}", styles["Body"]))
    story.append(Paragraph(f"Neues Zahlungsziel: {escape(zahlungsziel_str)}", styles["Body"]))
    story.append(Spacer(1, 4 * mm))

    if kunde:
        story.append(Paragraph("Mahnung an:", styles["Body"]))
        story.append(Paragraph(escape(f"{kunde.vorname or ''} {kunde.nachname or ''}".strip()), styles["BodySmall"]))
        if kunde.adresse:
            story.append(Paragraph(escape(kunde.adresse), styles["BodySmall"]))
        ort = f"{kunde.plz or ''} {kunde.ort or ''}".strip()
        if ort:
            story.append(Paragraph(escape(ort), styles["BodySmall"]))
        story.append(Spacer(1, 5 * mm))

    table_data = [["Datum", "Zeit", "Beschreibung", "Betrag (EUR)"]]
    for t in termine_json:
        time_range = f"{t.get('startzeit') or ''} - {t.get('endzeit') or ''}".strip(" -")
        table_data.append([
            str(t.get("datum") or ""),
            time_range,
            str(t.get("beschreibung") or ""),
            _format_currency(t.get("betrag") or 0),
        ])

    table_data.append(["", "", "Zwischensumme", _format_currency(gesamtbetrag)])
    table_data.append(["", "", "Verzugszinsen", _format_currency(verzugszinsen)])
    table_data.append(["", "", "Mahnspesen", _format_currency(mahnspesen)])
    table_data.append(["", "", "Gesamtbetrag", _format_currency(gesamtbetragMahnung)])

    positions_table = Table(table_data, colWidths=[28 * mm, 28 * mm, 84 * mm, 30 * mm])
    positions_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9BCC2")),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(positions_table)
    story.append(Spacer(1, 4 * mm))

    _append_multiline_paragraphs(story, mahnung.kommentar, styles["Body"])

    if standort:
        story.append(Spacer(1, 4 * mm))
        if standort.kontoName:
            story.append(Paragraph(f"Kontoinhaber: {escape(str(standort.kontoName))}", styles["BodySmall"]))
        if standort.iban:
            story.append(Paragraph(f"IBAN: {escape(str(standort.iban))}", styles["BodySmall"]))
        if standort.bic:
            story.append(Paragraph(f"BIC: {escape(str(standort.bic))}", styles["BodySmall"]))

    if os.path.exists(qr_absolute_path):
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("GiroCode", styles["BodySmall"]))
        qr_image = Image(qr_absolute_path)
        qr_image.drawHeight = 28 * mm
        qr_image.drawWidth = 28 * mm
        story.append(qr_image)

    doc.build(story)

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

        if sys.platform.startswith("darwin"):
            mailto = f"mailto:{quote(kunde.email)}?subject={quote(subject)}&body={quote(body)}"
            subprocess.Popen(["open", mailto])
            subprocess.Popen(["open", "-a", "Mail", pdf_path])
        elif sys.platform.startswith("win"):
            opened = open_windows_mail_with_attachment(kunde.email, subject, body, pdf_path)
            if not opened:
                mailto = f"mailto:{quote(kunde.email)}?subject={quote(subject)}&body={quote(body)}"
                subprocess.Popen(["cmd", "/c", "start", "", mailto])
        else:
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

