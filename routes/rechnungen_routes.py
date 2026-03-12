from flask import Blueprint, request, jsonify, render_template, render_template_string, current_app as app,  send_file
from database import db
from models import Rechnung, Termin, TermineRechnung, Kunde, Mahnung, Programmvariable, Druckvorlage
from datetime import date, datetime, timedelta
import os
import subprocess
import sys
import qrcode
import pdfkit



def get_zahlungsziel_tage():
    """Holt Zahlungsziel-Tage aus Programmvariablen"""
    zahlungsziel_var = Programmvariable.query.filter_by(name='zahlungsziel_tage_rechnung').first()
    return int(zahlungsziel_var.wert) if zahlungsziel_var else 14


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
        "zahlungsziel_tage": r.zahlungsziel_tage
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
        "zahlungsziel_tage": r.zahlungsziel_tage
    })

# --- Rechnung anlegen ---
@rechnungen_bp.post("/rechnungen")
def add_rechnung():
    data = request.get_json()
    
    # Zahlungsziel aus Daten oder Programmvariablen holen
    zahlungsziel_tage = data.get("zahlungsziel_tage") or get_zahlungsziel_tage()
    
    # Timestamp automatisch setzen, falls nicht im Request
    now_timestamp = int(datetime.now().timestamp())
    r = Rechnung(
        datum=data["datum"],
        betrag=data["betrag"],
        rechnungsnr=data.get("rechnungsnr"),
        bezahlt=data.get("bezahlt", 0),
        rechnungTextOben=data.get("rechnungTextOben"),
        rechnungTextUnten=data.get("rechnungTextUnten"),
        kommentar=data.get("kommentar"),
        timestamp=data.get("timestamp", now_timestamp),
        changestamp=data.get("changestamp"),
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
        "kommentar","timestamp","changestamp","zahlungsziel_tage"
    ]:
        if field in data:
            setattr(r, field, data[field])
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
            "zahlungsziel_datum": zahlungsziel_datum
        },
        "termine": termine_json
    })


