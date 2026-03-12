# Bedienungsanleitung und Seitenübersicht

## Konfiguration

In der Datei `config.ini` können folgende Einstellungen angepasst werden:

- **db_file**: Pfad zur verwendeten Datenbankdatei (Abschnitt [database], Schlüssel `db_file`)
- **max_backups**: Anzahl der aufzubewahrenden Backupdateien (Abschnitt [database], Schlüssel `max_backups`)

Beispiel:

    [database]
    db_file = /Pfad/zur/praxis.db
    max_backups = 10

Diese Werte steuern, welche Datenbank verwendet wird und wie viele Backups automatisch behalten werden.

**Backup-Strategie:**
- Bei jedem Backup wird eine Kopie der aktuellen Datenbank erstellt.
- Es werden maximal so viele Backups behalten, wie in `max_backups` angegeben.
- Zusätzlich werden folgende Backups automatisch aufbewahrt:
    - Das jeweils letzte Backup jeder Woche (Wochensicherung)
    - Das jeweils letzte Backup der letzten 7 Tage (Tagessicherung)
- Ältere Backups, die nicht unter diese Regeln fallen, werden automatisch gelöscht.

---

## Dashboard
**Beschreibung:**
Das Dashboard bietet einen schnellen Überblick über aktuelle Termine, überfällige Rechnungen und Mahnungen. Es dient als Startseite und zeigt wichtige Kennzahlen und Hinweise an.

**Bedienung:**
- Anzeige heutiger Termine (informativ)
- Anzeige überfälliger Rechnungen (informativ)
- Anzeige aktueller Mahnungen (informativ)

**Buttons/Funktionen:**
- Keine direkten Buttons, nur Übersicht.

---

## Kalender
**Beschreibung:**
Im Kalender werden alle Termine übersichtlich dargestellt. Es können sowohl interne als auch externe (z.B. CalDAV) Kalender synchronisiert und angezeigt werden.

**Bedienung:**
- Termine per Klick anzeigen, bearbeiten oder neu anlegen
- Synchronisation mit Praxiskalender und externen Kalendern
- Externe Events ein-/ausblenden

**Buttons/Funktionen:**
- **SyncButton:** Synchronisiert den Praxiskalender.
- **SyncExterneButton:** Synchronisiert externe Events.
- **ToggleExterne (Checkbox):** Zeigt/verbirgt externe Events.
- **EventPopup:** Felder für Terminbearbeitung (Datum, Zeit, Beschreibung, Kunde/Gruppe).

---

## Kunden
**Beschreibung:**
Hier werden alle Kunden verwaltet. Es können neue Kunden angelegt, bestehende bearbeitet oder gefiltert werden.

**Bedienung:**
- Kundenliste filtern (aktiv/inaktiv/alle)
- Suche nach Kunden
- Kunden per Klick auswählen und bearbeiten


**Buttons/Funktionen:**
- **kundenAktivFilter:** Auswahlfilter für aktive/inaktive/alle Kunden.
- **Suchfeld:** Filtert die Kundenliste nach Namen/Kürzel.
- **Bearbeiten:** Schaltet in den Bearbeitungsmodus.
- **MailKundeBtn:** Sendet eine Mail an den Kunden.
- **Neuer Termin:** Öffnet das Terminfenster für den ausgewählten Kunden.

**Pflichtfelder:**
- Name
- Vorname
- Nachname
- Kürzel

---

## Gruppen
**Beschreibung:**
Verwaltung von Therapiegruppen. Gruppen können angelegt, bearbeitet und gefiltert werden.

**Bedienung:**
- Gruppenliste filtern (aktiv/inaktiv/alle)
- Suche nach Gruppen
- Gruppen per Klick auswählen und bearbeiten


**Buttons/Funktionen:**
- **gruppenAktivFilter:** Auswahlfilter für aktive/inaktive/alle Gruppen.
- **Suchfeld:** Filtert die Gruppenliste.
- **Bearbeiten:** Schaltet in den Bearbeitungsmodus.
- **MailGruppeBtn:** Mail an Teilnehmer.
- **Neu:** Legt eine neue Gruppe an.
- **Löschen:** Löscht die ausgewählte Gruppe.
- **Speichern:** Speichert Änderungen.

