
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
        from datetime import datetime
        def calc_min(start, end):
            try:
                if start and end and isinstance(start, str) and isinstance(end, str):
                    # Versuche verschiedene Formate (mit/ohne Sekunden, mit/ohne Z)
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
                        try:
                            s = datetime.strptime(start, fmt)
                            e = datetime.strptime(end, fmt)
                            return int((e-s).total_seconds()//60)
                        except Exception:
                            continue
            except Exception as ex:
                print(f"Fehler bei Zeitberechnung: {start} - {end}: {ex}")
            return 0

        termine = Termin.query.filter(extract('year', Termin.datum) == jahr).all()
        abgehalten = len([t for t in termine if not t.abgesagt])
        abgesagt = len([t for t in termine if t.abgesagt])
        minuten = sum([calc_min(t.utc_starttime, t.utc_endtime) for t in termine if not t.abgesagt])
        # Gruppentermine
        gruppentermine = Gruppentermin.query.filter(extract('year', Gruppentermin.datum) == jahr).all()
        gruppen_abgehalten = len([g for g in gruppentermine if not g.entfallen])
        gruppen_abgesagt = len([g for g in gruppentermine if g.entfallen])
        gruppen_minuten = sum([calc_min(g.utc_starttime, g.utc_endtime) for g in gruppentermine if not g.entfallen])
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
        # Einnahmen für diesen Kunden im Jahr: alle Rechnungen, die über einen Termin mit diesem Kunden verknüpft sind
        rechnungen = []
        for r in Rechnung.query.all():
            for tr in r.termine_rechnungen:
                if tr.termin and tr.termin.kunde_id == k.id:
                    if not jahr or (r.datum and r.datum.startswith(str(jahr))):
                        rechnungen.append(r)
                        break
        einnahmen_gesamt = sum([r.betrag for r in rechnungen])
        einnahmen_umsatz = sum([r.betrag for r in rechnungen if k.ust == 1])
        einnahmen_nicht_umsatz = sum([r.betrag for r in rechnungen if k.ust != 1])
        from datetime import datetime
        def calc_min(start, end):
            try:
                if start and end and isinstance(start, str) and isinstance(end, str):
                    print(f"Berechnung Minuten: Start {start} - End {end}")
                    for fmt in ("%Y-%m-%dT%H:%M:%S",  "%H:%M","%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
                        try:
                            s = datetime.strptime(start, fmt)
                            e = datetime.strptime(end, fmt)
                            print(f"Berechnung11 Minuten: Start {s} - End {e} => {(e-s).total_seconds()//60} Minuten")
                            return int((e-s).total_seconds()//60)
                        except Exception:
                            continue
            except Exception as ex:
                print(f"Fehler bei Zeitberechnung: {start} - {end}: {ex}")
            return 0

        termine = Termin.query.filter(Termin.kunde_id == k.id)
        if jahr:
            termine = termine.filter(extract('year', Termin.datum) == jahr)
        termine = list(termine)
        abgehalten = len([t for t in termine if not t.abgesagt])
        abgesagt = len([t for t in termine if t.abgesagt])
        print("Zeiten Kunde", k.kuerzel, [(t.utc_starttime, t.utc_endtime) for t in termine])
        minuten = sum([calc_min(t.utc_starttime, t.utc_endtime) for t in termine if not t.abgesagt])
        stunden = minuten / 60
        if einnahmen_gesamt > 0:
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

@auswertung_bp.route("/api/auswertung/gruppen", methods=["GET"])
def auswertung_gruppen():
    jahr = request.args.get("jahr", type=int)
    gruppen = Gruppe.query.all()
    result = []
    for g in gruppen:
        # Einnahmen für diese Gruppe im Jahr: alle Rechnungen, die über einen Termin mit einem Gruppentermin dieser Gruppe verknüpft sind
        rechnungen = []
        for r in Rechnung.query.all():
            for tr in r.termine_rechnungen:
                if tr.termin and tr.termin.gruppentermin_id:
                    gruppentermin = Gruppentermin.query.get(tr.termin.gruppentermin_id)
                    if gruppentermin and gruppentermin.gruppe_id == g.id:
                        if not jahr or (r.datum and r.datum.startswith(str(jahr))):
                            rechnungen.append(r)
                            break
        einnahmen_gesamt = sum([r.betrag for r in rechnungen])
        # USt-pflichtig: analog zu Kunden, aber auf Gruppenebene meist nicht relevant, daher 0
        einnahmen_umsatz = 0
        einnahmen_nicht_umsatz = einnahmen_gesamt
        from datetime import datetime
        def calc_min(start, end):
            try:
                if start and end and isinstance(start, str) and isinstance(end, str):
                    for fmt in ("%Y-%m-%dT%H:%M:%S", "%H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
                        try:
                            s = datetime.strptime(start, fmt)
                            e = datetime.strptime(end, fmt)
                            return int((e-s).total_seconds()//60)
                        except Exception:
                            continue
            except Exception as ex:
                print(f"Fehler bei Zeitberechnung: {start} - {end}: {ex}")
            return 0

        termine = Gruppentermin.query.filter(Gruppentermin.gruppe_id == g.id)
        if jahr:
            termine = termine.filter(extract('year', Gruppentermin.datum) == jahr)
        termine = list(termine)
        abgehalten = len([t for t in termine if not t.entfallen])
        abgesagt = len([t for t in termine if t.entfallen])
        minuten = sum([calc_min(t.utc_starttime, t.utc_endtime) for t in termine if not t.entfallen])
        if einnahmen_gesamt > 0 or abgehalten > 0 or abgesagt > 0:
            result.append({
                'kuerzel': g.gruppenkuerzel,
                'einnahmen_gesamt': float(einnahmen_gesamt),
                'einnahmen_umsatzsteuerpflichtig': float(einnahmen_umsatz),
                'einnahmen_nicht_umsatzsteuerpflichtig': float(einnahmen_nicht_umsatz),
                'abgehaltene_termine': abgehalten,
                'abgehaltene_termine_min': minuten,
                'abgesagte_termine': abgesagt
            })
    return jsonify(result)
