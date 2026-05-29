from flask import Blueprint, request, jsonify, current_app as app, send_file
from database import db
from models import Rechnung, Termin, TermineRechnung, Kunde, Mahnung, Programmvariable, Druckvorlage
from datetime import date, datetime, timedelta, timezone
import os
import subprocess
import sys
from urllib.parse import quote
import qrcode
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle



def get_zahlungsziel_tage():
    """Holt Zahlungsziel-Tage aus Programmvariablen"""
    zahlungsziel_var = Programmvariable.query.filter_by(name='zahlungsziel_tage_rechnung').first()
    return int(zahlungsziel_var.wert) if zahlungsziel_var else 14


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

    # 1) Bevorzugt: pywin32, falls verfügbar
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

    # 2) Fallback ohne zusätzliche Python-Abhängigkeit: Outlook COM via PowerShell
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


rechnungen_bp = Blueprint("rechnungen", __name__)

# --- Alle Rechnungen ---
@rechnungen_bp.get("/rechnungen")
def get_all_rechnungen():
    rechnungen = Rechnung.query.order_by(Rechnung.datum.desc()).all()
    return jsonify([{
        "id": r.id,
        "datum": r.datum,
        "betrag": r.betrag,
        "rechnungsnr": r.rechnungsnr,
        "bezahlt": r.bezahlt,
        "rechnungTextOben": r.rechnungTextOben,
        "rechnungTextUnten": r.rechnungTextUnten,
        "kommentar": r.kommentar,
        "timestamp": r.timestamp,
        "changestamp": r.changestamp,
        "zahlungsziel_tage": r.zahlungsziel_tage,
        "zahlungsverweis": r.zahlungsverweis
    } for r in rechnungen])

# --- Einzelne Rechnung ---
@rechnungen_bp.get("/rechnungen/<int:id>")
def get_rechnung(id):
    r = Rechnung.query.get_or_404(id)
    return jsonify({
        "id": r.id,
        "datum": r.datum,
        "betrag": r.betrag,
        "rechnungsnr": r.rechnungsnr,
        "bezahlt": r.bezahlt,
        "rechnungTextOben": r.rechnungTextOben,
        "rechnungTextUnten": r.rechnungTextUnten,
        "kommentar": r.kommentar,
        "timestamp": r.timestamp,
        "changestamp": r.changestamp,
        "zahlungsziel_tage": r.zahlungsziel_tage,
        "zahlungsverweis": r.zahlungsverweis
    })

# --- Rechnung anlegen ---
@rechnungen_bp.post("/rechnungen")
def add_rechnung():
    data = request.get_json()
    
    # Zahlungsziel aus Daten oder Programmvariablen holen
    zahlungsziel_tage = data.get("zahlungsziel_tage") or get_zahlungsziel_tage()
    
    # Timestamp automatisch setzen, falls nicht im Request
    now_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    from datetime import datetime
    r = Rechnung(
        datum=data["datum"],
        betrag=data["betrag"],
        rechnungsnr=data.get("rechnungsnr"),
        bezahlt=data.get("bezahlt", 0),
        rechnungTextOben=data.get("rechnungTextOben"),
        rechnungTextUnten=data.get("rechnungTextUnten"),
        kommentar=data.get("kommentar"),
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        zahlungsziel_tage=zahlungsziel_tage
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"success": True, "id": r.id}), 201

# --- Rechnung ändern ---
@rechnungen_bp.put("/rechnungen/<int:id>")
def update_rechnung(id):
    r = Rechnung.query.get_or_404(id)
    data = request.get_json()
    for field in [
        "datum","betrag","rechnungsnr",
        "bezahlt","rechnungTextOben","rechnungTextUnten",
        "kommentar","timestamp","zahlungsziel_tage","zahlungsverweis"
    ]:
        if field in data:
            setattr(r, field, data[field])
    # changestamp immer setzen
    r.changestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    db.session.commit()
    return jsonify({"success": True})

