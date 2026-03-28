let selectedGruppeId = localStorage.getItem("selectedGruppeId");

const form = document.getElementById("gruppenForm");
const gruppenDokuText = document.getElementById("gruppenDokuText");
const gruppenDokuSaveBtn = document.getElementById("gruppenDokuSaveBtn");
const mailGruppeBtn = document.getElementById("mailGruppeBtn");

reloadGruppenTabelle();

if (mailGruppeBtn) {
    mailGruppeBtn.addEventListener("click", async () => {
        const gruppeId = document.getElementById("gruppenForm_id").value;
        if (!gruppeId) {
            alert("Bitte zuerst eine Gruppe auswählen.");
            return;
        }

        try {
            const res = await fetch(`/api/gruppen/${gruppeId}/kunden`);
            if (!res.ok) throw new Error("Fehler beim Laden der Teilnehmer");
            const kunden = await res.json();
            const emails = kunden
                .map(k => (k.email || "").trim())
                .filter(e => e.length > 0);

            if (emails.length === 0) {
                alert("Keine E-Mail-Adressen bei den Teilnehmern gefunden.");
                return;
            }

            const gruppenname = (document.getElementById("gruppenname").value || "").trim();
            const subject = `Info zur Gruppe ${gruppenname ? gruppenname  : ""}`;
            const body = `Hallo Teilnehmer der Gruppe - ${gruppenname ? gruppenname : ""}!`;

            const mailto = `mailto:?bcc=${encodeURIComponent(emails.join(","))}` +
                `&subject=${encodeURIComponent(subject)}` +
                `&body=${encodeURIComponent(body)}`;

            window.location.href = mailto;
        } catch (err) {
            console.error(err);
            alert("Fehler beim Erstellen der E-Mail.");
        }
    });
}

// Filterfunktion
document.getElementById("search").addEventListener("input", function() {
    const f = this.value.toLowerCase();
    document.querySelectorAll("#gruppentabelle tbody tr").forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(f) ? "" : "none";
    });
});

// Funktion: Zeile anklickbar machen – jetzt async
function activateRowEvents() { 
    const rows = document.querySelectorAll("#gruppentabelle tbody tr");

  
    rows.forEach(row => {
        row.addEventListener("click", async () => {
            selectedGruppeId = row.dataset.id;
            localStorage.setItem("selectedGruppeId", selectedGruppeId);

            // visuell hervorheben
            document.querySelectorAll("#gruppentabelle tbody tr")
                .forEach(r => r.classList.remove("selected"));
            row.classList.add("selected");

            // Formular befüllen
            document.getElementById("gruppenForm_id").value = row.dataset.id; 
            document.getElementById("gruppenname").value = row.dataset.gruppenname;
            document.getElementById("gruppenkuerzel").value = row.dataset.gruppenkuerzel;
            document.getElementById("standardbetrag").value = row.dataset.standardbetrag;
            document.getElementById("dauer_min").value = row.dataset.dauer_min;
            if (gruppenDokuText) {
                gruppenDokuText.value = row.dataset.doku || "";
            }
            document.getElementById("rechnungstext").value = row.dataset.rechnungstext;
            document.getElementById("aktiv").checked = row.dataset.aktiv === "1" || row.dataset.aktiv === "true";
            document.getElementById("therapieform").value = row.dataset.therapieform || "";

            

            // Kunden laden
            await loadSelectedKunden(row.dataset.id);

            // Termine laden
            console.log("tabellen laden")
            console.log(row.dataset.id)
            reloadGruppentermineAnwesenheit(row.dataset.id);

        });
    });
}

//laden anwesenheitstabelle Terminetabelle

