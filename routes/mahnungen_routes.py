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
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _format_currency(value):
    return f"{float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _append_multiline_paragraphs(story, text, style, space_after=2):
    if not text:
        return
    for line in str(text).splitlines():
        if line.strip():
            story.append(Paragraph(escape(line.strip()), style))
            story.append(Spacer(1, space_after * mm))


def _format_date_de(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d.%m.%Y")
    text = str(value)
    for date_format in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, date_format).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return text


def _ps_single_quote(value):
    """Escapes text for PowerShell single-quoted string literals."""
    return "'" + str(value).replace("'", "''") + "'"


class NumberedCanvas(pdf_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(page_count)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        if page_count <= 1:
            return
        self.saveState()
        self.setFont("Helvetica", 9)
        page_width = self._pagesize[0]
        self.drawCentredString(page_width / 2.0, 28 * mm, f"Seite {self._pageNumber}/{page_count}")
        self.restoreState()


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
    
            "-Command",
            ps_script,
        ])
        return True
    except Exception:
        return False


def open_macos_mail_with_attachment(recipient, subject, body, attachment_path):
    """Öffnet unter macOS genau einen Mail-Entwurf mit Anhang."""
    abs_attachment = os.path.abspath(attachment_path)
    if not os.path.exists(abs_attachment):
        return False

    script_lines = [
        "on run argv",
        "set theRecipient to item 1 of argv",
        "set theSubject to item 2 of argv",
        "set messageBody to item 3 of argv",
        "set attachmentPath to item 4 of argv",
        "if messageBody does not end with return then set messageBody to messageBody & return",
        "tell application \"Mail\"",
        "set newMessage to make new outgoing message with properties {visible:true, subject:theSubject, content:messageBody}",
        "tell newMessage",
        "make new to recipient at end of to recipients with properties {address:theRecipient}",
        "make new attachment with properties {file name:POSIX file attachmentPath} at after the last paragraph",
        "end tell",
        "activate",
        "end tell",
        "end run",
    ]

    try:
        subprocess.Popen(["osascript", *sum([["-e", line] for line in script_lines], []), recipient, subject, body, abs_attachment])
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