# --- Rechnung löschen ---
@rechnungen_bp.delete("/rechnungen/<int:id>")
def delete_rechnung(id):
    r = Rechnung.query.get_or_404(id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({"success": True})


# --- Rechnungen mit Kundendaten ---
@rechnungen_bp.get("/rechnungen/mit-kunde")
def get_rechnungen_mit_kunde():
    """
    Liefert alle Rechnungen mit den Kundendaten, die zu den enthaltenen Termine gehören.
    Jede Rechnung erscheint nur einmal.
    """
    result = (
        db.session.query(
            Rechnung.id.label("rechnung_id"),
            Rechnung.datum,
            Rechnung.betrag,
            Rechnung.rechnungsnr,
            Rechnung.bezahlt,
            Rechnung.rechnungTextOben,
            Rechnung.rechnungTextUnten,
            Rechnung.kommentar,
            Rechnung.zahlungsziel_tage,
            Rechnung.zahlungsverweis,
            Kunde.id.label("kunde_id"),
            Kunde.vorname,
            Kunde.nachname,
            Kunde.kuerzel,
            Kunde.email,
            Kunde.adresse,
            Kunde.plz,
            Kunde.ort
        )
        .join(TermineRechnung, TermineRechnung.rechnung_id == Rechnung.id)
        .join(Termin, Termin.id == TermineRechnung.termin_id)
        .join(Kunde, Kunde.id == Termin.kunde_id)
        .group_by(Rechnung.id, Kunde.id)  # sorgt dafür, dass jede Rechnung nur einmal kommt
        .order_by(Rechnung.datum.desc(), Kunde.nachname)
        .all()
    )

    # Ergebnis in JSON umwandeln
    rechnungen = [
        {
            "rechnung_id": r.rechnung_id,
            "datum": r.datum,
            "betrag": r.betrag,
            "rechnungsnr": r.rechnungsnr,
            "bezahlt": r.bezahlt,
            "rechnungTextOben": r.rechnungTextOben,
            "rechnungTextUnten": r.rechnungTextUnten,
            "kommentar": r.kommentar,
            "zahlungsziel_tage": r.zahlungsziel_tage,
            "zahlungsverweis": r.zahlungsverweis,
            "kunde_id": r.kunde_id,
            "vorname": r.vorname,
            "nachname": r.nachname,
            "kuerzel": r.kuerzel,
            "email": r.email,
            "adresse": r.adresse,
            "plz": r.plz,
            "ort": r.ort
        }
        for r in result
    ]

    return jsonify(rechnungen)



# --- Alle Termine für eine Rechnung ---
@rechnungen_bp.get("/rechnungen/<int:rechnung_id>/termine")
def get_termine_fuer_rechnung(rechnung_id):
    """
    Liefert alle Termine für eine Rechnung
    + Rechnungsnummer
    + Rechnungstexte
    """

    # 1️⃣ Rechnung laden
    rechnung = Rechnung.query.get_or_404(rechnung_id)

    # 2️⃣ Termine laden
    termine = (
        db.session.query(Termin)
        .join(TermineRechnung, TermineRechnung.termin_id == Termin.id)
        .filter(TermineRechnung.rechnung_id == rechnung_id)
        .order_by(Termin.datum.desc(), Termin.startzeit)
        .all()
    )
 

    # 3️⃣ Termine serialisieren
    termine_json = []
    for s in termine:
        gruppenkuerzel = None
        if getattr(s, "gruppentermin_id", None):
            from models.gruppentermine import Gruppentermin
            gruppentermin = Gruppentermin.query.get(s.gruppentermin_id)
            if gruppentermin and gruppentermin.gruppe_id:
                from models.gruppen import Gruppe
                gruppe = Gruppe.query.get(gruppentermin.gruppe_id)
                if gruppe:
                    gruppenkuerzel = gruppe.gruppenkuerzel
        termine_json.append({
            "termine_id": s.id,
            "kunde_id": s.kunde_id,
            "datum": s.datum,
            "startzeit": s.startzeit,
            "endzeit": s.endzeit,
            "beschreibung": s.beschreibung,
            "kommentar": s.kommentar,
            "betrag": s.betrag,
            "abgesagt": s.abgesagt,
            "timestamp": s.timestamp,
            "changestamp": s.changestamp,
            "gruppenkuerzel": gruppenkuerzel
        })

    # 4️⃣ Antwort
    # Zahlungsziel-Datum berechnen
    zahlungsziel_datum = None
    try:
        if rechnung.datum and rechnung.zahlungsziel_tage is not None:
            rechnungsdatum = datetime.strptime(str(rechnung.datum), "%Y-%m-%d")
            zahlungsziel_datum = (rechnungsdatum + timedelta(days=int(rechnung.zahlungsziel_tage))).strftime("%Y-%m-%d")
    except Exception:
        zahlungsziel_datum = None

    print("Zahlungsziel Datum:", zahlungsziel_datum)

    return jsonify({
        "rechnung": {
            "id": rechnung.id,
            "rechnungsnr": rechnung.rechnungsnr,
            "rechnungTextOben": rechnung.rechnungTextOben,
            "rechnungTextUnten": rechnung.rechnungTextUnten,
            "kommentar": rechnung.kommentar,
            "datum": rechnung.datum,
            "zahlungsziel_tage": rechnung.zahlungsziel_tage,
            "zahlungsziel_datum": zahlungsziel_datum,
            "zahlungsverweis": rechnung.zahlungsverweis
        },
        "termine": termine_json
    })


def generate_rechnung_pdf(rechnung_id):
    """Rechnung laden und mit ReportLab als PDF erzeugen."""

    r = Rechnung.query.get_or_404(rechnung_id)

    # Termine laden
    termine = (
        db.session.query(Termin)
        .join(TermineRechnung, TermineRechnung.termin_id == Termin.id)
        .filter(TermineRechnung.rechnung_id == rechnung_id)
        .order_by(Termin.datum.desc(), Termin.startzeit)
        .all()
    )

    termine_json = [
        {
            "termine_id": s.id,
            "kunde_id": s.kunde_id,
            "datum": s.datum,
            "startzeit": s.startzeit,
            "endzeit": s.endzeit,
            "beschreibung": s.beschreibung,
            "kommentar": s.kommentar,
            "betrag": s.betrag,
            "abgesagt": s.abgesagt,
            "timestamp": s.timestamp,
            "changestamp": s.changestamp
        }
        for s in termine
    ]

    kunde = Kunde.query.get_or_404(termine_json[0]["kunde_id"]) if termine_json else None
    standort = kunde.standort if kunde else None

    # Gesamtbetrag
    gesamtbetrag = sum(s["betrag"] for s in termine_json)
    r.gesamtbetrag = gesamtbetrag

    # Zahlungsziel-Datum berechnen
    zahlungsziel_datum = None
    try:
        if r.datum and r.zahlungsziel_tage is not None:
            rechnungsdatum = datetime.strptime(str(r.datum), "%Y-%m-%d")
            zahlungsziel_datum = (rechnungsdatum + timedelta(days=int(r.zahlungsziel_tage))).strftime("%Y-%m-%d")
    except Exception:
        zahlungsziel_datum = None

    # PDF-Dateiname
    now_str = datetime.now().strftime("%y%m%d_%H%M")
    rechnungs_nr = r.rechnungsnr
    druckvorlage_kuerzel = ""
    if kunde and getattr(kunde, "druckvorlage_id", None):
        druckvorlage = Druckvorlage.query.get(kunde.druckvorlage_id)
        if druckvorlage and getattr(druckvorlage, "kuerzel", None):
            druckvorlage_kuerzel = f"_{druckvorlage.kuerzel}_"
    kuerzel = kunde.kuerzel if kunde else "kunde"
    pdf_filename = f"ReNr_{rechnungs_nr}_{now_str}_{druckvorlage_kuerzel}_{kuerzel}.pdf"
    folder_path = os.path.join(app.root_path, "Rechnungen")
    os.makedirs(folder_path, exist_ok=True)
    pdf_path = os.path.join(folder_path, pdf_filename)

    # QR-Code
    qr_filename = f"girocode_{rechnungs_nr}.png"
    qr_dir = os.path.join(app.root_path, "static", "girocode")
    os.makedirs(qr_dir, exist_ok=True)
    qr_path = os.path.join(qr_dir, qr_filename)
    if os.path.exists(qr_path):
        os.remove(qr_path)

    data = f"""BCD
001
1
SCT
{standort.bic}
{standort.kontoName}
{standort.iban}
EUR{gesamtbetrag}
ReNR:{rechnungs_nr}
"""
    img = qrcode.make(data)
    img.save(qr_path)

    logo_var = Programmvariable.query.filter_by(name='logo_file').first()
    logo_filename = logo_var.wert if logo_var and logo_var.wert else "static/firmen_logo_fuer_schreiben.png"
    logo_absolute_path = os.path.join(app.root_path, logo_filename.lstrip('/'))

    firma_name = standort.name if standort else ""
    firma_ort = f"{standort.plz or ''} {standort.ort or ''}".strip() if standort else ""

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

    story.append(Paragraph(f"Rechnung Nr. {escape(str(rechnungs_nr))}", styles["Heading"]))
    story.append(Paragraph(f"Rechnungsdatum: {escape(str(r.datum or ''))}", styles["Body"]))
    if zahlungsziel_datum:
        story.append(Paragraph(f"Zahlungsziel: {escape(str(zahlungsziel_datum))}", styles["Body"]))
    story.append(Spacer(1, 4 * mm))

    if kunde:
        story.append(Paragraph("Rechnung an:", styles["Body"]))
        story.append(Paragraph(escape(f"{kunde.vorname or ''} {kunde.nachname or ''}".strip()), styles["BodySmall"]))
        if kunde.adresse:
            story.append(Paragraph(escape(kunde.adresse), styles["BodySmall"]))
        ort = f"{kunde.plz or ''} {kunde.ort or ''}".strip()
        if ort:
            story.append(Paragraph(escape(ort), styles["BodySmall"]))
        story.append(Spacer(1, 5 * mm))

    _append_multiline_paragraphs(story, r.rechnungTextOben, styles["Body"])
    if r.rechnungTextOben:
        story.append(Spacer(1, 2 * mm))

    table_data = [["Datum", "Zeit", "Beschreibung", "Betrag (EUR)"]]
    for t in termine_json:
        time_range = f"{t.get('startzeit') or ''} - {t.get('endzeit') or ''}".strip(" -")
        table_data.append([
            str(t.get("datum") or ""),
            time_range,
            str(t.get("beschreibung") or ""),
            _format_currency(t.get("betrag") or 0),
        ])
    table_data.append(["", "", "Gesamt", _format_currency(gesamtbetrag)])

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

    _append_multiline_paragraphs(story, r.rechnungTextUnten, styles["Body"])

    if standort:
        story.append(Spacer(1, 4 * mm))
        if standort.kontoName:
            story.append(Paragraph(f"Kontoinhaber: {escape(str(standort.kontoName))}", styles["BodySmall"]))
        if standort.iban:
            story.append(Paragraph(f"IBAN: {escape(str(standort.iban))}", styles["BodySmall"]))
        if standort.bic:
            story.append(Paragraph(f"BIC: {escape(str(standort.bic))}", styles["BodySmall"]))

    if os.path.exists(qr_path):
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("GiroCode", styles["BodySmall"]))
        qr_image = Image(qr_path)
        qr_image.drawHeight = 28 * mm
        qr_image.drawWidth = 28 * mm
        story.append(qr_image)

    doc.build(story)

    return pdf_path, kunde, rechnungs_nr, kunde.nachname if kunde else ""