//laden der Terminetabelle/
async function reloadGruppentermineAnwesenheit(gruppeId) {
    // Termine laden
    try {
        console.log("Lade Gruppentermine für Gruppe ID:", gruppeId);
        // 1️⃣ Fetch für Gruppentermine mit Teilnehmern
        const response = await fetch(`api/gruppentermine/${gruppeId}/termine`);
        if (!response.ok) throw new Error("Fehler beim Laden der Gruppentermine");
        const gruppentermine = await response.json();
        console.log("gruppentermine", gruppentermine)

        // 2️⃣ Fetch für alle bestehenden Termine
        console.log("Lade alle Termine für Anwesenheitsabgleich");
        const termineResponse = await fetch("api/termine");
        if (!termineResponse.ok) throw new Error("Fehler beim Laden aller Termine");
        const alleTermine = await termineResponse.json(); // enthält gruppe_id + kunde_id

        // 2️⃣ Fetch für alle bestehenden kunden
        const kunden = await fetch(`/api/gruppen/${gruppeId}/kunden`);
        if (!kunden.ok) throw new Error("Fehler beim Laden aller Kunden");
        const alleKunden = await kunden.json(); // enthält gruppe_id + kunde_id
        console.log("alleKunden", alleKunden)

        if (gruppentermine.length === 0) {
            termineProGruppeListe.innerHTML = `<tr><td colspan="3">Keine Termine vorhanden.</td></tr>`;
            termineProGruppeAnwesenheitsListe.innerHTML = `<tr><td colspan="3">Keine Termine vorhanden.</td></tr>`;
        } else {

            termineProGruppeAnwesenheitsListe.innerHTML = gruppentermine.map(st => {
                // Datum umformatieren von YYYY-MM-DD → DD.MM.YYYY
                console.log("Stundendaten für Anwesenheitstabelle:", st);
                const datumParts = st.datum.split("-");
                const datumDeutsch = `${datumParts[2]}.${datumParts[1]}.${datumParts[0]}`;
                // Zeile zurückgeben, Klasse "abgesagt" setzen, optional display:none wenn Toggle aktiv
                const rowStyle = (st.entfallen && toggleAbgesagtBtn.dataset.show === "false") ? "display:none;" : "";

                function utcToLocalTime(dateStr, utcTime) {
                    if (!dateStr || !utcTime) return "";
                    const [h, m, s] = utcTime.split(":");
                    const date = new Date(Date.UTC(
                        parseInt(dateStr.slice(0, 4)),
                        parseInt(dateStr.slice(5, 7)) - 1,
                        parseInt(dateStr.slice(8, 10)),
                        h, m, s || 0
                    ));
                    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                }

                return `
                <tr data-id="${st.id}" class="${st.entfallen ? 'abgesagt' : ''}" style="${rowStyle}"
                    data-utc_starttime="${utcToLocalTime(st.datum, st.utc_starttime)}" 
                    data-utc_endtime="${utcToLocalTime(st.datum, st.utc_endtime)}" 
                    data-betrag="${st.betrag}">
                    <th align="center">${datumDeutsch}</td>
                    <td>${st.beschreibung}</td>
                    <td>
                        <div class="anwesenheit-container">
                            ${st.teilnehmer.map(t => {
                                // Prüfen, ob für diese Gruppentermin und diesen Kunden bereits eine Termin existiert
                                const istSelected = alleTermine.some(s =>
                                    s.gruppentermin_id === st.id && s.kunde_id === t.kunde_id
                                );
                                return `
                                    <div class="anwesenheit-tag ${istSelected ? 'selected' : ''}" 
                                        data-kunden-id="${t.kunde_id}">
                                        ${t.kuerzel}
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </td>
                    <td class="actions">
                        <button class="refresh-btn" onclick="aktualisiereTermin(this, ${st.id}, '${st.datum}')" title="Speichern der Anwesenheit">
                            💾
                        </button>
                    </td>
                </tr>
            `}).join("");

            termineProGruppeListe.innerHTML = gruppentermine.map(st => {
                // Datum umformatieren von YYYY-MM-DD → DD.MM.YYYY
                const datumParts = st.datum.split("-");
                const datumDeutsch = `${datumParts[2]}.${datumParts[1]}.${datumParts[0]}`;
                let betragNum = parseFloat(st.betrag);
                let betragFormatted = isNaN(betragNum) ? "" : new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(betragNum);
                // Zeile zurückgeben, Klasse "abgesagt" setzen, optional display:none wenn Toggle aktiv
                const rowStyle = (st.entfallen && toggleAbgesagtBtn.dataset.show === "false") ? "display:none;" : "";

                // Zeitfelder in lokale Zeit umwandeln
                 function utcToLocalTime(dateStr, utcTime) {
                    if (!dateStr || !utcTime) return "";
                    const [h, m, s] = utcTime.split(":");
                    const date = new Date(Date.UTC(
                        parseInt(dateStr.slice(0, 4)),
                        parseInt(dateStr.slice(5, 7)) - 1,
                        parseInt(dateStr.slice(8, 10)),
                        h, m, s || 0
                    ));
                    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                }

                const localStart = utcToLocalTime(st.datum, st.utc_starttime);
                const localEnd = utcToLocalTime(st.datum, st.utc_endtime);

                return `
                <tr data-id="${st.id}" class="${st.entfallen ? 'abgesagt' : ''}" style="${rowStyle}">
                    <th align="center">${datumDeutsch}</td>
                    <td align="center">${utcToLocalTime(st.datum, st.utc_starttime)}</td>
                    <td align="center">${utcToLocalTime(st.datum, st.utc_endtime)}</td>
                    <td>${st.beschreibung}</td>
                    <td align="right">${betragFormatted} €</td>
                    <td>
                        <button class="editBtnTermineProGruppe table-btn" data-id="${st.id}" title="Datensatz editieren">🛠️</button>
                        <button class="dokuBtntermineproKunde table-btn" data-id="${st.id}" title="Doku Eintrag erstellen/bearbeiten">📚</button>
                        <button class="absageBtnGruppe table-btn" data-id="${st.id}" title="Ereignis absagen">🚫</button>
                        <button class="deleteBtnTermineProGruppe table-btn" data-id="${st.id}" title="Datensatz löschen">🗑️</button>                     
                    </td>
                </tr>
            `}).join("");

            // Event Listener für Toggle direkt nach Einfügen
            termineProGruppeAnwesenheitsListe.querySelectorAll(".anwesenheit-tag").forEach(tag => {
                tag.addEventListener("click", () => {
                    tag.classList.toggle("selected"); // toggelt Auswahl
                });
            });
        }
       if (!kunden || kunden.length === 0) {
            BetragTeilnehmerListe.innerHTML = `<tr><td colspan="3">Keine Termine vorhanden.</td></tr>`;
        } else {
            const rawBetrag = document.getElementById("standardbetrag").value || "0";
            const gruppeId = document.getElementById("gruppenForm_id").value; // aktuelle Gruppe

            BetragTeilnehmerListe.innerHTML = alleKunden.map(k => {
                let betragNum = parseFloat(k.betrag);
                let betragFormatted = isNaN(betragNum)
                    ? rawBetrag
                    : new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(betragNum);

                return `
                    <tr data-id="${k.id}" data-gruppe-id="${gruppeId}">
                        <td>${k.kuerzel} - ${k.nachname}</td>
                        <td contenteditable="true" data-field="betrag" style="text-align:right;">
                            ${betragFormatted}
                        </td>
                    </tr>
                `;
            }).join("");

            // Listener für Änderungen
            // Listener für direkte Änderungen
            BetragTeilnehmerListe.querySelectorAll('[contenteditable][data-field="betrag"]').forEach(cell => {
                const tr = cell.closest("tr");
                const kundeId = tr.dataset.id;
                const gruppeId = tr.dataset.gruppeId;

                const saveBetrag = async () => {
                    const neuerBetrag = parseFloat(cell.innerText.replace(",", "."));
                    if (isNaN(neuerBetrag)) return;
                    console.log(`Neuer Betrag für Kunde ${kundeId} in Gruppe ${gruppeId}: ${neuerBetrag} €`);
                    
                    try {
                        await fetch(`/api/gruppen/${gruppeId}/kunden/${kundeId}`, {
                            method: "PUT",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ betrag: neuerBetrag })
                        });
                        console.log(`Gruppe ${gruppeId}, Kunde ${kundeId} aktualisiert: ${neuerBetrag} €`);
                    } catch (err) {
                        console.error("Fehler beim Speichern:", err);
                        alert(`Fehler beim Speichern des Betrags für Kunde ${kundeId}`);
                    }
                    showToast("Neuer Betrag gespeichert", 1500);
                };

                // Speichern bei Blur
                cell.addEventListener("blur", saveBetrag);

                // Speichern bei Enter
                cell.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") {
                        e.preventDefault(); // kein Zeilenumbruch
                        cell.blur();        // löst automatisch saveBetrag aus
                    }
                });
            });
        }

            


    } catch (err) {
        console.error(err);
        termineProGruppeListe.innerHTML = `<tr><td colspan="6">Fehler beim Laden der Termine.</td></tr>`;
        termineProGruppeAnwesenheitsListe.innerHTML = `<tr><td colspan="6">Fehler beim Laden der Anwesenheit.</td></tr>`;
    }

} 

//akutalisieren Tabellen nach schließen fensterTerminAnpassen
document.addEventListener("kalenderTermineAnpassung", function (e) {
    reloadGruppentermineAnwesenheit(document.getElementById("gruppenForm_id").value); // einfach, zuverlässig
});

//für button löschen delete in der Tabelle
const termineProGruppeListeElement =
    document.getElementById("termineProGruppeListe");

termineProGruppeListeElement.addEventListener("click", async (e) => {

    // 🗑️ LÖSCHEN
    if (e.target.classList.contains("deleteBtnTermineProGruppe")) {
        const id = e.target.dataset.id;
        if (!confirm("Soll diese Termin wirklich gelöscht werden?")) return;

        try {
            const res = await fetch(`/api/gruppentermine/${id}`, { method: "DELETE" });
            if (res.ok) {
                e.target.closest("tr").remove();
                console.log("🗑️ Termin gelöscht:", id);
            } else {
                alert("Fehler beim Löschen");
            }
        } catch (err) {
            console.error(err);
            alert("Verbindung fehlgeschlagen");
        }
    }

    // 🛠️ BEARBEITEN
    if (e.target.classList.contains("editBtnTermineProGruppe")) {
        const id = e.target.dataset.id;
        console.log("🛠️ Termin bearbeiten:", id);

        try {
            const response = await fetch(`/api/gruppentermine/${id}`);
            if (!response.ok) throw new Error("Fehler beim Laden");

            const stunde = await response.json();

            openfensterTerminAnpassen({
                stundensatz: stunde.betrag || "",
                beschreibung: stunde.beschreibung || "",
                datum: stunde.datum || "",
                utc_starttime: stunde.utc_starttime || "",
                utc_endtime: stunde.utc_endtime || "",
                stundeId: stunde.id || "",
                gruppeId: stunde.gruppe_id || ""
            });

        } catch (err) {
            console.error(err);
            alert("Fehler beim Laden der Termin");
        }
    }

    if (e.target.classList.contains("absageBtnGruppe")) {
        const stundeId = e.target.dataset.id;
        const row = e.target.closest("tr");
        const btn = e.target;

        // --- Doku-Eintrag abfragen ---
        let dokuText = prompt("Optional: Doku-Eintrag zur Absage hinzufügen (leer lassen für keinen Eintrag):", "");
        if (dokuText === null) return; // Abbruch

        // --- UI sofort ---
        row.classList.add("abgesagt");
        btn.disabled = true;
        btn.textContent = "Abgesagt";

        const datumCell = row.cells[0];
        datumCell.innerHTML = `<s>${datumCell.textContent}</s>`;

        if (toggleAbgesagtBtn.dataset.show === "false") {
            row.style.display = "none";
        }

        // --- Fetch im Hintergrund ---
        fetch(`/api/gruppentermine/${stundeId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ entfallen: 1, doku: dokuText })
        })
        .then(res => {
            if (!res.ok) throw new Error("Fehler beim Absagen");
            return res.text();
        })
        .then(result => console.log("Server bestätigt Absage:", result))
        .catch(err => {
            console.error(err);
            // Optional: UI zurücksetzen, falls Fehler
            row.classList.remove("abgesagt");
            btn.disabled = false;
            btn.textContent = "🚫";
            datumCell.textContent = datumCell.textContent.replace(/^\u0336+|\u0336+$/g, "");
            alert("Absage konnte nicht gespeichert werden!");
        });
    }

    // ===============================
    // � DOKU BUTTON GEDRÜCKT
    // ===============================
    if (e.target.classList.contains("dokuBtntermineproKunde")) {
        const gruppentermineId = e.target.dataset.id;
        console.log("Doku Button gedrückt für Termin ID:", gruppentermineId);
        const res = await fetch(`/api/gruppentermine/${gruppentermineId}`);
        if (!res.ok) {
            alert("Fehler beim Laden der Doku!");
            return;
        }
         const stunde = await res.json();

        console.log("📚 Doku öffnen für Termin:", gruppentermineId);

        openFensterDoku({
            gruppentermineId,
            doku : stunde.doku || ""
        });
     }   
});

