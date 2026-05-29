
from flask import Blueprint, request, send_file
from models import Kunde, Termin, Gruppe, Gruppentermin, GruppenKunde
from database import db
from datetime import datetime
import os
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

doku_bp = Blueprint("doku", __name__)


def _append_multiline(story, text, style):
    if not text:
        return
    for line in str(text).splitlines():
        if line.strip():
            story.append(Paragraph(escape(line.strip()), style))
        else:
            story.append(Spacer(1, 0.5 * mm))


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


def _format_time_short(value):
    if not value:
        return ""
    text = str(value).strip()
    for time_format in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, time_format).strftime("%H:%M")
        except ValueError:
            continue
    return text[:5] if len(text) >= 5 else text

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
            "startzeit": t.startzeit,
            "endzeit": t.endzeit,
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
                    "startzeit": g.startzeit,
                    "endzeit": g.endzeit,
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
    # Filter aus Query-Parameter lesen
    doku_filter = request.args.get("filter", "ges")
    now_str = datetime.now().strftime("%y%m%d_%H%M%S")
    pdf_filename = f"Dokuexport_{kunde.kuerzel}_{now_str}.pdf"
    folder_path = os.path.join(os.path.dirname(__file__), "..", "Rechnungen")
    folder_path = os.path.abspath(folder_path)
    os.makedirs(folder_path, exist_ok=True)
    pdf_path = os.path.join(folder_path, pdf_filename)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocHeading", parent=styles["Heading2"], fontSize=14, leading=17))
    styles.add(ParagraphStyle(name="DocMeta", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="DocBody", parent=styles["Normal"], fontSize=10, leading=14))

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Dokuexport",
    )

    story = []
    if doku_filter == "allg":
        heading = f"Allgemeine Dokumentation: {kunde.vorname or ''} {kunde.nachname or ''}".strip()
    elif doku_filter == "pers":
        heading = f"Persoenliche Dokumentation: {kunde.vorname or ''} {kunde.nachname or ''}".strip()
    else:
        heading = f"Dokumentation: {kunde.vorname or ''} {kunde.nachname or ''}".strip()

    story.append(Paragraph(escape(heading), styles["DocHeading"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"Export am: {escape(datetime.now().strftime('%d.%m.%Y %H:%M'))}", styles["DocMeta"]))
    story.append(Spacer(1, 6 * mm))

    if not alle_dokus:
        story.append(Paragraph("Keine Dokumentationseinträge vorhanden.", styles["DocBody"]))
    else:
        previous_datum = None
        for index, entry in enumerate(alle_dokus):
            aktuelles_datum = str(entry.get("datum") or "")
            if index > 0 and aktuelles_datum != previous_datum:
                story.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.6,
                        color=colors.HexColor("#CFCFCF"),
                        spaceBefore=1 * mm,
                        spaceAfter=4 * mm,
                    )
                )

            status_parts = []
            if entry.get("abgesagt"):
                status_parts.append("abgesagt")
            if entry.get("entfallen"):
                status_parts.append("entfallen")
            status = f" ({', '.join(status_parts)})" if status_parts else ""

            datum_text = _format_date_de(entry.get("datum"))
            startzeit_text = _format_time_short(entry.get("startzeit"))
            endzeit_text = _format_time_short(entry.get("endzeit"))
            zeit_text = ""
            if startzeit_text and endzeit_text:
                zeit_text = f" {startzeit_text}-{endzeit_text}"
            elif startzeit_text:
                zeit_text = f" {startzeit_text}"

            title = f"{datum_text}{zeit_text}{status}"
            story.append(Paragraph(escape(title.strip()), styles["DocMeta"]))

            beschreibung = entry.get("beschreibung") or ""
            if beschreibung.strip():
                story.append(Paragraph(f"<b>Bezeichnung:</b> {escape(beschreibung.strip())}", styles["DocBody"]))

            doku_text = entry.get("doku") or ""
            if doku_text.strip() and doku_filter in ("ges", "allg"):
                story.append(Paragraph("<b>Allgemeine Dokumentation:</b>", styles["DocMeta"]))
                _append_multiline(story, doku_text, styles["DocBody"])

            pers_text = entry.get("pers_doku") or ""
            if pers_text.strip() and doku_filter in ("ges", "pers"):
                story.append(Spacer(1, 1.2 * mm))
                story.append(Paragraph("<b>Persoenliche Dokumentation:</b>", styles["DocMeta"]))
                _append_multiline(story, pers_text, styles["DocBody"])

            story.append(Spacer(1, 5 * mm))
            previous_datum = aktuelles_datum

    doc.build(story)
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename, mimetype="application/pdf")