def generate_mahnung_pdf(mahnung_id, save_to_disk=False):
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
    _, zahlungsziel_mahnung, mahnspesen, _ = get_mahnung_config()
    zahlungsziel = date.today() + timedelta(days=zahlungsziel_mahnung)
    zahlungsziel_str = zahlungsziel.strftime("%d.%m.%Y")

    # Verzugstage fuer den Mahnungstext
    rechnungsdatum_obj = None
    if hasattr(rechnung.datum, "date"):
        rechnungsdatum_obj = rechnung.datum.date()
    elif isinstance(rechnung.datum, date):
        rechnungsdatum_obj = rechnung.datum
    else:
        try:
            rechnungsdatum_obj = datetime.strptime(str(rechnung.datum), "%Y-%m-%d").date()
        except Exception:
            rechnungsdatum_obj = None
    zahlungsziel_tage_rechnung = int(rechnung.zahlungsziel_tage or 0)
    if rechnungsdatum_obj:
        verzugsbeginn = rechnungsdatum_obj + timedelta(days=zahlungsziel_tage_rechnung)
        verzugstage = max((date.today() - verzugsbeginn).days, 0)
    else:
        verzugstage = 0

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
    import io
    rechnungs_pfad_var = Programmvariable.query.filter_by(name="rechnungs_pfad").first()
    rechnungs_pfad = rechnungs_pfad_var.wert.strip() if rechnungs_pfad_var and rechnungs_pfad_var.wert else ""
    if save_to_disk and rechnungs_pfad:
        if not os.path.isabs(rechnungs_pfad) and rechnungs_pfad:
            # Fehler: Pfad ist nicht absolut
            from flask import flash
            flash("Der Ablagepfad für Mahnungen muss absolut sein. PDF wird nicht gespeichert.", "warning")
            pdf_buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                leftMargin=20 * mm,
                rightMargin=20 * mm,
                topMargin=12 * mm,
                bottomMargin=34 * mm,
            )
        else:
            folder_path = rechnungs_pfad
            os.makedirs(folder_path, exist_ok=True)
            pdf_path = os.path.join(folder_path, pdf_filename)
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                leftMargin=20 * mm,
                rightMargin=20 * mm,
                topMargin=12 * mm,
                bottomMargin=34 * mm,
            )
    else:
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=12 * mm,
            bottomMargin=34 * mm,
        )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="Body", parent=styles["Normal"], fontSize=10, leading=15))
    styles.add(ParagraphStyle(name="BodyRight", parent=styles["Body"], alignment=2))
    styles.add(ParagraphStyle(name="TopName", parent=styles["Body"], fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Heading", parent=styles["Heading2"], fontSize=14, leading=16, spaceAfter=6))

    doc.title = f"Rnr{rechnungs_nr}"
    story = []

    firma_name = standort.name if standort else ""
    firma_ort = f"{standort.plz or ''} {standort.ort or ''}".strip() if standort else ""
    header_left = [Paragraph(escape(firma_name), styles["TopName"]) if firma_name else Paragraph("", styles["Body"]) ]
    if standort and standort.adresse:
        header_left.append(Paragraph(escape(standort.adresse), styles["BodySmall"]))
    if firma_ort:
        header_left.append(Paragraph(escape(firma_ort), styles["BodySmall"]))
    if standort and standort.email:
        header_left.append(Paragraph(escape(standort.email), styles["BodySmall"]))

    logo_cell = ""
    if os.path.exists(logo_absolute_path):
        logo_reader = ImageReader(logo_absolute_path)
        original_width, original_height = logo_reader.getSize()
        max_logo_width = 42 * mm
        max_logo_height = 14 * mm
        scale = min(max_logo_width / float(original_width), max_logo_height / float(original_height))

        logo = Image(logo_absolute_path)
        logo.drawWidth = float(original_width) * scale
        logo.drawHeight = float(original_height) * scale
        logo.hAlign = "RIGHT"
        logo_cell = logo

    header_logo_width = 50 * mm
    header_table = Table([[header_left, logo_cell]], colWidths=[doc.width - header_logo_width, header_logo_width])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    header_separator = Table([[""]], colWidths=[doc.width])
    header_separator.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (0, 0), 0.3, colors.HexColor("#CFCFCF")),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 0), (0, 0), 2),
        ("BOTTOMPADDING", (0, 0), (0, 0), 3),
    ]))
    story.append(header_separator)
    story.append(Spacer(1, 8 * mm))

    meta_data = [
        ["Betrifft Rechnungsnummer:", str(rechnungs_nr)],
        ["Rechnungsdatum:", _format_date_de(rechnung.datum)],
        ["Mahnungsdatum:", _format_date_de(mahnung.datum)],
    ]
    meta_table = Table(meta_data, colWidths=[doc.width - (35 * mm), 35 * mm])
    meta_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    if kunde:
        story.append(Paragraph(escape(f"{kunde.vorname or ''} {kunde.nachname or ''}".strip()), styles["TopName"]))
        if kunde.adresse:
            story.append(Paragraph(escape(kunde.adresse), styles["BodySmall"]))
        ort = f"{kunde.plz or ''} {kunde.ort or ''}".strip()
        if ort:
            story.append(Paragraph(escape(ort), styles["BodySmall"]))
        story.append(Spacer(1, 5 * mm))

    story.append(Paragraph(f"{escape(str(mahnung.mahnungsnr))}. Mahnung zu Rechnung {escape(str(rechnungs_nr))}", styles["Heading"]))
    story.append(Spacer(1, 2.5 * mm))

    story.append(Paragraph("Guten Tag!", styles["Body"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        f"Leider konnte ich bis heute keinen Zahlungseingang zur oben genannten Rechnung ueber {_format_currency(gesamtbetrag)} € feststellen. Ich ersuche Sie daher, den offenen Betrag zuzueglich gesetzlicher Verzugszinsen und einer pauschalen Mahngebuehr bis spaetestens <b>{escape(zahlungsziel_str)}</b> zu begleichen. Nachfolgend die aktuelle Forderungsaufstellung:", styles["Body"]))
    story.append(Spacer(1, 3 * mm))

    table_data = [
        ["Offener Rechnungsbetrag", f"{_format_currency(gesamtbetrag)} €"],
        [f"Verzugszinsen ({mahnung.verzugszinsenProz} % p.a. fuer {verzugstage} Tage)", f"{_format_currency(verzugszinsen)} €"],
        ["Mahnspesen (pauschal)", f"{_format_currency(mahnspesen)} €"],
        ["Gesamtbetrag", f"{_format_currency(gesamtbetragMahnung)} €"],
    ]

    positions_table = Table(table_data, colWidths=[122 * mm, 31 * mm])
    positions_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9BCC2")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEADING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, -1), 4 * mm),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(positions_table)
    story.append(Spacer(1, 6 * mm))

    if int(mahnung.mahnungsnr or 1) == 1:
        story.append(Paragraph("Bitte begleichen Sie den offenen Betrag zeitnah.", styles["Body"]))
    else:
        story.append(Paragraph(
            f"Sollte bis zum <b>{escape(zahlungsziel_str)}</b> keine Zahlung eingehen, sehe ich mich gezwungen, weitere rechtliche Schritte einzuleiten.",
            styles["Body"],
        ))
    story.append(Spacer(1, 2 * mm))

    has_footer = standort or os.path.exists(qr_absolute_path)

    bank_name = standort.bankname if standort and getattr(standort, "bankname", None) else "easybank"
    account_name = standort.kontoName if standort and getattr(standort, "kontoName", None) else "Daniel Maurer"
    account_iban = standort.iban if standort and getattr(standort, "iban", None) else "1111 2222 3333 4455"
    account_bic = standort.bic if standort and getattr(standort, "bic", None) else "EASYATW1"

    bank_lines = [
        "Bankverbindung",
        str(bank_name),
        str(account_name),
        f"IBAN: {account_iban}",
        f"BIC: {account_bic}",
    ]

    def _draw_footer(canvas, page_doc):
        if not has_footer:
            canvas.setTitle(f"Rnr{rechnungs_nr}")
            return

        canvas.saveState()
        canvas.setTitle(f"Rnr{rechnungs_nr}")

        footer_top_y = page_doc.bottomMargin - 2 * mm
        canvas.setStrokeColor(colors.HexColor("#CFCFCF"))
        canvas.setLineWidth(0.3)
        canvas.line(page_doc.leftMargin, footer_top_y, page_doc.leftMargin + page_doc.width, footer_top_y)

        qr_size = 24 * mm
        qr_x = page_doc.leftMargin
        qr_y = footer_top_y - qr_size - 2 * mm
        if os.path.exists(qr_absolute_path):
            canvas.drawImage(qr_absolute_path, qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask="auto")

        canvas.setFont("Helvetica", 9)
        qr_text_x = qr_x + qr_size + 2 * mm
        qr_text_y = qr_y + (qr_size / 2.0) + (1.3 * mm)
        canvas.drawString(qr_text_x, qr_text_y, "QR Code scannen")
        canvas.drawString(qr_text_x, qr_text_y - (3.8 * mm), "und bezahlen")

        right_col_x = page_doc.leftMargin + page_doc.width
        line_y = footer_top_y - 4 * mm
        for line in bank_lines:
            canvas.drawRightString(right_col_x, line_y, line)
            line_y -= 4.2 * mm

        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer, canvasmaker=NumberedCanvas)
    if save_to_disk and rechnungs_pfad:
        return pdf_path, kunde, rechnungs_nr, nachname, zahlungsziel_str, mahnung.mahnungsnr
    else:
        pdf_buffer.seek(0)
        return pdf_buffer, kunde, rechnungs_nr, nachname, zahlungsziel_str, mahnung.mahnungsnr