// Referenz auf Button holen
const toggleAbgesagtBtn = document.getElementById("toggleAbgesagtBtn");

// Startzustand: abgesagte Zeilen verstecken (auch bei dynamisch geladenen)
function hideAbgesagteRows() {
  document.querySelectorAll("#termineProGruppeListe tr.abgesagt").forEach(row => {
    row.style.display = "none";
  });
  console.log("Abgesagte Zeilen ausgeblendet");
}
hideAbgesagteRows();

// Klick-Event für Toggle-Button
toggleAbgesagtBtn.addEventListener("click", () => {
  const currentlyShown = toggleAbgesagtBtn.dataset.show === "true";
  const rows = document.querySelectorAll("#termineProGruppeListe tr.abgesagt");

  rows.forEach(row => {
    row.style.display = currentlyShown ? "none" : "";
  });

  const rows1 = document.querySelectorAll("#termineProGruppeAnwesenheitsListe tr.abgesagt");

  rows1.forEach(row => {
    row.style.display = currentlyShown ? "none" : "";
  });

  toggleAbgesagtBtn.dataset.show = (!currentlyShown).toString();
  toggleAbgesagtBtn.textContent = currentlyShown
    ? "Abgesagte anzeigen"
    : "Abgesagte ausblenden";
});

// Funktion: Termin aktualisieren basierend auf ausgewählten Teilnehmern
async function aktualisiereTermin(button, termineId,datum) {
    const tr = button.closest("tr");
    showToast("Wird akualisiert …", null);
    if (!tr) {
        console.error("Keine Tabellenzeile gefunden");
        return;
    }

    const gruppenId = document.getElementById("gruppenForm_id").value;

    // ausgewählte Teilnehmer
    const selectedDivs = tr.querySelectorAll(".anwesenheit-tag.selected");
    const selectedIds = Array.from(selectedDivs).map(div => div.dataset.kundenId);
    const dauer = document.getElementById("dauer_min").value

    console.log("Gruppentermine-ID:", termineId);
    console.log("Ausgewählte Kunden-IDs:", selectedIds);

    const { utc_starttime, utc_endtime } = tr.dataset;

    try {
        // 1️⃣ vorhandene Termine laden
        const res = await fetch("/api/termine");
        const allTermine = await res.json();

        const termineDerGruppe = allTermine.filter(
            s => s.gruppentermin_id === termineId
        );

        const vorhandeneIds = termineDerGruppe.map(s => s.kunde_id.toString());

        // 2️⃣ NEU → POST (Betrag pro Kunde von Flask holen)
        await Promise.all(selectedIds.map(async kundeId => {
            if (!vorhandeneIds.includes(kundeId)) {
                // Betrag von Flask abrufen
                const rawBetrag = parseFloat(document.getElementById("standardbetrag").value) || 0;

                const betragRes = await fetch(`api/gruppen/${gruppenId}/kunden/${kundeId}/betrag`);
                let betrag = rawBetrag; // Standard fallback

                if (betragRes.ok) {
                    const betragData = await betragRes.json();
                    const fetchedBetrag = parseFloat(betragData.betrag);
                    if (!isNaN(fetchedBetrag) && fetchedBetrag > 0) {
                        betrag = fetchedBetrag; // nur überschreiben, wenn gültig
                    }
                }
                

                
                const createRes = await fetch(`/api/termine/${kundeId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        datum: datum,
                        utc_starttime,
                        utc_endtime,
                        betrag,
                        gruppentermin_id: termineId,
                        beschreibung: "Gruppentherapie á " + dauer + " min",
                        push_termin: 1 
                    })
                });
                const createData = await createRes.json();
                console.log("➕ Termin erstellt:", createData);
            }
        }));

        // 3️⃣ ENTFERNT → DELETE
        await Promise.all(termineDerGruppe.map(async s => {
            if (!selectedIds.includes(s.kunde_id.toString())) {
                const delRes = await fetch(`/api/termine/${s.id}`, { method: "DELETE" });
                const delData = await delRes.json();
                console.log("🗑️ Termin gelöscht:", delData);
            }
        }));

        // 4️⃣ VORHANDEN → PUT (optional)
        await Promise.all(termineDerGruppe.map(async s => {
            if (selectedIds.includes(s.kunde_id.toString())) {
                await fetch(`/api/termine/${s.id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        changestamp: new Date().toISOString(),
                        push_termin: 1  // ✅ Push-Flag für das Backend
                     })
                });
            }
        }));

    } catch (err) {
        console.error("Fehler:", err);
    }
}


