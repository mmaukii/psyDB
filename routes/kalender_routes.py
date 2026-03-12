from flask import Blueprint, request, jsonify
from database import db
from models import Termin, Gruppentermin, Kunde, Gruppe,Programmvariable
from sqlalchemy import union_all, literal
from caldav import DAVClient
from caldav.elements import dav
from datetime import datetime, timedelta
import time
from config import get_webdav_config
from sqlalchemy import text



kalender_bp = Blueprint("kalender", __name__)

# --- termine mit aktivem Kunden, nicht abgesagt und nicht in Rechnung ---
@kalender_bp.get("/kalender/termine_anzuzeigen")
def get_kalender_termine_anzuzueigen():

    # Einzeltermine (kundenbezogen)
    termine = (
        db.session.query(
            Termin.id,
            Termin.datum,
            Termin.startzeit,
            Termin.endzeit,
            Termin.betrag,
            Termin.beschreibung,
            Termin.kunde_id,
            Termin.gruppentermin_id,
            Kunde.kuerzel.label("kunde_kuerzel")
        )
        .join(Kunde, Termin.kunde_id == Kunde.id)
        .filter(((Termin.abgesagt == 0) | (Termin.abgesagt.is_(None))) & (Termin.gruppentermin_id.is_(None)))
        .all()
    )

    # Gruppentermine
    gruppen = (
        db.session.query(
            Gruppentermin.id,
            Gruppentermin.datum,
            Gruppentermin.startzeit,
            Gruppentermin.endzeit,
            Gruppentermin.betrag,
            Gruppentermin.beschreibung,
            Gruppentermin.gruppe_id,
            Gruppe.gruppenkuerzel
        )
        .join(Gruppe, Gruppentermin.gruppe_id == Gruppe.id)
        .filter((Gruppentermin.entfallen == 0) | (Gruppentermin.entfallen.is_(None)))
        .all()
    )

    # Beide Listen zusammenführen
    result = [
        {
            "id": r.id,
            "datum": r.datum,
            "startzeit": r.startzeit,
            "endzeit": r.endzeit,
            "betrag": r.betrag,
            "kunde_id": getattr(r, "kunde_id", None),
            "kunde_kuerzel": getattr(r, "kunde_kuerzel", None),
            "gruppe_id": getattr(r, "gruppe_id", None),
            "gruppen_kuerzel": getattr(r, "gruppenkuerzel", None)
        }
        for r in termine + gruppen
    ]

    return jsonify(result)

# --- Externe Kalenderdaten via WebDAV / CalDAV abrufen ---

caldav_bp = Blueprint("caldav", __name__)

