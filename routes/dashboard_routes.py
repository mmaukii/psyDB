from flask import Blueprint, render_template
from datetime import date, timedelta
from models import Rechnung, Mahnung, Termin, Kunde

def time_to_minutes(time_str):
    """Konvertiert HH:MM in Minuten seit Mitternacht"""
    if not time_str or ":" not in time_str:
        return 0
    h, m = time_str.split(":")
    return int(h) * 60 + int(m)

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.get("/")
def dashboard():
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # 1. Unbezahlte Rechnungen, die überfällig sind (Fälligkeitsdatum überschritten)
    all_unpaid = Rechnung.query.filter(Rechnung.bezahlt == 0).all()
    overdue_rechnungen = []
    from models.termine_rechnungen import TermineRechnung
    from models.termine import Termin
    for r in all_unpaid:
        if r.zahlungsziel_tage:
            due_date = date.fromisoformat(r.datum) + timedelta(days=r.zahlungsziel_tage)
            if due_date < today:
                days_overdue = (today - due_date).days
                setattr(r, 'days_overdue', days_overdue)
                # Kundenkürzel über zugehörige Termine ermitteln
                tr = TermineRechnung.query.filter_by(rechnung_id=r.id).first()
                kuerzel = ""
                if tr:
                    termin = Termin.query.get(tr.termin_id)
                    if termin and termin.kunde:
                        kuerzel = termin.kunde.kuerzel
                setattr(r, 'kuerzel', kuerzel)
                overdue_rechnungen.append(r)
    # Sortiere nach Datum
    overdue_rechnungen.sort(key=lambda x: x.datum)
    
    # 2. Überfällige Mahnungen
    from models.termine_rechnungen import TermineRechnung
    from models.termine import Termin
    overdue_mahnungen = []
    all_mahnungen = Mahnung.query.all()
    for m in all_mahnungen:
        if m.zahlungsziel_tage:
            due_date = date.fromisoformat(m.datum) + timedelta(days=m.zahlungsziel_tage)
            if due_date < today:
                # Kürzel ermitteln
                kuerzel = ""
                termin = None
                if m.rechnung:
                    tr = TermineRechnung.query.filter_by(rechnung_id=m.rechnung.id).first()
                    if tr:
                        termin = Termin.query.get(tr.termin_id)
                if termin and termin.kunde:
                    kuerzel = termin.kunde.kuerzel
                setattr(m, 'kuerzel', kuerzel)
                # Fälligkeitsdauer berechnen
                days_overdue = (today - due_date).days
                setattr(m, 'days_overdue', days_overdue)
                overdue_mahnungen.append(m)
    # Sortiere nach Datum absteigend und nimm die letzten 10
    overdue_mahnungen.sort(key=lambda x: x.datum, reverse=True)
    mahnungen = overdue_mahnungen[:10]
    
    # 3. Termine heute und morgen (inkl. Gruppentermine)
    from models.gruppentermine import Gruppentermin
    termine_heute = Termin.query.filter(Termin.datum == today.isoformat(), (Termin.abgesagt == None) | (Termin.abgesagt == "") ).order_by(Termin.startzeit).all()
    gruppentermine_heute = Gruppentermin.query.filter(
        Gruppentermin.datum == today.isoformat(),
        (Gruppentermin.entfallen == None) | (Gruppentermin.entfallen == ""),
        Gruppentermin.nur_offline_geloescht == 0
    ).order_by(Gruppentermin.startzeit).all()
    termine_heute = sorted(list(termine_heute) + list(gruppentermine_heute), key=lambda t: t.startzeit)

    termine_morgen = Termin.query.filter(Termin.datum == tomorrow.isoformat(), (Termin.abgesagt == None) | (Termin.abgesagt == "") ).order_by(Termin.startzeit).all()
    gruppentermine_morgen = Gruppentermin.query.filter(
        Gruppentermin.datum == tomorrow.isoformat(),
        (Gruppentermin.entfallen == None) | (Gruppentermin.entfallen == ""),
        Gruppentermin.nur_offline_geloescht == 0
    ).order_by(Gruppentermin.startzeit).all()
    termine_morgen = sorted(list(termine_morgen) + list(gruppentermine_morgen), key=lambda t: t.startzeit)
    
    # 4. Prüfung Rechnungsnummern durchgängig
    all_rechnungen = Rechnung.query.order_by(Rechnung.rechnungsnr).all()
    rechnungsnrs = [r.rechnungsnr for r in all_rechnungen]
    missing_numbers = []
    if rechnungsnrs:
        min_nr = min(rechnungsnrs)
        max_nr = max(rechnungsnrs)
        expected = set(range(min_nr, max_nr + 1))
        actual = set(rechnungsnrs)
        missing_numbers = sorted(expected - actual)
    
    # 5. Überschneidende Termine
    overlapping_termine = []
    all_termine = list(Termin.query.filter(Termin.datum >= today.isoformat()).order_by(Termin.datum, Termin.startzeit).all())
    gruppentermine_ab_heute = list(Gruppentermin.query.filter(
        Gruppentermin.datum >= today.isoformat(),
        (Gruppentermin.entfallen == None) | (Gruppentermin.entfallen == ""),
        Gruppentermin.nur_offline_geloescht == 0
    ).order_by(Gruppentermin.datum, Gruppentermin.startzeit).all())
    all_termine += gruppentermine_ab_heute
    all_termine.sort(key=lambda t: (t.datum, t.startzeit))
    grouped_by_date = {}
    for t in all_termine:
        if t.datum not in grouped_by_date:
            grouped_by_date[t.datum] = []
        grouped_by_date[t.datum].append(t)
    
    for datum, termine in grouped_by_date.items():
        termine.sort(key=lambda x: time_to_minutes(x.startzeit))
        for i in range(len(termine) - 1):
            current = termine[i]
            next_t = termine[i+1]
            if time_to_minutes(current.endzeit) > time_to_minutes(next_t.startzeit):
                overlapping_termine.append((current, next_t))
    
    # Letzte Kalender-Synchronisierung
    from models.programmvariablen import Programmvariable
    from datetime import datetime
    letzte_kalender_sync = None
    letzte_kalender_sync_diff = None
    pv = Programmvariable.query.filter_by(name="letzte_kalender_sync").first()
    if pv and pv.wert:
        letzte_kalender_sync = pv.wert
        try:
            last_sync_dt = datetime.fromisoformat(letzte_kalender_sync)
            now = datetime.now()
            delta = now - last_sync_dt
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            letzte_kalender_sync_diff = ""
            if days > 0:
                letzte_kalender_sync_diff += f"{days} d "
            if hours > 0 or days > 0:
                letzte_kalender_sync_diff += f"{hours} h "
            letzte_kalender_sync_diff += f"{minutes} min"
        except Exception:
            letzte_kalender_sync_diff = None

    return render_template("dashboard.html",
                          overdue_rechnungen=overdue_rechnungen,
                          mahnungen=mahnungen,
                          termine_heute=termine_heute,
                          termine_morgen=termine_morgen,
                          missing_numbers=missing_numbers,
                          overlapping_termine=overlapping_termine,
                          letzte_kalender_sync=letzte_kalender_sync,
                          letzte_kalender_sync_diff=letzte_kalender_sync_diff)