// Nach dem Einfügen: Klick-Events auf Tags
document.querySelectorAll('.anwesenheit-container .anwesenheit-tag').forEach(tag => {
    tag.addEventListener('click', () => {
        tag.classList.toggle('selected'); // toggelt Zustand
        // Optional: hier könntest du z.B. eine API call machen oder Array aktualisieren
    });
});

//Bearbeitung ein und ausblenden
//zeilen ein ausblenden
const toggleButton = document.getElementById("toggleButton");
const gruppenBereich = document.getElementById("gruppenBereich");
const kundenAuswahl = document.getElementById("kundenAuswahl");

toggleButton.addEventListener("click", () => {
    const isHidden = gruppenBereich.style.display === "none" || gruppenBereich.style.display === "";

    if (isHidden) {
        // Bereiche einblenden
        gruppenBereich.style.display = "grid";
        kundenAuswahl.style.display = "grid";
        toggleButton.classList.add("active");  // roter Rahmen
    } else {
        // Bereiche ausblenden
        gruppenBereich.style.display = "none";
        kundenAuswahl.style.display = "none";
        toggleButton.classList.remove("active");  // Rahmen weg
    }
});

// Initial aktivieren
activateRowEvents();


// Neu-Button
// Neuer Gruppe Button
document.getElementById("neuBtnGruppe").addEventListener("click", () => {
    document.getElementById("gruppenForm").reset();
    document.getElementById("gruppenForm_id").value = "";
    document.getElementById("aktiv").checked = true;
    if (gruppenDokuText) {
        gruppenDokuText.value = "";
    }

    // Ausblendbaren Bereich einblenden
    document.getElementById("gruppenBereich").style.display = "grid";

    // Optional: scrollen zum Formular
    document.getElementById("gruppenBereich").scrollIntoView({ behavior: "smooth", block: "start" });
});

