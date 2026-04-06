const FILTER_STATE_KEY = "offeneTermineFilter";
const SELECTED_STUNDEN_KEY = "selectedTermineIds";

document.addEventListener("DOMContentLoaded", () => {
    restoreFilterState();
    ladeTermine();
});

//offene Termine Tabelle

const offeneTermineTabelle = document.getElementById("offeneTermineTabelle").querySelector("tbody");



// Beispiel: Daten vom Server holen
async function ladeTermine() {
    const response = await fetch('/api/termine/aktive-kunde-nicht-in-rechnung'); // sollte JSON mit allen Termine + Kundendaten liefern
    const termine = await response.json();
    console.log("Geladene Termine:", termine);

    offeneTermineTabelle.innerHTML = termine.map(st => {
        // Datum umformatieren von YYYY-MM-DD → DD.MM.YYYY
            const datumParts = st.datum.split("-");
            const datumDeutsch = `${datumParts[2]}.${datumParts[1]}.${datumParts[0]}`;
            let betragNum = parseFloat(st.betrag);
            let betragFormatted = isNaN(betragNum) ? "" : new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(betragNum);
            
            const abgesagt = st.abgesagt && st.abgesagt !== "null" && st.abgesagt !== "0";
            const datumHtml = abgesagt
                ? `<s>${datumDeutsch}</s>` // <s> = durchgestrichen
                : datumDeutsch;

            return `
            <tr data-termine-id="${st.id}">
                <td><input type="checkbox" class="selectRow" data-termine-id="${st.id}"></td>
                <th align="center">${datumHtml}</th>            
                <td>${st.vorname}</td>
                <td>${st.nachname}</td>
                <td>${st.kuerzel}</td>
                <td align="center">${st.utc_starttime}</td>
                <td align="center">${st.utc_endtime}</td>
                <td>${st.beschreibung}</td>
                <td>${st.gruppenkuerzel}</td>
                <td align="right">${betragFormatted}&nbsp;€</td>
                <td>
                    <button class="editBtn table-btn" data-id="${st.id}" title="Datensatz editieren">🛠️</button>
                    <button class="deleteBtn table-btn" data-id="${st.id}" title="Datensatz löschen">🗑️</button>
                </td> 
                <td hidden>${st.abgesagt}</td> 
                <td hidden>${st.ust}</td> 
                <td hidden>${st.kundeId}</td>    
            </tr>
    `;
        }).join("");
        filterTabelle(); // Tabelle nach dem Laden filtern
}


