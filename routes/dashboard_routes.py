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
    for r in all_unpaid:
        if r.zahlungsziel_tage:
            due_date = date.fromisoformat(r.datum) + timedelta(days=r.zahlungsziel_tage)
            if due_date < today:
                overdue_rechnungen.append(r)
    # Sortiere nach Datum
    overdue_rechnungen.sort(key=lambda x: x.datum)
    
    # 2. Überfällige Mahnungen
    all_mahnungen = Mahnung.query.all()
    overdue_mahnungen = []
    for m in all_mahnungen:
        if m.zahlungsziel_tage:
            due_date = date.fromisoformat(m.datum) + timedelta(days=m.zahlungsziel_tage)
            if due_date < today:
                overdue_mahnungen.append(m)
    # Sortiere nach Datum absteigend und nimm die letzten 10
    overdue_mahnungen.sort(key=lambda x: x.datum, reverse=True)
    mahnungen = overdue_mahnungen[:10]
    
    # 3. Termine heute und morgen
    termine_heute = Termin.query.filter(Termin.datum == today.isoformat(), (Termin.abgesagt == None) | (Termin.abgesagt == "") ).order_by(Termin.startzeit).all()
    termine_morgen = Termin.query.filter(Termin.datum == tomorrow.isoformat(), (Termin.abgesagt == None) | (Termin.abgesagt == "") ).order_by(Termin.startzeit).all()
    
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
    all_termine = Termin.query.filter(Termin.datum >= today.isoformat()).order_by(Termin.datum, Termin.startzeit).all()
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