// Löschen-Button
document.getElementById("loeschenBtnGruppe").addEventListener("click", async () => {
    const id = document.getElementById("gruppenForm_id").value;
    if (!id) return alert("Keine Gruppe ausgewählt.");

    if (confirm("Diese Gruppe wirklich löschen?")) {
        const response = await fetch(`api/gruppen/${id}`, { method: "DELETE" });
        if (response.ok) {
            // Formular zurücksetzen
            document.getElementById("gruppenForm").reset();
            document.getElementById("gruppenForm_id").value = "";
            lastSelectedGruppeId = null; // Markierung zurücksetzen

            // Tabelle neu laden
            await reloadGruppenTabelle();
        }
    }
});

//Änderung speichern-Button
document.getElementById("gruppenForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const rawBetrag = document.getElementById("standardbetrag").value;
    // Komma durch Punkt ersetzen, dann in Float konvertieren
    const standardbetrag = parseFloat(rawBetrag.replace(",", "."));
    const aktivValue = document.querySelector('[name="aktiv"]').checked ? 1 : 0;

    const id = document.getElementById("gruppenForm_id").value;
    const data = {
        gruppenname: document.getElementById("gruppenname").value,
        gruppenkuerzel: document.getElementById("gruppenkuerzel").value,
        standardbetrag: standardbetrag,
        dauer_min: document.getElementById("dauer_min").value,
        doku: gruppenDokuText ? gruppenDokuText.value : "",
        rechnungstext: document.getElementById("rechnungstext").value,
        therapieform: document.getElementById("therapieform").value,
        aktiv: aktivValue
    };

    const kundenData = {
        kunden_ids: selected.map(k => k.id)  // ausgewählte Kunden
    };

    try {
        if (id) {
            // 1️⃣ Gruppe anpassen
            await fetch(`/api/gruppen/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            // 2️⃣ Kunden anpassen
            await fetch(`/api/gruppen/${id}/kunden`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(kundenData)
            });

            showToast("Gespeichert");
        } else {
            // Neue Gruppe anlegen
            const response = await fetch("/api/gruppen", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            const newId = result.id;

            // Kunden zu neuer Gruppe hinzufügen
            await fetch(`/api/gruppen/${newId}/kunden`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(kundenData)
            });

            document.getElementById("gruppenForm_id").value = newId;
            showToast("Neue Gruppe erstellt mit Kunden");
        }

        await reloadGruppenTabelle();
    } catch (err) {
        console.error(err);
        alert("❌ Fehler beim Speichern der Gruppe oder Kunden");
    }
});


document.getElementById("gruppenAktivFilter").addEventListener("change", () => {
    ersteZeileAusgewaehlt = false; // optional
    console.log("Filter geändert, Tabelle wird neu geladen");
    reloadGruppenTabelle();
});

//---------------------------------------------------------
// Tabelle neu laden – ANALOG zu Kunden
//---------------------------------------------------------
let ersteZeileAusgewaehlt = false; // Flag, um nur einmal auszuwählen
async function reloadGruppenTabelle() {
    selectedGruppeId = localStorage.getItem("selectedGruppeId"); // 🔥 WICHTIG
    const filter = document.getElementById("gruppenAktivFilter").value;

    let url;
    switch (filter) {
        case "aktiv":
            url = "/api/gruppen/aktiv";
            break;
        case "inaktiv":
            url = "/api/gruppen/inaktiv";
            break;
        case "alle":
        default:
            url = "/api/gruppen";
    }
    const res = await fetch(url);
    const gruppen = await res.json();
    console.log("Geladene Gruppen:", gruppen);
    // Sortieren nach Kürzel alphabetisch
    gruppen.sort((a, b) => {
        const kuerzelA = a.gruppenkuerzel.toLowerCase();
        const kuerzelB = b.gruppenkuerzel.toLowerCase();
        if (kuerzelA < kuerzelB) return -1;
        if (kuerzelA > kuerzelB) return 1;
        return 0;
    });

    const tbody = document.querySelector("#gruppentabelle tbody");
    tbody.innerHTML = gruppen.map(g => {
    // stundensatz formatieren
    console.log("standardbetrag roh:", g.standardbetrag, typeof g.standardbetrag);

    let standardbetragNum = parseFloat(g.standardbetrag);
    let standardbetragFormatted = isNaN(standardbetragNum) ? "" : new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(standardbetragNum);

    return `
        <tr
            data-id="${g.id}"
            data-gruppenname="${g.gruppenname}"
            data-standardbetrag="${standardbetragFormatted}"
            data-dauer_min="${g.dauer_min}"
            data-gruppenkuerzel="${g.gruppenkuerzel}"
            data-doku="${g.doku}"
            data-rechnungstext="${g.rechnungstext}"
            data-aktiv="${g.aktiv}"
            data-therapieform="${g.therapieform}">
            <td>${g.gruppenkuerzel}</td>
        </tr>
    `}).join("");

    // Event-Listener für neue Zeilen
    activateRowEvents();

    // --- Kunde nach Reload automatisch auswählen ---
    let rowToSelect = null;

    if (selectedGruppeId) {
        rowToSelect = tbody.querySelector(
            `tr[data-id="${selectedGruppeId}"]`
        );
    }

    // Fallback: erste Zeile
    if (!rowToSelect) {
        rowToSelect = tbody.querySelector("tr[data-id]");
    }

    if (rowToSelect) {
        rowToSelect.click();
    }
}

// Kundenauswahl
let kunden = [];
let selected = [];

const selectedDiv = document.getElementById("selectedKunden");
const listDiv = document.getElementById("list");
const searchInput = document.getElementById("searchKundefuergruppe");

// Kunden von Flask laden
let kundenGeladen = false;
async function loadKunden() {
    if (kundenGeladen) return;

    try {
        const response = await fetch("/api/kunden");
        if (!response.ok) throw new Error("Fehler beim Laden der Kunden");
        kunden = await response.json();
        kundenGeladen = true;
        renderList();
    } catch (err) {
        console.error(err);
        listDiv.innerHTML = "<div>Fehler beim Laden der Kunden</div>";
    }
}

// Liste rendern mit Filter
function renderList() {
    const filter = searchInput.value.toLowerCase().trim();
    listDiv.innerHTML = kunden
        .filter(k => !selected.some(s => s.id === k.id))
        .filter(k => {
            const text = `${k.kuerzel} ${k.nachname} ${k.vorname}`.toLowerCase();
            return text.includes(filter);
        })
        .map(k => `<div onclick="addItem(${k.id})">${k.kuerzel} - ${k.nachname}, ${k.vorname}</div>`)
        .join("");

    if (listDiv.innerHTML === "") {
        listDiv.innerHTML = "<div style='color:#888;padding:5px;'>Keine Treffer</div>";
    }
}

// Ausgewählte Kunden rendern
function renderSelected() {
    selectedDiv.innerHTML = selected
        .map(k => `<div class="tag">${k.kuerzel} - ${k.nachname}<span onclick="removeItem(${k.id})">×</span></div>`)
        .join("");
}

// Hinzufügen
window.addItem = function(id) {
    const kunde = kunden.find(k => k.id === id);
    if (kunde && !selected.includes(kunde)) selected.push(kunde);
    renderSelected();
    renderList();
};

// Entfernen
window.removeItem = function(id) {
    const idx = selected.findIndex(k => k.id === id);
    if (idx !== -1) selected.splice(idx, 1);
    renderSelected();
    renderList();
};

// Suche
searchInput.addEventListener("input", renderList);

// Kunden in Gruppe laden
async function loadSelectedKunden(gruppenId) {
    selected = [];
    renderSelected();
    renderList();

    const res = await fetch(`/api/kunden/${gruppenId}/gruppe`);
    const kundenInGruppe = await res.json();
    if (!kundenInGruppe || kundenInGruppe.length === 0) return;

    kundenInGruppe.forEach(k => selected.push(k));
    renderSelected();
    renderList();
}

// Initial Kunden laden
document.addEventListener("DOMContentLoaded", async () => {
    await loadKunden();
});


const neuTerminBtn = document.getElementById("neuTerminBtn");
const closeModal = fensterTerminAnpassen.querySelector(".close");

// Modal öffnen und Felder vorbelegen
neuTerminBtn.addEventListener("click", async () => {
    console.log("Neuer Termin für Gruppe ID:", form.id.value);
    gruppen_id = form.querySelector("#gruppenForm_id").value
    if (!gruppen_id) {
        alert("Bitte zuerst eine Gruppe auswählen!");
        return;
    }
    console.log("gruppen_id", gruppen_id)
    const response = await fetch(`/api/gruppen/${gruppen_id}`);
    if (!response.ok) {
        alert("Fehler beim Laden der Termine");
        return;
    }
    const termine = await response.json();

    beschreibung = "Gruppentherapie á " + termine.dauer_min + " min"
     openfensterTerminAnpassen({
                stundensatz: termine.standardbetrag || "",
                beschreibung: beschreibung || "",
                gruppeId: gruppen_id || ""
            });
    
    // Modal anzeigen
    fensterTerminAnpassen.style.display = "block";
});

// Modal schließen
closeModal.addEventListener("click", () => {
    fensterTerminAnpassen.style.display = "none";
});

// Modal schließen bei Klick außerhalb
window.addEventListener("click", (e) => {
    if (e.target === fensterTerminAnpassen) fensterTerminAnpassen.style.display = "none";
});

//für Tab Umschalten im Gruppenbereich
document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab");
    const contents = document.querySelectorAll(".tab-content");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            const content = document.getElementById(tab.dataset.tab);
            if (content) {
                content.classList.add("active");
            }
        });
    });
});

// Gruppen-Doku speichern
if (gruppenDokuSaveBtn) {
    gruppenDokuSaveBtn.addEventListener("click", async () => {
        const id = document.getElementById("gruppenForm_id").value;
        if (!id) {
            alert("Bitte zuerst eine Gruppe auswählen!");
            return;
        }
        showToast("Wird übertragen...", null);
        const doku = gruppenDokuText ? gruppenDokuText.value : "";

        try {
            const response = await fetch(`/api/gruppen/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ doku })
            });
            const data = await response.json();

            if (!data.success) {
                alert(data.error || "Fehler beim Speichern");
                return;
            }

            const row = document.querySelector(`#gruppentabelle tbody tr[data-id='${id}']`);
            if (row) {
                row.dataset.doku = doku;
            }
            showToast("Gespeichert!");
        } catch (err) {
            console.error("Fehler beim Speichern:", err);
            alert("Fehler beim Speichern. Siehe Konsole für Details.");
        }
    });
}

// Toast-Funktion für kurze Erfolgsmeldungen
function showToast(text = "Gespeichert!") {
    const toast = document.getElementById("toast");
    toast.textContent = text;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2000);
}