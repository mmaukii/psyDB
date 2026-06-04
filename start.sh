#!/bin/bash

echo "Starte App..."
cd "/home/damaurer/Nextcloud/Aktuelles/01_Psy Praxis und Ausbildung/04_psyDB"

./.venv/bin/python app.py

echo "Programm beendet oder Fehler passiert"
read -p "ENTER zum Schließen..."
