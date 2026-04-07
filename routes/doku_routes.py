
from flask import Blueprint, request, send_file, abort, render_template
from models import Kunde, Termin, Gruppe, Gruppentermin, GruppenKunde
from database import db
from datetime import datetime
import pdfkit
import os

doku_bp = Blueprint("doku", __name__)

# --- PDF-Export aller Dokus eines Kunden (Einzel + Gruppen) ---
@doku_bp.route("/doku/kunde/<int:kunde_id>/pdf")
def export_dokus_kunde_pdf(kunde_id):
    kunde = Kunde.query.get_or_404(kunde_id)
    # Einzeltermine mit Doku
    termine = Termin.query.filter_by(kunde_id=kunde_id, nur_offline_vorhanden=0, nur_offline_geloescht=0).all()
    einzel_dokus = [
        {
            "dokuId": t.id,
            "datum": t.datum,
            "utc_starttime": t.utc_starttime,
            "utc_endtime": t.utc_endtime,
            "beschreibung": t.beschreibung,
            "doku": t.doku,
            "pers_doku": t.pers_doku,
            "anzeigeName": f"{kunde.vorname} {kunde.nachname}",
            "type": "kunde",
            "abgesagt": t.abgesagt == "1"
        }
        for t in termine if t.doku and t.doku.strip()
    ]
    # Gruppen des Kunden
    gruppen = db.session.query(Gruppe).join(GruppenKunde, GruppenKunde.gruppe_id == Gruppe.id).filter(GruppenKunde.kunde_id == kunde_id).all()
    gruppen_dokus = []
    for gruppe in gruppen:
        gruppentermine = Gruppentermin.query.filter_by(gruppe_id=gruppe.id, nur_offline_vorhanden=0, nur_offline_geloescht=0).all()
        for g in gruppentermine:
            if g.doku and g.doku.strip():
                gruppen_dokus.append({
                    "dokuId": g.id,
                    "datum": g.datum,
                    "utc_starttime": g.utc_starttime,
                    "utc_endtime": g.utc_endtime,
                    "beschreibung": g.beschreibung,
                    "doku": g.doku,
                    "pers_doku": g.pers_doku,
                    "anzeigeName": gruppe.gruppenname,
                    "type": "gruppe",
                    "abgesagt": False,
                    "entfallen": g.entfallen == "1"
                })
    # Kombinieren und sortieren
    alle_dokus = einzel_dokus + gruppen_dokus
    alle_dokus.sort(key=lambda d: d["datum"] or "", reverse=True)
    # HTML generieren
    html_content = render_template("doku_export.html", kunde=kunde, alle_dokus=alle_dokus) # PDF-Dateiname und Pfad
    now_str = datetime.now().strftime("%y%m%d_%H%M%S")
    pdf_filename = f"Doku_{kunde.kuerzel}_{now_str}.pdf"
    folder_path = os.path.join(os.path.dirname(__file__), "..", "Rechnungen")
    folder_path = os.path.abspath(folder_path)
    os.makedirs(folder_path, exist_ok=True)
    pdf_path = os.path.join(folder_path, pdf_filename)
    # PDF erzeugen
    options = {
        'enable-local-file-access': None,
        'margin-top': '15mm',
        'margin-bottom': '15mm',
        'margin-left': '15mm',
        'margin-right': '15mm',
    }
    pdfkit.from_string(html_content, pdf_path, options=options)
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename, mimetype="application/pdf")
