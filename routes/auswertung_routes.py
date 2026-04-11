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
            # Umsatzsteuerpflichtig jetzt über alle zugeordneten termine_rechnungen prüfen
            ust_anteil = 0.0
            nicht_ust_anteil = 0.0
            if r.termine_rechnungen:
                for tr in r.termine_rechnungen:
                    if tr.termin and hasattr(tr.termin, 'betrag') and tr.termin.betrag is not None:
                        betrag = tr.termin.betrag
                    else:
                        betrag = 0.0
                    if tr.termin and hasattr(tr.termin, 'ust') and tr.termin.ust == 1:
                        ust_anteil += betrag
                    else:
                        nicht_ust_anteil += betrag
            else:
                nicht_ust_anteil += r.betrag
            einnahmen_umsatz += ust_anteil
            einnahmen_nicht_umsatz += nicht_ust_anteil
        # Einzeltermine
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

        termine = Termin.query.filter(extract('year', Termin.datum) == jahr).all()
        # Nur Termine, die einer Rechnung und termine_rechnungen zugeordnet sind
        termine_ids_mit_rechnung = set()
        for r in rechnungen:
            for tr in r.termine_rechnungen:
                if tr.termin_id:
                    termine_ids_mit_rechnung.add(tr.termin_id)
        abgehalten = len([t for t in termine if not t.abgesagt and t.id in termine_ids_mit_rechnung])
        abgesagt = len([t for t in termine if t.abgesagt])
        minuten = sum([calc_min(t.startzeit, t.endzeit) for t in termine if not t.abgesagt and t.id in termine_ids_mit_rechnung])
        # Gruppentermine
        gruppentermine = Gruppentermin.query.filter(extract('year', Gruppentermin.datum) == jahr).all()
        # Nur Gruppentermine, die in mindestens einem Termin als gruppentermin_id referenziert werden
        gruppentermin_ids_in_termine = set([t.gruppentermin_id for t in Termin.query.filter(Termin.gruppentermin_id.isnot(None)).all()])
        gruppen_abgehalten = len([g for g in gruppentermine if not g.entfallen and g.id in gruppentermin_ids_in_termine])
        gruppen_abgesagt = len([g for g in gruppentermine if g.entfallen])
        gruppen_minuten = sum([calc_min(g.startzeit, g.endzeit) for g in gruppentermine if not g.entfallen and g.id in gruppentermin_ids_in_termine])
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
        # Umsatzsteuerpflichtig jetzt über termine_rechnungen prüfen
        einnahmen_umsatz = 0.0
        einnahmen_nicht_umsatz = 0.0
        for r in rechnungen:
            if r.termine_rechnungen:
                for tr in r.termine_rechnungen:
                    if tr.termin and hasattr(tr.termin, 'betrag') and tr.termin.betrag is not None:
                        betrag = tr.termin.betrag
                    else:
                        betrag = 0.0
                    if tr.termin and hasattr(tr.termin, 'ust') and tr.termin.ust == 1:
                        einnahmen_umsatz += betrag
                    else:
                        einnahmen_nicht_umsatz += betrag
            else:
                einnahmen_nicht_umsatz += r.betrag
        from datetime import datetime
        def calc_min(start, end):
            try:
                if start and end and isinstance(start, str) and isinstance(end, str):
                    #print(f"Berechnung Minuten: Start {start} - End {end}")
                    for fmt in ("%Y-%m-%dT%H:%M:%S",  "%H:%M","%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
                        try:
                            s = datetime.strptime(start, fmt)
                            e = datetime.strptime(end, fmt)
                            #print(f"Berechnung11 Minuten: Start {s} - End {e} => {(e-s).total_seconds()//60} Minuten")
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
        #print("Zeiten Kunde", k.kuerzel, [(t.startzeit, t.endzeit) for t in termine])
        minuten = sum([calc_min(t.startzeit, t.endzeit) for t in termine if not t.abgesagt])
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
        # Einnahmen für diese Gruppe: alle Termine mit gruppentermin_id, die zu dieser Gruppe gehören und in einer Rechnung vorkommen
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

        # Alle Gruppentermine dieser Gruppe im Jahr
        gruppentermine = Gruppentermin.query.filter(Gruppentermin.gruppe_id == g.id)
        if jahr:
            gruppentermine = gruppentermine.filter(extract('year', Gruppentermin.datum) == jahr)
        gruppentermine = list(gruppentermine)
        gruppentermin_ids = [gt.id for gt in gruppentermine]

        # Alle Termine mit gruppentermin_id dieser Gruppe
        termine = Termin.query.filter(Termin.gruppentermin_id.in_(gruppentermin_ids)).all() if gruppentermin_ids else []

        # Einnahmen: nur Termine, die in einer Rechnung vorkommen
        termin_ids = [t.id for t in termine]
        einnahmen_umsatz = 0.0
        einnahmen_nicht_umsatz = 0.0
        if termin_ids:
            for r in Rechnung.query.all():
                for tr in r.termine_rechnungen:
                    if tr.termin_id in termin_ids:
                        if not jahr or (r.datum and r.datum.startswith(str(jahr))):
                            if tr.termin and hasattr(tr.termin, 'betrag') and tr.termin.betrag is not None:
                                betrag = tr.termin.betrag
                            else:
                                betrag = 0.0
                            if tr.termin and hasattr(tr.termin, 'ust') and tr.termin.ust == 1:
                                einnahmen_umsatz += betrag
                            else:
                                einnahmen_nicht_umsatz += betrag
        einnahmen_gesamt = einnahmen_umsatz + einnahmen_nicht_umsatz

        abgehalten = len([gt for gt in gruppentermine if not gt.entfallen])
        abgesagt = len([gt for gt in gruppentermine if gt.entfallen])
        minuten = sum([calc_min(gt.startzeit, gt.endzeit) for gt in gruppentermine if not gt.entfallen])
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

@auswertung_bp.route("/api/auswertung/therapieformen", methods=["GET"])
def auswertung_therapieformen():
    jahr = request.args.get("jahr", type=int)
    # Mapping für Anzeige
    therapieform_map = {
        1: "Einzeltherapie",
        2: "Paartherapie",
        3: "Familientherapie",
        4: "Gruppentherapie",
        5: "Einzelsupervision",
        6: "Gruppensupervision",
        7: "Einzelselbsterfahrung",
        8: "Gruppenselbsterfahrung",
        9: "Coaching",
        10: "Vortrag/Seminar/Workshop"
    }
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

    # Alle Termine im Jahr, gruppiert nach therapieform
    query = Termin.query
    if jahr:
        query = query.filter(extract('year', Termin.datum) == jahr)
    termine = query.all()
    therapieform_dict = {}
    for t in termine:
        tf = t.therapieform or 0
        if tf not in therapieform_dict:
            therapieform_dict[tf] = {
                'therapieform': tf,
                'therapieform_bezeichnung': therapieform_map.get(tf, str(tf)),
                'einnahmen_gesamt': 0.0,
                'einnahmen_umsatzsteuerpflichtig': 0.0,
                'einnahmen_nicht_umsatzsteuerpflichtig': 0.0,
                'abgehaltene_termine': 0,
                'abgehaltene_termine_min': 0,
                'abgesagte_termine': 0
            }
        # Nur Termine, die einer Rechnung zugeordnet sind, zählen
        # Einnahmen für diesen Termin im Jahr: t.betrag, wenn eine zugeordnete Rechnung im Jahr existiert
        hat_rechnung = any(
            tr.rechnung and (not jahr or (tr.rechnung.datum and tr.rechnung.datum.startswith(str(jahr))))
            for tr in t.termine_rechnungen
        )
        if hat_rechnung and not t.abgesagt:
            therapieform_dict[tf]['abgehaltene_termine'] += 1
            therapieform_dict[tf]['abgehaltene_termine_min'] += calc_min(t.startzeit, t.endzeit)
            therapieform_dict[tf]['einnahmen_gesamt'] += t.betrag or 0.0
            # USt-pflichtig: jetzt über alle termine_rechnungen prüfen
            ust_anteil = 0.0
            nicht_ust_anteil = 0.0
            if t.termine_rechnungen:
                for tr in t.termine_rechnungen:
                    if tr.termin and hasattr(tr.termin, 'betrag') and tr.termin.betrag is not None:
                        betrag = tr.termin.betrag
                    else:
                        betrag = 0.0
                    if tr.termin and hasattr(tr.termin, 'ust') and tr.termin.ust == 1:
                        ust_anteil += betrag
                    else:
                        nicht_ust_anteil += betrag
            else:
                nicht_ust_anteil += t.betrag or 0.0
            therapieform_dict[tf]['einnahmen_umsatzsteuerpflichtig'] += ust_anteil
            therapieform_dict[tf]['einnahmen_nicht_umsatzsteuerpflichtig'] += nicht_ust_anteil
        elif t.abgesagt:
            therapieform_dict[tf]['abgesagte_termine'] += 1
    # Ausgabe als Liste, aber nur Therapieformen mit echten Werten
    result = [x for x in therapieform_dict.values() if (
        x['einnahmen_gesamt'] > 0 or x['abgehaltene_termine'] > 0 or x['abgehaltene_termine_min'] > 0 or x['abgesagte_termine'] > 0
    )]
    # Nach Einnahmen sortieren (optional)
    result.sort(key=lambda x: x['einnahmen_gesamt'], reverse=True)
    return jsonify(result)
