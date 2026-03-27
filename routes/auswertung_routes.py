from flask import Blueprint, render_template, jsonify, request
from models import Rechnung, Termin, Gruppentermin, Kunde, Gruppe
from sqlalchemy import extract, func

auswertung_bp = Blueprint("auswertung", __name__)

@auswertung_bp.route("/auswertung")
def auswertung_page():
    return render_template("auswertung.html")

@auswertung_bp.route("/api/auswertung/jahre")
def auswertung_jahre():
    # Alle Jahre, die in Rechnungen vorkommen
    jahre = (
        Rechnung.query.with_entities(extract('year', Rechnung.datum).label('jahr'))
        .distinct().order_by('jahr').all()
    )
    return jsonify([int(j.jahr) for j in jahre if j.jahr])

@auswertung_bp.route("/api/auswertung/jahrestabelle")
def auswertung_jahrestabelle():
    # Für jedes Jahr: Einnahmen gesamt, umsatzsteuerpflichtig, nicht umsatzsteuerpflichtig, Termine, Zeit, abgesagte Termine, analog für Gruppen
    jahre = (
        Rechnung.query.with_entities(extract('year', Rechnung.datum).label('jahr'))
        .distinct().order_by('jahr').all()
    )
    result = []
    for j in jahre:
        jahr = int(j.jahr)
        rechnungen = Rechnung.query.filter(extract('year', Rechnung.datum) == jahr).all()
        einnahmen_gesamt = sum(r.betrag for r in rechnungen)
        einnahmen_umsatz = 0
        einnahmen_nicht_umsatz = 0
        for r in rechnungen:
            # Kunde zu Rechnung finden (über Termin)
            kunde_ust = None
            for tr in r.termine_rechnungen:
                if tr.termin and tr.termin.kunde and hasattr(tr.termin.kunde, 'ust'):
                    kunde_ust = tr.termin.kunde.ust
                    break
            if kunde_ust == 1:
                einnahmen_umsatz += r.betrag
            else:
                einnahmen_nicht_umsatz += r.betrag
        # Einzeltermine
        termine = Termin.query.filter(extract('year', Termin.datum) == jahr).all()
        abgehalten = len([t for t in termine if not t.abgesagt])
        abgesagt = len([t for t in termine if t.abgesagt])
        minuten = sum([int(t.dauer_min) if hasattr(t, 'dauer_min') and t.dauer_min else 0 for t in termine if not t.abgesagt])
        # Gruppentermine
        gruppentermine = Gruppentermin.query.filter(extract('year', Gruppentermin.datum) == jahr).all()
        gruppen_abgehalten = len([g for g in gruppentermine if not g.entfallen])
        gruppen_abgesagt = len([g for g in gruppentermine if g.entfallen])
        gruppen_minuten = sum([int(g.dauer_min) if hasattr(g, 'dauer_min') and g.dauer_min else 0 for g in gruppentermine if not g.entfallen])
        result.append({
            'jahr': jahr,
            'einnahmen_gesamt': float(einnahmen_gesamt),
            'einnahmen_umsatzsteuerpflichtig': float(einnahmen_umsatz),
            'einnahmen_nicht_umsatzsteuerpflichtig': float(einnahmen_nicht_umsatz),
            'abgehaltene_termine': abgehalten,
            'abgehaltene_termine_min': minuten,
            'abgesagte_termine': abgesagt,
            'abgehaltene_gruppentermine': gruppen_abgehalten,
            'abgehaltene_gruppentermine_min': gruppen_minuten,
            'abgesagte_gruppentermine': gruppen_abgesagt
        })
    return jsonify(result)

@auswertung_bp.route("/api/auswertung/kunden", methods=["GET"])
def auswertung_kunden():
    jahr = request.args.get("jahr", type=int)
    kunden = Kunde.query.all()
    result = []
    for k in kunden:
        # Einnahmen für diesen Kunden im Jahr
        rechnungen = Rechnung.query.filter(Rechnung.kunde_id == k.id)
        if jahr:
            rechnungen = rechnungen.filter(extract('year', Rechnung.datum) == jahr)
        einnahmen_gesamt = sum([r.betrag for r in rechnungen])
        einnahmen_umsatz = sum([r.betrag for r in rechnungen if r.umsatzsteuerpflichtig])
        einnahmen_nicht_umsatz = sum([r.betrag for r in rechnungen if not r.umsatzsteuerpflichtig])
        termine = Termin.query.filter(Termin.kunde_id == k.id)
        if jahr:
            termine = termine.filter(extract('year', Termin.datum) == jahr)
        termine = list(termine)
        abgehalten = len([t for t in termine if not t.abgesagt])
        abgesagt = len([t for t in termine if t.abgesagt])
        minuten = sum([int(t.dauer_min) if hasattr(t, 'dauer_min') and t.dauer_min else 0 for t in termine if not t.abgesagt])
        result.append({
            'kuerzel': k.kuerzel,
            'einnahmen_gesamt': float(einnahmen_gesamt),
            'einnahmen_umsatzsteuerpflichtig': float(einnahmen_umsatz),
            'einnahmen_nicht_umsatzsteuerpflichtig': float(einnahmen_nicht_umsatz),
            'abgehaltene_termine': abgehalten,
            'abgehaltene_termine_min': minuten,
            'abgesagte_termine': abgesagt
        })
    return jsonify(result)