# --- Endpoint: PDF anzeigen ---
@rechnungen_bp.get("/rechnungen/pdf/<int:rechnung_id>")
def rechnung_pdf(rechnung_id):
    pdf_path, _, _, _ = generate_rechnung_pdf(rechnung_id)
    return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)

# --- Endpoint: PDF + Mail versenden ---
@rechnungen_bp.get("/rechnungen/mail/<int:rechnung_id>")
def rechnung_mail(rechnung_id):
    pdf_path, kunde, rechnungs_nr, nachname = generate_rechnung_pdf(rechnung_id)
    print(nachname)

    if kunde:
        recipient = kunde.email
        geschlecht = getattr(kunde, "geschlecht", "").lower()
        if geschlecht == "m":
            anrede = f"Hallo Herr {nachname},"
        elif geschlecht == "w":
            anrede = f"Hallo Frau {nachname},"
        else:
            anrede = f"Hallo {kunde.vorname} {nachname},"

        subject = f"Rechnung {rechnungs_nr}"
        
        # Text aus Programmvariable holen
        from models import Programmvariable
        email_text_var = Programmvariable.query.filter_by(name='rechnung_text_email').first()
        if email_text_var and email_text_var.wert:
            body = f"{anrede}\n\n{email_text_var.wert}"
        else:
            body = anrede

        if sys.platform.startswith("darwin"):
            # macOS: Mail.app via open
            mailto = f"mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body)}"
            subprocess.Popen(["open", mailto])
            subprocess.Popen(["open", "-a", "Mail", pdf_path])
        elif sys.platform.startswith("win"):
            # Windows: Outlook mit echtem PDF-Anhang, mailto nur als Fallback
            opened = open_windows_mail_with_attachment(recipient, subject, body, pdf_path)
            if not opened:
                mailto = f"mailto:{quote(recipient)}?subject={quote(subject)}&body={quote(body)}"
                subprocess.Popen(["cmd", "/c", "start", "", mailto])
        else:
            # Linux: xdg-email
            cmd = [
                "xdg-email",
                "--subject", subject,
                "--body", body,
                "--attach", pdf_path,
                recipient
            ]
            subprocess.Popen(cmd)

    return jsonify({"success": True, "pdf_path": pdf_path})