def generate_rechnung_pdf(rechnung_id):
    """Rechnung laden, HTML rendern, QR-Code + PDF erzeugen"""
 
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

    # Firma-Daten
    firma = {
        "name": standort.name if standort else "",
        "adresse": standort.adresse if standort else "",
        "plz": standort.plz if standort else "",
        "ort": standort.ort if standort else "",
        "email": standort.email if standort else "",
        "iban": standort.iban if standort else "",
        "bic": standort.bic if standort else "",
        "kontoName": standort.kontoName if standort else "",
        "bankname": standort.bankname if standort else ""
    }

    # Lade Logo-Pfad
    from models import Programmvariable
    logo_var = Programmvariable.query.filter_by(name='logo_file').first()
    logo_filename = logo_var.wert if logo_var and logo_var.wert else "static/firmen_logo_fuer_schreiben.png"
    
    # Konvertiere zu absolutem Pfad 
    # Entferne /static/ Prefix falls vorhanden
    if logo_filename.startswith('/static/'):
        logo_filename = logo_filename[8:]  # Entferne "/static/"
    elif logo_filename.startswith('static/'):
        logo_filename = logo_filename[7:]  # Entferne "static/"
    
    logo_absolute_path = os.path.join(app.root_path, 'static', logo_filename)
    
    # Übergebe absoluten Pfad an Template
    logo_path = f"file://{logo_absolute_path}"

    # QR-Code-Pfad zu absoluter URL konvertieren
    qr_filename = f"girocode_{r.rechnungsnr}.png"
    qr_absolute_path = os.path.join(app.root_path, 'static/girocode', qr_filename)
    qr_path_file_url = f"file://{qr_absolute_path}" if os.path.exists(qr_absolute_path) else ""

    # HTML rendern
    if kunde and kunde.druckvorlage_id:
        druckvorlage = Druckvorlage.query.get(kunde.druckvorlage_id)
        if druckvorlage and druckvorlage.pfad:
            template_name = druckvorlage.pfad
            if os.path.isabs(template_name):
                template_root = os.path.join(app.root_path, "templates")
                try:
                    template_name = os.path.relpath(template_name, template_root)
                except ValueError:
                    pass
            if template_name.startswith("Vorlagen/"):
                template_name = template_name[len("Vorlagen/"):]
            if template_name.startswith("vorlagen/"):
                template_name = template_name[len("vorlagen/"):]
            if template_name.startswith("templates/"):
                template_name = template_name[len("templates/"):]
            if template_name.startswith("/"):
                template_name = template_name[1:]

    # Zahlungsziel-Datum berechnen
    zahlungsziel_datum = None
    try:
        if r.datum and r.zahlungsziel_tage is not None:
            rechnungsdatum = datetime.strptime(str(r.datum), "%Y-%m-%d")
            zahlungsziel_datum = (rechnungsdatum + timedelta(days=int(r.zahlungsziel_tage))).strftime("%Y-%m-%d")
    except Exception:
        zahlungsziel_datum = None

    template_context = {
        "firma": firma,
        "kunde": kunde,
        "rechnung": r,
        "positionen": termine_json,
        "logo_path": logo_path,
        "qr_code_path": qr_path_file_url,
        "diagnose": getattr(kunde, "diagnose", "") if kunde else "",
        "svnr": getattr(kunde, "svnr", "") if kunde else "",
        "krankenkasse": getattr(kunde, "krankenkasse", "") if kunde else "",
        "zahlungsziel_datum": zahlungsziel_datum,
     }
     # print("Template Kontext:", template_context )

    templates_root = os.path.join(app.root_path, "templates")
    template_in_templates = os.path.join(templates_root, template_name)
    if os.path.exists(template_in_templates):
        html_content = render_template(template_name, **template_context)
    else:
        candidate_paths = []
        if os.path.isabs(template_name):
            candidate_paths.append(template_name)
        else:
            candidate_paths.extend([
                os.path.join(app.root_path, template_name),
                os.path.join(app.root_path, "Vorlagen", template_name),
                os.path.join(app.root_path, "Vorlagen", "DruckvorlageRechnung.html"),
            ])

        template_file = next((p for p in candidate_paths if os.path.exists(p)), None)
        if not template_file:
            raise FileNotFoundError(f"Druckvorlage nicht gefunden: {template_name}")

        with open(template_file, "r", encoding="utf-8") as f:
            template_source = f.read()
        html_content = render_template_string(template_source, **template_context)

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
    qr_path = os.path.join(app.root_path, "static/girocode", qr_filename)
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

  
   # Footer HTML-Datei laden
    footer_file_path = os.path.join(app.root_path, "Vorlagen", "Druckvorlage_Footer.html")
    with open(footer_file_path, "r", encoding="utf-8") as f:
        footer_template_source = f.read()

    # Footer rendern mit qr_code_path
    footer_html_rendered = render_template_string(
        footer_template_source,
        firma=firma,
        qr_code_path=qr_path_file_url   # <-- hier wird das Bild gesetzt
    )

    # Temporäre Footer-Datei speichern
    temp_footer_path = os.path.join(app.root_path, "Vorlagen", "footer_rendered.html")
    with open(temp_footer_path, "w", encoding="utf-8") as f:
        f.write(footer_html_rendered)

    # wkhtmltopdf Option setzen
    options = {
    'enable-local-file-access': None,
    'margin-top': '10mm',
    'margin-bottom': '35mm',
    'margin-left': '20mm',
    'margin-right': '20mm',
    'footer-html': "file:///" + temp_footer_path.replace("\\", "/"),
    'footer-center': '[page]/[toPage]',
    'footer-font-size': '10',
    'footer-spacing': '5'
}


    pdfkit.from_string(html_content, pdf_path, options=options)

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
            mailto = f"mailto:{recipient}?subject={subject}&body={body}"
            subprocess.Popen(["open", mailto])
            subprocess.Popen(["open", "-a", "Mail", pdf_path])
        elif sys.platform.startswith("win"):
            # Windows: Standard-Mailclient via mailto
            mailto = f"mailto:{recipient}?subject={subject}&body={body}"
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
                zahlungsziel_tage=zahlungsziel_tage
            )
            db.session.add(rechnung)
            db.session.flush()  # 🔑 erzeugt rechnung.id OHNE commit

            # 4️⃣ Zuordnung in termine_rechnungen
            for s in kunden_termine:
                link = TermineRechnung(
                    rechnung_id=rechnung.id,
                    termin_id=s.id   # bleibt so
                )
                db.session.add(link)

            erstellte_rechnungen.append({
                "kunde_id": kunde_id,
                "rechnung_id": rechnung.id,
                "termine": [s.id for s in kunden_termine]
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