**Pflichtfelder:**
- Gruppenname
- Gruppen-Kürzel
- Standardbetrag
- Dauer (min)

---

## Rechnungen
**Beschreibung:**
Hier werden alle Rechnungen verwaltet. Es gibt Filtermöglichkeiten nach Nummer, Kunde, Status und Datum.

**Bedienung:**
- Rechnungen filtern und durchsuchen
- Bearbeitungsmodus aktivieren
- Rechnungen anzeigen, bearbeiten, als bezahlt markieren


**Buttons/Funktionen:**
- **FilterRechnungsNr:** Filtert nach Rechnungsnummer.
- **FilterRechnungsKunde:** Filtert nach Kunde.
- **FilterRechnungsStatus:** Filtert nach Status (offen/bezahlt).
- **RechnungsDatumVon/Bis:** Filtert nach Zeitraum.
- **toggleButtonRechnung:** Schaltet Bearbeitungsmodus.
- **Speichern:** Speichert Änderungen.
- **Neu:** Legt neue Rechnung an.
- **Löschen:** Löscht Rechnung.

**Pflichtfelder:**
- Rechnungsnummer
- Kunde/Kürzel
- Datum
- Betrag

---

## Standorte
**Beschreibung:**
Verwaltung der Praxisstandorte mit allen relevanten Daten wie Adresse, Bankverbindung etc.

**Bedienung:**
- Standorte anzeigen und bearbeiten
- Neuen Standort hinzufügen
- Felder direkt in der Tabelle editieren


**Buttons/Funktionen:**
- **addStandortBtn:** Fügt neuen Standort hinzu.
- **addDruckvorlageBtn:** Fügt neue Druckvorlage hinzu.
- **Druckvorlagen:** Name, Pfad, Aktionen.
- **Programmvariablen:** Verschiedene Einstellungen für die Praxis.
- **Logo-File Picker:** Auswahl einer Logo-Datei.

**Pflichtfelder:**
- Name
- Adresse
- PLZ
- Ort
- Kürzel

---

## Termine
**Beschreibung:**
Übersicht und Verwaltung aller Termine, mit Filtermöglichkeiten nach Kunde, Gruppe, Status und Zeitraum.

**Bedienung:**
- Termine filtern und durchsuchen
- Einzelne oder mehrere Termine auswählen
- Rechnungen für ausgewählte Termine erstellen


**Buttons/Funktionen:**
- **FilterVorname/Nachname/Kürzel/Gruppe:** Filterfelder.
- **FilterTermineStatus:** Filtert nach Status (abgesagt/nicht abgesagt).
- **RechnungsDatumVon/Bis:** Filtert nach Zeitraum.
- **filterLeeren:** Setzt Filter zurück.
- **getSelectedButton:** Erstellt Rechnungen für ausgewählte Termine.
- **selectAllTermine:** Wählt alle Termine aus.

**Pflichtfelder:**
- Datum
- Vorname
- Nachname
- Kürzel
- Startzeit
- Endzeit

---

## Terminfenster (Modal)
**Beschreibung:**
Popup-Fenster zum Anlegen oder Bearbeiten eines Termins.

**Bedienung:**
- Felder ausfüllen (Datum, Zeit, Kunde/Gruppe, Betrag, Beschreibung)
- Termin speichern, absagen/entfallen oder löschen
- Serientermine anlegen


**Buttons/Funktionen:**
- **Speichern:** Speichert den Termin.
- **Absagen/Entfallen:** Markiert den Termin als abgesagt/entfallen (setzt Zeitstempel).
- **Löschen:** Löscht den Termin.

**Pflichtfelder:**
- Datum
- Startzeit
- Endzeit
- Betrag
- Beschreibung
- Kunde oder Gruppe

---

*Diese Übersicht kann als Hilfeseite oder Dokumentation genutzt werden.*