@kalender_bp.route("/kalender/extern")
def kalender_extern():
    config = get_webdav_config()
    client = DAVClient(
        url=config['url'],
        username=config['user'],
        password=config['password']
    )

    principal = client.principal()
    calendars = principal.calendars()

    events_json = []

    # Zeitraum: letzter Monat bis +3 Monate

    andere_kalender_var = Programmvariable.query.filter_by(name='andere_kalender').first()
    andere_kalender_namen = (andere_kalender_var.wert or "").lower()
    terminkalender_var = Programmvariable.query.filter_by(name='termine_kalender').first()
    terminkalender_name =terminkalender_var.wert
    kunden_kuerzel_low = {k.kuerzel.lower() for k in Kunde.query.all()}
    gruppen_kuerzel_low = {g.gruppenkuerzel.lower() for g in Gruppe.query.all()}

    # String → Liste machen
    erlaubte_kalender = [name.strip() for name in andere_kalender_namen.split(";") if name.strip()]+[terminkalender_name.lower()]
    print("Erlaubte Kalender für Extern: " + ", ".join(erlaubte_kalender))
    for cal in calendars:
        cal_name = (cal.name or "").lower()
        # ❗ Nur weitermachen, wenn im andere_kalender enthalten
        if cal_name not in erlaubte_kalender:
            continue
        print("Daten holen von Kalender:" + cal_name)
        

        try:
            # 1️⃣ Events für diesen Kalender
            events = cal.events()
        except Exception as e:
            print(f"Kalender-Fehler: {cal_name} → {e}")
            continue
        

        # 2️⃣ Alle Events des Kalenders verarbeiten
        kalender_events = []
        for ev in events:
            try:
                vevent = ev.vobject_instance.vevent
            except Exception as e:
                print(f"VEVENT-Parsing-Fehler ({cal_name}): {e}")
                continue

            uid = vevent.uid.value
            title = getattr(vevent, "summary", None)
            title = title.value if title else "📅 Externer Termin"



            # ❗ Prüfen, ob Titel exakt Kunde-Kürzel oder Terminkalender ist
            if (title.lower() in kunden_kuerzel_low or title.lower() in gruppen_kuerzel_low) and cal_name == terminkalender_name.lower():
                # print(f"Event übersprungen (Titel im Kürzel oder Terminkalender): {title}")
                continue

            dtstart = vevent.dtstart.value
            dtend = getattr(vevent, "dtend", None)
            dtend = dtend.value if dtend else None

            # Ausgabe für alle Events (online) - jetzt nach Initialisierung von dtstart
            #print(f"[ONLINE] UID={uid}, Summary='{title}', Start={dtstart}, Calendar={cal_name}")

            # DATE → DATETIME
            if not hasattr(dtstart, "hour"):
                dtstart = datetime.combine(dtstart, datetime.min.time())
            if dtend and not hasattr(dtend, "hour"):
                dtend = datetime.combine(dtend, datetime.min.time())

            # ⏰ Prüfen auf Serientermine (RRULE direkt auslesen)
            has_rrule = hasattr(vevent, 'rrule') and vevent.rrule is not None
            #print(f"Event: {title}, UID: {uid}, hasRRULE: {has_rrule}")
            #print(f"  Attributes: {[str(x) for x in vevent.contents.keys()]}")
            #print(vevent)
            
            if has_rrule:
                # Serientermin → in Einzeltermine expandieren
                #print(f"📅 Serientermin erkannt: {title} (UID: {uid})")
                
                try:
                    rruleset = vevent.getrruleset()
                    if not rruleset:
                        rruleset = vevent.rrule.value if hasattr(vevent.rrule, 'value') else []
                    
                    duration = dtend - dtstart if dtend else timedelta(hours=1)

                    for occurrence_start in rruleset:
                        # Occurrence timezone-naive machen für Vergleich
                        if occurrence_start.tzinfo:
                            occurrence_start = occurrence_start.replace(tzinfo=None)
                        
                        occurrence_end = occurrence_start + duration

                        kalender_events.append({
                            "uid": f"{uid}-{occurrence_start.isoformat()}",
                            "title": title,
                            "start": occurrence_start.isoformat(),
                            "end": occurrence_end.isoformat() if occurrence_end else None,
                            "calendar": cal_name,
                            "is_recurring": True,
                            "parent_uid": uid
                        })
                except Exception as rrule_error:
                    print(f"⚠ Fehler beim Expandieren der RRULE: {rrule_error}")
                    # Fallback: als Einzeltermin hinzufügen
                    kalender_events.append({
                        "uid": uid,
                        "title": title,
                        "start": dtstart.isoformat(),
                        "end": dtend.isoformat() if dtend else None,
                        "calendar": cal_name
                    })
            else:
                # Einzeltermin
                kalender_events.append({
                    "uid": uid,
                    "title": title,
                    "start": dtstart.isoformat(),
                    "end": dtend.isoformat() if dtend else None,
                    "calendar": cal_name
                })


        # 3️⃣ Alle Kalender-Events anhängen
        events_json.extend(kalender_events)

    return jsonify(events_json)