@mahnungen_bp.get("/mahnungen/mail/<int:mahnung_id>")
def mahnung_mail(mahnung_id):
    pdf_path, kunde, rechnungs_nr, nachname, zahlungsziel_str, mahnungsnr = generate_mahnung_pdf(mahnung_id, save_to_disk=True)

    if kunde:
        recipient = str(kunde.email or "").strip()
        if not recipient:
            return jsonify({
                "success": False,
                "error": "Für diesen Kunden ist keine E-Mail-Adresse hinterlegt. Versand nicht möglich."
            }), 400

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
            opened = open_macos_mail_with_attachment(recipient, subject, body, pdf_path)
            if not opened:
                mailto = f"mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body)}"
                subprocess.Popen(["open", mailto])
        elif sys.platform.startswith("win"):
            opened = open_windows_mail_with_attachment(recipient, subject, body, pdf_path)
            if not opened:
                mailto = f"mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body)}"
                subprocess.Popen(["cmd", "/c", "start", "", mailto])
        else:
            cmd = [
                "thunderbird",
                "-compose",
                f"to='{recipient}',subject='{subject}',body='{body}',attachment='{pdf_path}'"
            ]
            subprocess.Popen(cmd)
    else:
        return jsonify({
            "success": False,
            "error": "Kein Kunde zur Mahnung gefunden. Versand nicht möglich."
        }), 400

    return jsonify({"success": True, "pdf_path": pdf_path})

@mahnungen_bp.get("/mahnungen/pdf/<int:mahnung_id>")
def mahnung_pdf(mahnung_id):
    pdf_obj, _, _, _, _, _ = generate_mahnung_pdf(mahnung_id, save_to_disk=False)
    return send_file(
        pdf_obj,
        mimetype="application/pdf",
        as_attachment=False,
        download_name="Mahnung.pdf",
    )