#--- Rechnungen aus Termine erstellen ---
@rechnungen_bp.post("/rechnungen/aus-termine")
def create_rechnungen_aus_termine():
    data = request.get_json()

    # Prüfen, ob JSON ein Array direkt ist oder ein Objekt mit Key "termine_ids"
    if isinstance(data, list):
        termine_ids = data
    else:
        termine_ids = data.get("termine_ids")


    if not termine_ids:
        return jsonify({"error": "Keine Termine übergeben"}), 400

    try:
        # 1️⃣ Termine laden
        termine = Termin.query.filter(Termin.id.in_(termine_ids)).all()

        if not termine:
            raise ValueError("Keine gültigen Termine gefunden")

        # 2️⃣ Termine nach Kunde gruppieren
        termine_pro_kunde = {}
        for s in termine:
            # Kontrollzeile: Kunde und Termin prüfen

            if s.kunde_id not in termine_pro_kunde:
                termine_pro_kunde[s.kunde_id] = []
            termine_pro_kunde[s.kunde_id].append(s)


        erstellte_rechnungen = []

        # 3️⃣ Für jeden Kunden eine Rechnung
        for kunde_id, kunden_termine in termine_pro_kunde.items():
            gesamtbetrag = sum(s.betrag or 0 for s in kunden_termine)

            # --- Kunde laden, um Texte zu übernehmen ---
            kunde = Kunde.query.get(kunde_id)
            if not kunde:
                raise ValueError(f"Kunde {kunde_id} nicht gefunden")

            # Prüfe, ob Druckvorlage vorhanden ist
            if not kunde.druckvorlage_id:
                return jsonify({
                    "success": False,
                    "error": f"Kunde {kunde.nachname} ({kunde_id}) hat keine Druckvorlage hinterlegt. Bitte zuerst eine Druckvorlage auswählen."
                }), 400

            # --- Rechnungsnummer generieren ---
            jahr = date.today().year % 100  # z. B. 25 für 2025

            # Höchste existierende Rechnungsnummer dieses Jahres abrufen
            letzte_rechnung = (
                Rechnung.query
                .filter(Rechnung.rechnungsnr.like(f"{jahr}%"))
                .order_by(Rechnung.rechnungsnr.desc())
                .first()
            )

            if letzte_rechnung and letzte_rechnung.rechnungsnr:
                # Letzte NNN extrahieren und +1
                letzte_nnn = int(str(letzte_rechnung.rechnungsnr)[2:])
                neue_nnn = letzte_nnn + 1
            else:
                neue_nnn = 1

            rechnungsnr = int(f"{jahr}{neue_nnn:03d}")  # z. B. 25001

            # Zahlungsziel aus Programmvariablen holen
            zahlungsziel_tage = get_zahlungsziel_tage()

            rechnung = Rechnung(
                datum=date.today(),
                betrag=gesamtbetrag,
                bezahlt=0,
                rechnungsnr=rechnungsnr,
                rechnungTextOben=kunde.rechnungTextObenVorgabe,
                rechnungTextUnten=kunde.rechnungTextUntenVorgabe,
                zahlungsziel_tage=zahlungsziel_tage,
                timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            db.session.add(rechnung)
            db.session.flush()  # 🔑 erzeugt rechnung.id OHNE commit

            # 4️⃣ Zuordnung in termine_rechnungen
            for s in kunden_termine:
                link = TermineRechnung(
                    rechnung_id=rechnung.id,
                    termin_id=s.id,   # bleibt so
                    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                db.session.add(link)

            erstellte_rechnungen.append({
                "kunde_id": kunde_id,
                "rechnung_id": rechnung.id,
                "termine": [s.id for s in kunden_termine],
                "rechnungsnr": rechnung.rechnungsnr
            })

        db.session.commit()

        # ✅ ALLES erfolgreich
        return jsonify({
            "success": True,
            "rechnungen": erstellte_rechnungen
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# --- Mahnungen für eine Rechnung ---
@rechnungen_bp.get("rechnungen/<int:rechnung_id>/mahnungen")
def get_mahnungen_fuer_rechnung(rechnung_id):
    mahnungen = Mahnung.query.filter_by(rechnung_id=rechnung_id).order_by(Mahnung.datum.desc()).all()
    return jsonify([{
        "id": m.id,
        "datum": m.datum,
        "kommentar": m.kommentar,
        "mahnungsnr": m.mahnungsnr,
        "verzugszinsenProz": m.verzugszinsenProz,
        "mahnspesen": m.mahnspesen,
        "verzugszinsen": m.verzugszinsen,
        "zahlungsziel_tage":m.zahlungsziel_tage
    } for m in mahnungen])
