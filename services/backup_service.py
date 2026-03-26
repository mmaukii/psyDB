import os
import shutil
from datetime import datetime, timedelta,timezone

def backup_sqlite_db(db_path, max_backups=10):
    if not os.path.exists(db_path):
        print("❌ Datenbank nicht gefunden:", db_path)
        return

    db_dir = os.path.dirname(db_path)
    db_name = os.path.basename(db_path)

    # Backup-Ordner erstellen
    backup_dir = os.path.join(db_dir, "backups", "db")
    os.makedirs(backup_dir, exist_ok=True)

    # Timestamp: yyMMdd_HHMM
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    backup_name = f"{timestamp}_{db_name}"
    backup_path = os.path.join(backup_dir, backup_name)

    # Backup erstellen
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup erstellt: {backup_name}")

    # Alle Backups auflisten
    backups = sorted(
        [f for f in os.listdir(backup_dir) if f.endswith(db_name)],
        reverse=True  # Neueste zuerst
    )

    # 1️⃣ Letztes Backup pro Woche behalten
    weekly_keep = {}
    # 2️⃣ Letztes Backup der letzten 7 Tage behalten
    last7days_keep = {}

    today = datetime.now().date()
    for f in backups:
        try:
            ts_str = f.split("_")[0]  # yyMMdd
            dt = datetime.strptime(ts_str, "%y%m%d").date()

            # Wöchentlich
            week = dt.isocalendar()[1]
            year = dt.isocalendar()[0]
            week_key = (year, week)
            if week_key not in weekly_keep:
                weekly_keep[week_key] = f

            # Letzte 7 Tage
            days_diff = (today - dt).days
            if 0 <= days_diff < 7:
                if dt not in last7days_keep:  # nur das neueste pro Tag
                    last7days_keep[dt] = f

        except Exception:
            continue

    # Dateien zum Löschen auswählen
    to_delete = []
    for idx, f in enumerate(backups):
        if idx >= max_backups and f not in weekly_keep.values() and f not in last7days_keep.values():
            to_delete.append(f)

    # Löschen
    for f in to_delete:
        try:
            os.remove(os.path.join(backup_dir, f))
            print(f"🗑️ Altes Backup gelöscht: {f}")
        except Exception as e:
            print(f"⚠️ Fehler beim Löschen {f}: {e}")