# -- für synchronisierung Pusch und pull des Kalenders ---
def get_termin_calendar():
    config = get_webdav_config()
    client = DAVClient(
        url=config['url'],
        username=config['user'],
        password=config['password']
    )

    terminkalender_var = Programmvariable.query.filter_by(name='termine_kalender').first()
    terminkalender_name =terminkalender_var.wert
    principal = client.principal()
    for cal in principal.calendars():
        if cal.name.lower() == terminkalender_name.lower():
            print(cal.name)
            print (terminkalender_name + " zum synchronisieren geladen")
            return cal

    raise Exception("Kalender '"+terminkalender_name+"' nicht gefunden")

# services/sync_termine_push.py
def push_termin(termin: dict, delete_from_db=False):
    """
    Push einer Termin zu CalDAV.
    - Nur wenn Kürzel einem Kunden oder Gruppe entspricht
    - Abgesagte/entfallene Events werden online gelöscht
    - Optional aus DB löschen
    """
    kunden = Kunde.query.all()
    gruppen = Gruppe.query.all()
    kunden_kuerzel = {k.kuerzel for k in kunden}
    gruppen_kuerzel = {g.gruppenkuerzel for g in gruppen}
    valid_kuerzel = kunden_kuerzel | gruppen_kuerzel
    kunden_by_kuerzel = {k.kuerzel: k for k in kunden}
    gruppen_by_kuerzel = {g.gruppenkuerzel: g for g in gruppen}
    print("Push Termin: " + termin.get("kuerzel", "") + ", ID: " + str(termin.get("termin_id") or termin.get("gruppentermin_id"))   )
 
    title = termin.get("kuerzel", "")
    if title not in valid_kuerzel:
        #print(f"⚠ Ignoriere Push für ungültiges Kürzel: {title}")
        return

    cal = get_termin_calendar()
    is_gruppe = bool(termin.get("gruppentermin_id"))
    id = termin.get("gruppentermin_id") if is_gruppe else termin.get("termin_id")
    table = "gruppentermine" if is_gruppe else "termine"

    uid = termin.get("caldav_uid") or f"{'grtermin' if is_gruppe else 'termin'}-{id}@probe"

    # Prüfen ob Timestamp für abgesagt/entfallen gesetzt
    is_abgesagt = termin.get("abgesagt_am") or termin.get("entfallen_am")
    try:
        if is_abgesagt:
            # Event online löschen
            try:
                event = cal.event_by_uid(uid)
                event.delete()
                print(f"🗑 Event online gelöscht: UID={uid}")
            except Exception as e:
                print(f"⚠ Event UID={uid} nicht gefunden online (vielleicht schon gelöscht)")

            # Optional: aus DB löschen
            if delete_from_db:
                try:
                    termin_obj = None
                    if is_gruppe:
                        termin_obj = Gruppentermin.query.get(termin.get("gruppentermin_id"))
                    else:
                        termin_obj = Termin.query.get(termin.get("termin_id"))
                    if termin_obj:
                        db.session.delete(termin_obj)
                        db.session.commit()
                        print(f"→ Event aus DB gelöscht: UID={uid}")
                except Exception as e:
                    print(f"⚠ Fehler beim Löschen aus DB: {e}")
            return  # Fertig, kein weiteres Update nötig

        # Wenn nicht abgesagt → normales Push/Update
        dtstart = datetime.fromisoformat(f"{termin['datum']}T{termin.get('startzeit') or '00:00'}")
        dtend   = datetime.fromisoformat(f"{termin['datum']}T{termin.get('endzeit') or '00:00'}")
        terminkalender_var = Programmvariable.query.filter_by(name='termine_kalender').first()
        terminkalender_name =terminkalender_var.wert
        vevent = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//{terminkalender_name}//termine Sync//DE
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}
DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{title}
DESCRIPTION:{termin.get('beschreibung') or ''}
LAST-MODIFIED:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}
END:VEVENT
END:VCALENDAR
"""
        if termin.get("caldav_uid"):
            # Update
            event = cal.event_by_uid(uid)
            event.data = vevent
            event.save()
            etag = get_event_etag(event)
            db.session.execute(
                text(f"UPDATE {table} SET caldav_etag=:etag WHERE id=:id"),
                {"etag": etag, "id": id}
            )
            db.session.commit()
        else:
            # Neues Event anlegen
            event = cal.add_event(vevent, content_type="text/calendar; charset=utf-8")
            event.load()
            uid = event.vobject_instance.vevent.uid.value
            etag = get_event_etag(event)
            db.session.execute(
                text(f"UPDATE {table} SET caldav_uid=:uid, caldav_etag=:etag WHERE id=:id"),
                {"uid": uid, "etag": etag, "id": id}
            )
            db.session.commit()

    except Exception as e:
        print(f"⚠ Fehler beim push_termin: {e}")



#--- Route zum löschen von terminen in webdav von Datenbank aus ---
@kalender_bp.delete("/kalender/webcal/<string:typ>/<int:id>")
def delete_webcal_event(typ, id):
    if typ == "termin":
        termin = Termin.query.get_or_404(id)
    elif typ == "gruppentermin":
        termin = Gruppentermin.query.get_or_404(id)
    else:
        return jsonify({"error": "Typ muss 'termin' oder 'gruppentermin' sein"}), 400
    
    if not termin:
     return jsonify({"error": "Termin existiert nicht mehr in DB"}), 404

    if not termin.caldav_uid:
        return jsonify({"error": "Kein WebCal-Event verknüpft"}), 400

    cal = get_termin_calendar()
    uid = termin.caldav_uid
    print ("termin wird gelöscht")

    # 1️⃣ Löschen im WebDAV-Kalender versuchen
    deleted_from_caldav = False
    try:
        event = cal.event_by_uid(uid)
        event.delete()
        deleted_from_caldav = True
        print(f"✅ Event {uid} aus WebDAV gelöscht")
    except Exception as e:
        # Event existiert möglicherweise nicht mehr im WebDAV - das ist OK
        print(f"⚠️ Event {uid} nicht im WebDAV gefunden (oder Fehler beim Löschen): {str(e)}")

    # 2️⃣ DB aktualisieren (unabhängig vom WebDAV-Erfolg)
    termin.caldav_uid = None
    termin.caldav_etag = None
    if typ == "termin":
        termin.abgesagt = datetime.now()
    else:
        termin.entfallen = datetime.now()

    db.session.commit()
    print("✅ Termin in DB als gelöscht markiert")

    return jsonify({
        "success": True,
        "message": "Termin wurde gelöscht",
        "deleted_from_caldav": deleted_from_caldav,
        "uid": uid
    })




# --- Route zum Pull der termine ---
def pull_termine_from_caldav(delete_action="abgesagt", log=None):
    def log_msg(msg):
        print(msg)
        if log is not None:
            log.append(msg)
    """
    Pull von CalDAV-Events in die DB.
    Nur Events mit Summary = Kunden- oder Gruppenkuerzel werden bearbeitet.
    delete_action: "abgesagt" oder "löschen" für online gelöschte Termine
    """
    config = get_webdav_config()
    client = DAVClient(
        url=config['url'],
        username=config['user'],
        password=config['password']
    )

    principal = client.principal()
    calendars = principal.calendars()

    # Probe-Kalender finden
    terminkalender_var  = Programmvariable.query.filter_by(name='termine_kalender').first()
    terminkalender_name =terminkalender_var.wert
    log_msg("kalender " + terminkalender_name)
    cal = next((c for c in calendars if terminkalender_name in str(c.url)), None)
    
    terminkalender_name = terminkalender_var.wert.lower()

    cal = next(
        (c for c in calendars
        if terminkalender_name in (c.name or "").lower()
        or terminkalender_name in str(c.url).lower()),
        None
    )

    if not cal:
        log_msg(f"❌ {terminkalender_name}-Kalender nicht gefunden")
        return

    log_msg("🔄 CalDAV Pull von Kalender" + str(cal))
    events = cal.events()

    # Alle gültigen Kürzel aus DB
    kunden = Kunde.query.all()
    gruppen = Gruppe.query.all()
    kunden_kuerzel = {k.kuerzel for k in kunden}
    gruppen_kuerzel = {g.gruppenkuerzel for g in gruppen}
    valid_kuerzel = kunden_kuerzel | gruppen_kuerzel
    valid_kuerzel_low = {k.lower() for k in valid_kuerzel}
    kunden_by_kuerzel = {k.kuerzel: k for k in kunden}
    kunden_by_kuerzel_low = {k.kuerzel.lower(): k for k in kunden}
    gruppen_by_kuerzel = {g.gruppenkuerzel: g for g in gruppen}
    gruppen_by_kuerzel_low = {g.gruppenkuerzel.lower(): g for g in gruppen}

    einzel_var = Programmvariable.query.filter_by(name='einzel_zeit').first()
    paar_var = Programmvariable.query.filter_by(name='paar_zeit').first()
    try:
        einzel_min = int(einzel_var.wert) if einzel_var and str(einzel_var.wert).strip() else 50
    except Exception:
        einzel_min = 50
    try:
        paar_min = int(paar_var.wert) if paar_var and str(paar_var.wert).strip() else 90
    except Exception:
        paar_min = 90


    # Online-UIDs sammeln (robust gegen fehlerhafte Events)
    online_uids = set()
    for ev in events:
        try:
            uid_value = ev.vobject_instance.vevent.uid.value
            if uid_value:
                online_uids.add(uid_value)
        except Exception as e:
            log_msg(f"⚠ Überspringe Event ohne UID: {e}")

    
    # DB-Events mit caldav_uid
    db_termine = Termin.query.filter(Termin.caldav_uid.isnot(None)).all()
    db_gruppen = Gruppentermin.query.filter(Gruppentermin.caldav_uid.isnot(None)).all()
    db_uids = {s.caldav_uid: s for s in db_termine + db_gruppen}

    # 1️⃣ Online gelöschte Events erkennen
    for uid, termin in db_uids.items():
        if uid not in online_uids:
            log_msg(f"🗑 Online gelöscht: UID={uid}, Titel={getattr(termin, 'beschreibung', '')}")
            # Prüfen ob Einzel- oder Gruppentermin
            timestamp = datetime.now()

            if isinstance(termin, Gruppentermin):
                if delete_action == "abgesagt":
                    if not termin.entfallen:
                        termin.entfallen = timestamp
                        log_msg("→ Gruppentermin als entfallen markiert (Timestamp gesetzt)")
                    else:
                        log_msg("→ Gruppentermin bereits entfallen, Timestamp bleibt")
                elif delete_action == "löschen":
                    db.session.delete(termin)
                    log_msg("→ Gruppentermin aus DB gelöscht")
            else:
                # Einzeltermin
                if delete_action == "abgesagt":
                    if not termin.abgesagt:
                        termin.abgesagt = timestamp
                        log_msg("→ Einzeltermin als abgesagt markiert (Timestamp gesetzt)")
                    else:
                        log_msg("→ Einzeltermin bereits abgesagt, Timestamp bleibt")
                elif delete_action == "löschen":
                    db.session.delete(termin)
                    log_msg("→ Einzeltermin aus DB gelöscht")

            db.session.commit()

    # 2️⃣ Events pullen
    for event in events:
        try:
            ve = event.vobject_instance.vevent
            uid = ve.uid.value
        except Exception as e:
            log_msg(f"⚠ Überspringe fehlerhaftes Event (kein VEVENT/UID): {e}")
            continue

        etag = get_event_etag(event)
        summary = getattr(ve.summary, "value", "").strip()

        # Nur Events mit gültigem Kürzel bearbeiten
        if summary.lower() not in valid_kuerzel_low:
            #log_msg(f"⚠ Ignoriere Event UID={uid}, Summary='{summary}'")
            continue
        #log_msg(f"   Bearbeiteter Event UID={uid}, Summary='{summary}'")
        # Prüfen, ob Event in DB existiert
        termin = db_uids.get(uid)

        if not termin:
            # Neues Online-Event mit gültigem Kürzel → minimal in DB anlegen
            print(f"Neues Event UID={uid}, Summary='{summary}'")
            start = ve.dtstart.value
            print("start:", start)
            if not hasattr(start, "hour"):
                start = datetime.combine(start, datetime.min.time())
            end = getattr(ve, "dtend", None)
            end = end.value if end and hasattr(end, "value") else end
            if end and not hasattr(end, "hour"):
                end = datetime.combine(end, datetime.min.time())

            if summary.lower() in kunden_by_kuerzel_low:
                kunde = kunden_by_kuerzel_low[summary.lower()]
                dauer_min = einzel_min if kunde.therapieform == 1 else paar_min if kunde.therapieform == 2 else 50
                beschreibung = "Einzeltherapie á " + str(einzel_min) + " min" if kunde.therapieform == 1 else "Paartherapie á " + str(paar_min) + " min" if kunde.therapieform == 2 else summary
                end = start + timedelta(minutes=dauer_min)
                neu = Termin(
                    kunde_id=kunde.id,
                    datum=start.date().isoformat(),
                    startzeit=start.time().strftime("%H:%M"),
                    endzeit=end.time().strftime("%H:%M") if end else None,
                    beschreibung=beschreibung,
                    kommentar="",
                    betrag=float(kunde.stundensatz) if kunde.stundensatz is not None else 0,
                    timestamp=datetime.utcnow().isoformat(),
                    caldav_uid=uid,
                    caldav_etag=etag
                )
                db.session.add(neu)
                db.session.commit()
                db_uids[uid] = neu
                log_msg(f"✅ Neuer Einzeltermin übernommen: UID={uid}")
                # Nach dem Anlegen: Kürzel online und Kunde case-sensitiv abgleichen
                if summary != kunde.kuerzel:
                    push_termin({
                        "termin_id": neu.id,
                        "kuerzel": kunde.kuerzel,
                        "datum": neu.datum,
                        "startzeit": neu.startzeit,
                        "endzeit": neu.endzeit,
                        "beschreibung": neu.beschreibung,
                        "caldav_uid": neu.caldav_uid,
                        "caldav_etag": neu.caldav_etag,
                        "abgesagt": None
                    })
            elif summary.lower() in gruppen_by_kuerzel_low:
                gruppe = gruppen_by_kuerzel_low[summary.lower()]
                dauer_min = gruppe.dauer_min or 60
                beschreibung = "Gruppentherapie á " + str(dauer_min) + " min"
                end = start + timedelta(minutes=dauer_min)
                neu = Gruppentermin(
                    gruppe_id=gruppe.id,
                    datum=start.date().isoformat(),
                    startzeit=start.time().strftime("%H:%M"),
                    endzeit=end.time().strftime("%H:%M") if end else None,
                    beschreibung=beschreibung,
                    kommentar="",
                    betrag=float(gruppe.standardbetrag) if gruppe.standardbetrag is not None else 0,
                    timestamp=datetime.utcnow().isoformat(),
                    caldav_uid=uid,
                    caldav_etag=etag
                )
                db.session.add(neu)
                db.session.commit()
                db_uids[uid] = neu
                log_msg(f"✅ Neuer Gruppentermin übernommen: UID={uid}")
                # Nach dem Anlegen: Kürzel online und Gruppenkuerzel case-sensitiv abgleichen
                if summary != gruppe.gruppenkuerzel:
                    push_termin({
                        "gruppentermin_id": neu.id,
                        "kuerzel": gruppe.gruppenkuerzel,
                        "datum": neu.datum,
                        "startzeit": neu.startzeit,
                        "endzeit": neu.endzeit,
                        "beschreibung": neu.beschreibung,
                        "caldav_uid": neu.caldav_uid,
                        "caldav_etag": neu.caldav_etag,
                        "entfallen": None
                    })
            continue

        # Datum & Uhrzeit
        start = ve.dtstart.value
        end = getattr(ve, "dtend", None)
        if end is not None:
            end = end.value if hasattr(end, "value") else end
            if not hasattr(end, "hour"):
                end = datetime.combine(end, datetime.min.time())
        if not hasattr(start, "hour"):
            start = datetime.combine(start, datetime.min.time())

        # 🔁 Bestehendes Event aktualisieren (auch wenn ETag fehlt)
        # Debug-Ausgabe: Online-Event vs. DB-Event
        log_msg(f"[VERGLEICH] UID={uid}")
        log_msg(f"  Online: datum={start.date().isoformat()}, startzeit={start.time().strftime('%H:%M')}, endzeit={(end.time().strftime('%H:%M') if end else None)}, beschreibung={summary}, kommentar={str(getattr(ve, 'description', '')) if hasattr(ve, 'description') else ''}")
        log_msg(f"  DB: datum={termin.datum}, startzeit={termin.startzeit}, endzeit={termin.endzeit}, beschreibung={termin.beschreibung}, kommentar={termin.kommentar}")
        try:
            log_msg(f"[DEBUG] Werte vor Assignment: start={start}, end={end}, summary={summary}, ve={ve}")
            new_datum = start.date().isoformat()
            new_startzeit = start.time().strftime("%H:%M")
            new_endzeit = end.time().strftime("%H:%M") if end else None
            #new_beschreibung = summary
            #new_kommentar = str(getattr(ve.description, "value", "")) if hasattr(ve, "description") else ""
            
        except Exception as e:
            log_msg(f"[ERROR] Exception bei Assignment: {e}")
            raise
        etag_changed = etag and termin.caldav_etag != etag
       

        fields_changed = (
            termin.datum != new_datum
            or termin.startzeit != new_startzeit
            or termin.endzeit != new_endzeit
            #or termin.beschreibung != new_beschreibung
            #or (termin.kommentar or "") != new_kommentar
        )
        
        #log_msg(f"etag_changed: {etag_changed}, fields_changed: {fields_changed}, etag in DB: {termin.caldav_etag}, etag online: {etag}")   
        if etag_changed or fields_changed or not etag:
            termin.datum = new_datum
            termin.startzeit = new_startzeit
            termin.endzeit = new_endzeit
            #termin.beschreibung = new_beschreibung
            #termin.kommentar = new_kommentar
            termin.caldav_etag = etag or termin.caldav_etag
            db.session.commit()

    log_msg("✅ CalDAV Pull abgeschlossen")


def get_event_etag(event):
    """
    Holt den ETag einer CalDAV-Event-Ressource
    Funktioniert mit allen python-caldav Versionen
    """
    href = event.url              # URL der .ics-Datei
    client = event.client         # DAVClient
    session = client.session      # requests.Session

    try:
        response = session.head(href)
        return response.headers.get("ETag")
    except Exception as e:
        print(f"⚠ Konnte ETag nicht laden: {e}")
        return None


@kalender_bp.post("/calendar/sync")
def sync_calendar():
    from datetime import datetime
    logs = []
    print("🔄 Termin-Kalender-Synchronisation gestartet backend")
    try:
        pull_termine_from_caldav(delete_action="abgesagt", log=logs)
        # Zeitstempel speichern
        pv = Programmvariable.query.filter_by(name="letzte_kalender_sync").first()
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        if not pv:
            pv = Programmvariable(name="letzte_kalender_sync", wert=now)
            db.session.add(pv)
        else:
            pv.wert = now
        db.session.commit()
        return jsonify({"success": True, "logs": logs})
    except BrokenPipeError:
        return jsonify({"success": True, "warning": "Broken pipe", "logs": logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "logs": logs}), 500