//offene Termine Eventlistener für Lösch-Buttons (Event Delegation)
offeneTermineTabelle.addEventListener("click", async (e) => {
    if (e.target.classList.contains("deleteBtn")) {
    const id = e.target.dataset.id;
    if (!confirm("Soll dieser Eintrag wirklich gelöscht werden?")) return;

    try {
        const res = await fetch(`api/termine/${id}`, { method: "DELETE" });
        if (res.ok) {
            e.target.closest("tr").remove();
            console.log(`🗑️ Termin ${id} gelöscht`);
        } else {
            alert("Fehler beim Löschen!");
        }
    } catch (err) {
        console.error("Fehler:", err);
        alert("Verbindung fehlgeschlagen.");
    }
}

    //ändern Buttone gedrückt
    if (e.target.classList.contains("editBtn")) {
        const id = e.target.dataset.id;

        const response = await fetch(`/api/termine/${id}`);
        if (!response.ok) throw new Error("Fehler beim Laden der Termine");
        const stunde = await response.json();
        console.log("stunde", stunde)


        openfensterTerminAnpassen({
                stundensatz: stunde.betrag || "",
                beschreibung: stunde.beschreibung || "",
                datum: stunde.datum || "",
                utc_starttime: stunde.utc_starttime || "",
                utc_endtime: stunde.utc_endtime || "",
                stundeId: stunde.id || "",
                kundeId: stunde.kunde_id || ""
            });
    }

    if (e.target.classList.contains("absageBtn")) {
        const stundeId = e.target.dataset.id;

        try {
            const response = await fetch(`/api/termine/${stundeId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    abgesagt: 1,
                    push_termin: 1  // ✅ Push-Flag für das Backend
                 }) // nur abgesagt setzen
            });

            if (!response.ok) {
                throw new Error("Fehler beim Absagen der Termin");
            }

            const result = await response.text();
            console.log(result);

            // Optional: Button deaktivieren oder UI aktualisieren
            e.target.disabled = true;
            e.target.textContent = "Abgesagt";
        } catch (error) {
            console.error(error);
            alert("Konnte die Termin nicht absagen.");
        }
    }

});

// Seite laden
ladeTermine();

// Filterauswahl speichern
function saveFilterState() {
    const state = {
        vorname: document.getElementById("filterVorname").value,
        nachname: document.getElementById("filterNachname").value,
        kuerzel: document.getElementById("filterKuerzel").value,
        gruppe: document.getElementById("filterGruppe").value,
        status: document.getElementById("filterTermineStatus").value,
        von: document.getElementById("RechnungsDatumVon").value,
        bis: document.getElementById("RechnungsDatumBis").value
    };
    localStorage.setItem(FILTER_STATE_KEY, JSON.stringify(state));
}

function restoreFilterState() {
    const raw = localStorage.getItem(FILTER_STATE_KEY);
    if (!raw) return;

    const state = JSON.parse(raw);
    document.getElementById("filterVorname").value = state.vorname || "";
    document.getElementById("filterNachname").value = state.nachname || "";
    document.getElementById("filterKuerzel").value = state.kuerzel || "";
    document.getElementById("filterGruppe").value = state.gruppe || "";
    document.getElementById("filterTermineStatus").value = state.status ?? "";
    document.getElementById("RechnungsDatumVon").value = state.von || "";
    document.getElementById("RechnungsDatumBis").value = state.bis || "";
}

//tabelle nach Änderung über festensterTermineanpassen neu lande
document.addEventListener("kalenderTermineAnpassung", function (e) {
    ladeTermine();
});

// Filterfunktionen
function filterTabelle() {
    const fVorname = document.getElementById("filterVorname").value.toLowerCase();
    const fNachname = document.getElementById("filterNachname").value.toLowerCase();
    const fKuerzel = document.getElementById("filterKuerzel").value.toLowerCase();
    const fGruppe = document.getElementById("filterGruppe").value.toLowerCase();

    const fStatusVal = document.getElementById("filterTermineStatus").value;
    const fStatus = fStatusVal === "" ? null : Number(fStatusVal);

    const fDateFromVal = document.getElementById("RechnungsDatumVon").value;
    const fDateToVal   = document.getElementById("RechnungsDatumBis").value;

    const fromDate = fDateFromVal ? new Date(fDateFromVal).toISOString().slice(0,10) : null;
    const toDate   = fDateToVal   ? new Date(fDateToVal).toISOString().slice(0,10) : null;

    function parseGermanDateToISO(dateStr) {
        if (!dateStr) return null;
        const [d,m,y] = dateStr.split(".");
        return `${y}-${m.padStart(2,"0")}-${d.padStart(2,"0")}`;
    }

    offeneTermineTabelle.querySelectorAll("tr").forEach(row => {
        const rowDate  = parseGermanDateToISO(row.cells[1].textContent.trim());
        const vorname  = row.cells[2].textContent.toLowerCase();
        const nachname = row.cells[3].textContent.toLowerCase();
        const kuerzel  = row.cells[4].textContent.toLowerCase();
        const gruppe   = row.cells[8].textContent.toLowerCase();

        // 👉 abgesagt-Spalte (Index ggf. anpassen!)
        const abgesagtText = row.cells[11].textContent.trim().toLowerCase();

        const istAbgesagt =
            abgesagtText !== "" &&
            abgesagtText !== "null" &&
            abgesagtText !== "0";


        // Datumsfilter
        let dateMatch = true;
        if (fromDate && toDate) dateMatch = rowDate >= fromDate && rowDate <= toDate;
        else if (fromDate)      dateMatch = rowDate >= fromDate;
        else if (toDate)        dateMatch = rowDate <= toDate;

        // Statusfilter
        let statusMatch = true;
        if (fStatus !== null) {
            statusMatch = fStatus === 1 ? istAbgesagt : !istAbgesagt;
        }

        const visible =
            vorname.includes(fVorname) &&
            nachname.includes(fNachname) &&
            kuerzel.includes(fKuerzel) &&
            gruppe.includes(fGruppe) &&
            dateMatch &&
            statusMatch;

        row.style.display = visible ? "" : "none";
        if (!visible) {
            const cb = row.querySelector(".selectRow");
            if (cb) cb.checked = false;
        }
    });
    saveSelectedTermine();
}


// Event Listener für Filter
document.getElementById("filterVorname").addEventListener("input", () => {
    saveFilterState();
    filterTabelle();
});
document.getElementById("filterNachname").addEventListener("input", () => {
    saveFilterState();
    filterTabelle();
});
document.getElementById("filterKuerzel").addEventListener("input", () => {
    saveFilterState();
    filterTabelle();
});
document.getElementById("filterGruppe").addEventListener("input", () => {
    saveFilterState();
    filterTabelle();
});
document.getElementById("RechnungsDatumVon").addEventListener("input", () => {
    saveFilterState();
    filterTabelle();
});
document.getElementById("RechnungsDatumBis").addEventListener("input", () => {
    saveFilterState();
    filterTabelle();
});
document.getElementById("filterTermineStatus").addEventListener("change", () => {
    saveFilterState();
    filterTabelle();
});



// Filterzustand beim Laden wiederherstellen
function saveSelectedTermine() {
    const ids = [];
    document.querySelectorAll('.selectRow:checked').forEach(cb => {
        ids.push(cb.dataset.termineId);
    });
    localStorage.setItem(SELECTED_STUNDEN_KEY, JSON.stringify(ids));
}

function restoreSelectedTermine() {
    const raw = localStorage.getItem(SELECTED_STUNDEN_KEY);
    if (!raw) return;

    const ids = JSON.parse(raw);
    document.querySelectorAll(".selectRow").forEach(cb => {
        cb.checked = ids.includes(cb.dataset.termineId);
    });
}

offeneTermineTabelle.addEventListener("click", (e) => {
    if (e.target.classList.contains("selectRow")) {
        saveSelectedTermine();
    }
});

// Checkbox „Alle auswählen“
// Select All Checkbox
const selectAll = document.getElementById("selectAllTermine");

selectAll.addEventListener("change", () => {
    const checked = selectAll.checked;
    offeneTermineTabelle.querySelectorAll("tr").forEach(row => {
        if (row.style.display === "none") return;
        const cb = row.querySelector(".selectRow");
        if (cb) cb.checked = checked;
    });
    saveSelectedTermine();
});



// Event Delegation für Checkboxen in der Tabelle
offeneTermineTabelle.addEventListener("click", (e) => {
    if (e.target.classList.contains("selectRow")) {
        console.log("Checkbox geändert:", e.target.dataset.termineId, e.target.checked);
    }
});

// Select All Event
selectAll.addEventListener("change", () => {
    const checked = selectAll.checked;
    offeneTermineTabelle.querySelectorAll("tr").forEach(row => {
        if (row.style.display === "none") return;
        const cb = row.querySelector(".selectRow");
        if (cb) cb.checked = checked;
    });
});

// Tabelle beim Laden füllen
ladeTermine();


// Funktion zum Sammeln aller ausgewählten Termine-IDs
function getSelectedTermineIds() {
    const selectedIds = [];
    document.querySelectorAll('#offeneTermineTabelle tbody input[type="checkbox"]:checked').forEach(cb => {
        const row = cb.closest("tr");
        if (row && row.style.display === "none") return;
        selectedIds.push(cb.dataset.termineId);
    });
    console.log(selectedIds)
    return selectedIds;
}

// rechnung erstellen
document.getElementById('getSelectedButton').addEventListener('click', () => {
    const selectedIds = [];
    document.querySelectorAll('#offeneTermineTabelle tbody input[type="checkbox"]:checked').forEach(cb => {
        selectedIds.push(cb.dataset.termineId);
    });
    console.log("Ausgewählte Termine-IDs:", selectedIds);

    // Prüfen, ob alle Termine pro Kunde den gleichen ust-Wert haben
    // Map: kundeId -> { ust: Set, ids: [] }
    const kundeMap = {};
    selectedIds.forEach(id => {
        const row = document.querySelector(`#offeneTermineTabelle tr[data-termine-id="${id}"]`);
        if (!row) return;
        const kundeId = row.cells[13] ? row.cells[13].textContent.trim() : null;
        const ust = row.cells[12] ? row.cells[12].textContent.trim() : null;
        console.log(`Termin ${id}: KundeID=${kundeId}, USt=${ust}`);
        if (!kundeId) return;
        if (!kundeMap[kundeId]) {
            kundeMap[kundeId] = { ustSet: new Set(), ids: [] };
        }
        kundeMap[kundeId].ustSet.add(ust);
        kundeMap[kundeId].ids.push(id);
    });

    // IDs, die entfernt werden müssen (wegen unterschiedlicher ust pro Kunde)
    let removedIds = [];
    Object.entries(kundeMap).forEach(([kundeId, obj]) => {
        if (obj.ustSet.size > 1) {
            // Mehrere unterschiedliche ust-Werte für diesen Kunden
            removedIds = removedIds.concat(obj.ids);
        }
    });

    let filteredIds = selectedIds.filter(id => !removedIds.includes(id));
    if (removedIds.length > 0) {
        // Kundenkürzel der betroffenen Kunden sammeln
        const kundeKuerzel = Object.entries(kundeMap)
            .filter(([_, obj]) => obj.ustSet.size > 1)
            .map(([kundeId, _]) => {
            // Suche das erste Vorkommen in der Tabelle, um das Kürzel zu holen
            const row = document.querySelector(`#offeneTermineTabelle tr[data-termine-id="${kundeMap[kundeId].ids[0]}"]`);
            return row ? row.cells[4].textContent.trim() : kundeId;
            });

        alert(
            "Achtung: Für mindestens einen Kunden wurden Termine mit unterschiedlichen USt-Werten ausgewählt. Diese Termine werden von der Rechnungsstellung ausgeschlossen.\n\nBetroffene Kunden: " +
            kundeKuerzel.join(", ")
        );
        // Optional: Checkboxen für entfernte Termine abwählen
        removedIds.forEach(id => {
            const cb = document.querySelector(`#offeneTermineTabelle input.selectRow[data-termine-id="${id}"]`);
            if (cb) cb.checked = false;
        });
    }

    if (filteredIds.length === 0) {
        alert("Keine gültigen Termine für die Rechnungsstellung ausgewählt.");
        return;
    }

    // POST-Request an Flask senden
    const formData = new FormData();
    filteredIds.forEach(id => formData.append("termine_ids[]", id));
    console.log("FormData zum Senden:", Array.from(formData.entries()));

    fetch('/api/rechnungen/aus-termine', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'   // ❗ extrem wichtig
            },
            body: JSON.stringify({
                termine_ids: filteredIds
            })
        })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Rechnungsnummern und IDs extrahieren
            const rechnungsNrs = data.rechnungen.map(r => r.rechnungsnr);
            const rechnungsIds = data.rechnungen.map(r => r.rechnung_id);
            console.log("Neue Rechnungsnummern vom Server:", rechnungsNrs);
            alert(`Neue Rechnungen erstellt! Nummern: ${rechnungsNrs.join(", ")}`);

            // Offene Termine aktualisieren und Auswahl zurücksetzen
            ladeTermine();
            localStorage.removeItem(SELECTED_STUNDEN_KEY);
            document.querySelectorAll(".selectRow").forEach(cb => cb.checked = false);
            document.getElementById("selectAllTermine").checked = false;

            // Für jede neue Rechnungs-ID die PDF erzeugen
            rechnungsIds.forEach(id => {
                fetch(`/api/rechnungen/mail/${id}`, { method: "GET" })
                    .then(resp => {
                        if (!resp.ok) {
                            console.error(`Fehler bei PDF für Rechnung ${id} (Status: ${resp.status})`);
                        } else {
                            console.log(`PDF erfolgreich für Rechnung ${id} erstellt`);
                        }
                    })
                    .catch(err => console.error(`Fetch-Fehler für Rechnung ${id}:`, err));
            });

        } else {
            // Fehler z.B. keine Druckvorlage
            alert(data.error || "Fehler beim Erstellen der Rechnung.");
            console.error("Fehler beim Erstellen der Rechnung:", data.error);
        }
    })
    .catch(err => console.error("Fetch-Fehler beim Erstellen der Rechnung:", err));
});

// ================================
// FILTER ZURÜCKSETZEN
// ================================
document.getElementById("filterLeeren").addEventListener("click", () => {
    console.log("Filter wird zurückgesetzt");

    // Textfilter
    document.getElementById("filterVorname").value = "";
    document.getElementById("filterNachname").value = "";
    document.getElementById("filterKuerzel").value = "";
    document.getElementById("filterGruppe").value = "";

    // Statusfilter
    document.getElementById("filterTermineStatus").value = "";

    // Datumsfilter
    document.getElementById("RechnungsDatumVon").value = "";
    document.getElementById("RechnungsDatumBis").value = "";

    // LocalStorage löschen
    localStorage.removeItem(FILTER_STATE_KEY);

    // OPTIONAL: Checkbox-Auswahl zurücksetzen (empfohlen)
    localStorage.removeItem(SELECTED_STUNDEN_KEY);
    document.querySelectorAll(".selectRow").forEach(cb => cb.checked = false);
    document.getElementById("selectAllTermine").checked = false;

    // Tabelle neu filtern
    filterTabelle();
});