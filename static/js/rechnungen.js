const RECHNUNG_UI_STATE_KEY = "rechnungUiState";

const termineproRechnungTabelle = document.getElementById("termineproRechnungTabelle")

// Hilfsfunktion: DD.MM.YYYY -> "YYYY-MM-DD"
function parseGermanDateToISO(dateStr) {
    if (!dateStr) return null;
    const parts = dateStr.split(".");
    const d = parts[0].padStart(2,"0");
    const m = parts[1].padStart(2,"0");
    const y = parts[2];
    return `${y}-${m}-${d}`;
}

// Deutsche Formatierung
const formatDE = (num) => {
    if (num === undefined || num === null) return "";
    return new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(num);
};


// Klick auf Rechnungzeile um Termine für Rechnung anzuzeigen


const rechnungsTabelle = document.getElementById("rechnungsTabelle").querySelector("tbody");
const termineproRechnungBody = document.getElementById("termineproRechnungBody");

rechnungsTabelle.addEventListener("click", async (e) => {
    const row = e.target.closest("tr[data-id]");
    if (!row) return;

    // 🔐 Auswahl speichern
    saveRechnungUIState(row.dataset.id);

    // Visuelle Markierung
    rechnungsTabelle.querySelectorAll("tr").forEach(r => r.classList.remove("selected"));
    row.classList.add("selected");
    // Termine laden
    try {
        const response = await fetch(`api/rechnungen/${row.dataset.id}/termine`); 
        if (!response.ok) throw new Error("Fehler beim Laden der Termine");
        const data = await response.json();

        // Status der ersten Spalte abfragen
        //const thFirst = termineproRechnungTabelle.querySelector("thead th:first-child");
        //const isHidden = thFirst.hidden;

        // Tabelle neu aufbauen
        if (data.termine.length === 0) {
            termineproRechnungBody.innerHTML = `<tr><td colspan="4">Keine Termine vorhanden.</td></tr>`;
        } else {
            termineproRechnungBody.innerHTML = data.termine.map(st => {
            // Datum umformatieren von YYYY-MM-DD → DD.MM.YYYY
            const datumParts = st.datum.split("-");
            const datumDeutsch = `${datumParts[2]}.${datumParts[1]}.${datumParts[0]}`;
            let betragNum = parseFloat(st.betrag);
            let betragFormatted = isNaN(betragNum) ? "" : betragNum.toFixed(2).replace(".", ",");

             const abgesagt = st.abgesagt && st.abgesagt !== "null" && st.abgesagt !== "0"; 
             const datumHtml = abgesagt
                ? `<s>${datumDeutsch}</s>` // <s> = durchgestrichen
                : datumDeutsch;

            return `
            <tr data-termine-id="${st.termine_id}">
              <th align="center">${datumHtml}</th>
              <td>${st.beschreibung}</td>
              <td align="right">${betragFormatted} €</td>
			     	</tr>
            `}).join("");
        }
            const datumParts = data.rechnung.datum.split("-");
            const datumDeutsch = `${datumParts[2]}.${datumParts[1]}.${datumParts[0]}`;
          // 2️⃣ Rechnungstexte setzen
        // Annahme: Dein Endpoint `/terminerechnung/<id>` liefert auch die Felder `rechnungTextOben` und `rechnungTextUnten`       
            document.getElementById("rechnungTextOben").value = data.rechnung.rechnungTextOben || "";
            document.getElementById("rechnungTextUnten").value = data.rechnung.rechnungTextUnten || "";
            document.getElementById("rechnungsnr").value = data.rechnung.rechnungsnr || "";
            document.getElementById("rechnungid").value = data.rechnung.id || "";
            document.getElementById("kommentar").value = data.rechnung.kommentar || "";
            document.getElementById("rechnungsdatum").value = datumDeutsch || "";
            document.getElementById("rechnungsdatumid").value = datumDeutsch || "";
        
    } catch (err) {
        console.error(err);
        termineproRechnungBody.innerHTML = `<tr><td colspan="4">Fehler beim Laden der Termine.</td></tr>`;
    }
    await ladeMahnungen(row.dataset.id);
});


function getCheckedTermine() {
    const rows = document.querySelectorAll("#termineproRechnungBody tr");
    const checkedIds = [];

    rows.forEach(row => {
        const checkbox = row.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked) {
            checkedIds.push(Number(row.dataset.termineId));
        }
    });

    return checkedIds;
}

document.getElementById("saveBtnRechnungTextRnr").addEventListener("click", async () => {

    // Rechnungsnummer aus dem Formular
    const rechnungsnr = document.getElementById("rechnungsnr").value.trim();
    // Rechnungsdaten laden (dataRn)
    const rechnungId = document.getElementById("rechnungid").value;
    const response1 = await fetch(`/api/rechnungen`); // Annahme: liefert alle Rechnungen als Array
    if (!response1.ok) throw new Error("Fehler beim Laden der Rechnungen");
    const dataRn = await response1.json();
    //console.log("Alle Rechnungen:", dataRn);
    //console.log("Aktuelle Rechnungsnummer:", rechnungsnr, "Aktuelle Rechnung ID:", rechnungId);

    // Prüfen, ob Rechnungsnummer schon vorhanden (außer für aktuelle Rechnung)
    const exists = dataRn.some(r => {
      const rnr = (r.rechnungsnr || "").toString().trim();
      const rid = (r.id || r.rechnung_id || "").toString();
      return rnr === rechnungsnr && rid !== rechnungId;
    });
    if (exists) {
      alert("Diese Rechnungsnummer ist bereits vergeben. Bitte wählen Sie eine andere Nummer.");
      return;
    }

    const data = {
        rechnungsnr: document.getElementById("rechnungsnr").value,
        rechnungTextOben: document.getElementById("rechnungTextOben").value,
        rechnungTextUnten: document.getElementById("rechnungTextUnten").value,
        rechnungId: document.getElementById("rechnungid").value,
        datum: parseGermanDateToISO(document.getElementById("rechnungsdatum").value),
        kommentar: document.getElementById("kommentar").value,
        termine: getCheckedTermine()  
    };

    // rechnungId ist bereits oben deklariert, keine erneute Zuweisung nötig

    const response = await fetch(`/api/rechnungen/${rechnungId}`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });

    if (response.ok) {
        showToast("Gespeichert!");
        // optional: Tabelle neu laden
        if (typeof ladeRechnungen === "function") {
            ladeRechnungen();
        }
    } else {
        alert("Fehler beim Speichern!");
    }
});

async function ladeRechnungen() {
  const response = await fetch('/api/rechnungen/mit-kunde');
  const rechnungen = await response.json();

  rechnungsTabelle.innerHTML = rechnungen.map(r => {
    // Datum umformatieren von YYYY-MM-DD → DD.MM.YYYY
    const datumParts = r.datum.split("-");
    const datumDeutsch = `${datumParts[2]}.${datumParts[1]}.${datumParts[0].slice(-2)}`;

    // Zahlungsziel (Tage)
    const zahlungsziel = parseInt(r.zahlungsziel_tage) || 0;
    // Neues Datum = Rechnungsdatum + Zahlungsziel
    const zielDatum = new Date(r.datum);
    zielDatum.setDate(zielDatum.getDate() + zahlungsziel);
    console.log("ZielDatum:", zielDatum);
    const heute = new Date();
    heute.setHours(0,0,0,0);
    const istUeberfaellig = zielDatum < heute;
    // Zahlungsziel-Datum aus zielDatum (einfacher)
    const zahlungsziel_datum = zielDatum.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });

    let betragNum = parseFloat(r.betrag);
    let betragFormatted = isNaN(betragNum) ? "" : new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(betragNum);

    return `
    <tr data-id="${r.rechnung_id}"${istUeberfaellig ? ' style="background:#d66767;"' : ''}>
      <th align="center"><span style="color:#000;">${r.rechnungsnr}</span></td>
      <td align="center">${r.kuerzel}</td>
      <td align="center">${r.vorname || ""}</td>
      <td align="center">${r.nachname || ""}</td>
      <td align="center">${datumDeutsch}</td>
      <td align="right">${betragFormatted} €</td>
      <td align="center">
        <span${istUeberfaellig ? ' style="text-decoration: underline double; font-weight: bold;"' : ''}>
          ${zahlungsziel_datum} (${r.zahlungsziel_tage || ''} d)
        </span>
      </td>
      <td>
        <select class="status-select" data-id="${r.rechnung_id}">
          <option value="0" ${r.bezahlt === 0 ? "selected" : ""}>offen</option>
          <option value="1" ${r.bezahlt === 1 ? "selected" : ""}>bezahlt</option>
        </select>
      </td>
      <td>
        <button class="mail-btn" data-id="${r.rechnung_id}"title="Rechnung per E-Mail senden">✉️</button>
        <button class="pdf-btn" data-id="${r.rechnung_id}"title="Rechnung als PDF herunterladen">🗂️</button>
        <button class="mahnung-btn" data-id="${r.rechnung_id}"title="Mahnung erstellen">🔔</button>
        <button class="delete-btn" data-id="${r.rechnung_id}"title="Datensatz löschen">🗑️</button>
      </td>
    </tr>
  `}).join("");

  // 🔹 Status ändern
  document.querySelectorAll('.status-select').forEach(select => {
    select.addEventListener('change', async (e) => {
      const id = e.target.dataset.id;
      const neuerStatus = e.target.value;

      await fetch(`api/rechnungen/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bezahlt: neuerStatus })
      });
    });
  });

  // 🔹 mail-Button
  document.querySelectorAll('.mail-btn').forEach(button => {
    button.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = button.dataset.id;

        fetch(`/api/rechnungen/mail/${id}`, { method: "GET" })
        .catch(err => console.error(err));
    });
  });

  // 🔹 pdf-Button
  document.querySelectorAll('.pdf-btn').forEach(button => {
    button.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = button.dataset.id;

        fetch(`/api/rechnungen/pdf/${id}`, { method: "GET" })
        .catch(err => console.error(err));
        window.open(`api/rechnungen/pdf/${id}`, "_blank");
    });
    
  });

  // 🔹 Löschen-Button (SEPARAT & STABIL)
  document.querySelectorAll('.delete-btn').forEach(button => {
    button.addEventListener('click', async (e) => {
      e.stopPropagation();

      const id = button.dataset.id; // ✅ korrekt
      if (!id) {
        console.error("Delete ohne ID");
        return;
      }

      if (!confirm("Diese Rechnung wirklich löschen?")) return;

      const response = await fetch(`/api/rechnungen/${id}`, {
        method: "DELETE"
      });

      if (response.ok) {
        showToast("Rechnung gelöscht!");
        ladeRechnungen();
        if (rechnungBereich?.reset) rechnungBereich.reset();
      } else {
        alert("Fehler beim Löschen!");
      }
    });
  });

  // ================================
  // 🔁 Auswahl wiederherstellen (RICHTIG)
  // ================================
  const saved = localStorage.getItem(RECHNUNG_UI_STATE_KEY);

  if (saved) {
      try {
          const { rechnungId, filterNr, filterKunde, filterStatus, filterVon, filterBis } = JSON.parse(saved);

          // Filterfelder setzen
          if (filterNr !== undefined) document.getElementById("filterRechnungsNr").value = filterNr;
          if (filterKunde !== undefined) document.getElementById("filterRechnungsKunde").value = filterKunde;
          if (filterStatus !== undefined) document.getElementById("filterRechnungsStatus").value = filterStatus;
          if (filterVon !== undefined) document.getElementById("RechnungsDatumVon").value = filterVon;
          if (filterBis !== undefined) document.getElementById("RechnungsDatumBis").value = filterBis;

          // Filter anwenden
          filterRechnungen();

          // Rechnung markieren
          if (rechnungId) {
              const row = rechnungsTabelle.querySelector(`tr[data-id="${rechnungId}"]`);
              if (row) {
                  row.click();
              }
          }

      } catch (e) {
          console.warn("Rechnungs-UI-State ungültig", e);
      }
  }
}

document.getElementById("filterRechnungsNr").addEventListener("input", () => { filterRechnungen(); saveRechnungUIState(document.getElementById("rechnungid").value); });
document.getElementById("filterRechnungsKunde").addEventListener("input", () => { filterRechnungen(); saveRechnungUIState(document.getElementById("rechnungid").value); });
document.getElementById("filterRechnungsStatus").addEventListener("input", () => { filterRechnungen(); saveRechnungUIState(document.getElementById("rechnungid").value); });
document.getElementById("RechnungsDatumVon").addEventListener("input", () => { filterRechnungen(); saveRechnungUIState(document.getElementById("rechnungid").value); });
document.getElementById("RechnungsDatumBis").addEventListener("input", () => { filterRechnungen(); saveRechnungUIState(document.getElementById("rechnungid").value); });




const mahnungenproRechnungBody = document.getElementById("mahnungenproRechnungBody");

async function ladeMahnungen(rechnungId) {
  try {
    const response = await fetch(`/api/rechnungen/${rechnungId}/mahnungen`);
    if (!response.ok) throw new Error("Fehler beim Laden der Mahnungen");
    const mahnungen = await response.json();
    if (mahnungen.length === 0) {
      mahnungenproRechnungBody.innerHTML = `<tr><td colspan="7">Keine Mahnungen vorhanden.</td></tr>`;
    } else {
      mahnungenproRechnungBody.innerHTML = mahnungen.map((m, index) => {
        // Datum
        const datumParts = m.datum ? m.datum.split("-") : ["", "", ""];
        const datumDeutsch = datumParts[2] ? `${datumParts[2]}.${datumParts[1]}.${datumParts[0]}` : "";
        // Zahlungsziel
        const zahlungsziel = parseInt(m.zahlungsziel_tage) || 0;
        const zielDatum = new Date(m.datum);
        zielDatum.setDate(zielDatum.getDate() + zahlungsziel);
        const heute = new Date();
        heute.setHours(0,0,0,0);
        const istUeberfaellig = zielDatum < heute;
        // Zahlungsziel-Datum aus zielDatum (einfacher)
        const zahlungsziel_datum = zielDatum.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' });
        // "wie vielte Mahnung": 1 = erste, 2 = zweite, ...
        const mahnungNr = index + 1;
        return `
          <tr data-mahnung-id="${m.id}"${istUeberfaellig ? ' style="background:#d66767;"' : ''}>
                <th align="center">${datumDeutsch}</th>
                 <td align="center">${m.mahnungsnr}</td>     
                <td contenteditable="true" class="kommentar-cell">${m.kommentar || ""}</td>
                <td align="center" contenteditable="true" class="verzugszinsen-cell">${formatDE(m.verzugszinsenProz) || ""}</td>
                <td align="center" contenteditable="true" class="mahnspesen-cell">${formatDE(m.mahnspesen) || ""} €</td>
                <td align="center" contenteditable="true" class="verzugszinsen-cell">${formatDE(m.verzugszinsen) || ""} €</td>
                <td align="center" contenteditable="true" >
                  <span${istUeberfaellig ? ' style="text-decoration: underline double; font-weight: bold;"' : ''}>
                    ${zahlungsziel_datum} (${m.zahlungsziel_tage|| ""} d)
                  </span>
                </td>
                <td>    
                <button class="mail-mahnung-btn" data-id="${m.id}" title="Mahnung per E-Mail senden">✉️</button>
                      <button class="pdf-mahnung-btn" data-id="${m.id}" title="Mahnung als PDF herunterladen">🗂️</button>
                      <button class="delete-mahnung-btn" data-id="${m.id}"title="Datensatz löschen">🗑️</button>
                  </td>
              </tr>
            `;
      }).join("");
    }
    // 🔹 Buttons einrichten

        // Mail
        document.querySelectorAll(".mail-mahnung-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                fetch(`/api/mahnungen/mail/${id}`, { method: "GET" })
                  .catch(err => console.error(err));
            });
        });

        // PDF
        document.querySelectorAll(".pdf-mahnung-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                window.open(`/api/mahnungen/pdf/${id}`, "_blank");
            });
        });

        // Löschen
        document.querySelectorAll(".delete-mahnung-btn").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                if (!confirm("Möchten Sie diese Mahnung wirklich löschen?")) return;

                const res = await fetch(`/api/mahnungen/${id}`, { method: "DELETE" });
                if (res.ok) {
                    showToast("Mahnung gelöscht!");
                    ladeMahnungen(rechnungId);
                } else {
                    alert("Fehler beim Löschen der Mahnung");
                }
            });
        });

  } catch (err) {
    console.error(err);
    mahnungenproRechnungBody.innerHTML = `<tr><td colspan="7">Fehler beim Laden der Mahnungen.</td></tr>`;
  }
}

function filterRechnungen() {
    const fNr = document.getElementById("filterRechnungsNr").value.toLowerCase();
    const fKunde = document.getElementById("filterRechnungsKunde").value.toLowerCase();
    const fStatusVal = document.getElementById("filterRechnungsStatus").value;
    const fStatus = fStatusVal === "" ? null : Number(fStatusVal);// Status als Zahl oder null, falls leer
    const fDateFromVal = document.getElementById("RechnungsDatumVon").value;
    const fDateToVal   = document.getElementById("RechnungsDatumBis").value;

    fromDate = fDateFromVal ? new Date(fDateFromVal).toISOString().slice(0,10) : null;
    toDate = fDateToVal ? new Date(fDateToVal).toISOString().slice(0,10) : null;



    rechnungsTabelle.querySelectorAll("tr").forEach(row => {
        const nr = row.cells[0].textContent.toLowerCase();
        const kunde = (
          row.cells[1].textContent + " " +
          row.cells[2].textContent + " " +
          row.cells[3].textContent
        ).toLowerCase();
        const rowDate = parseGermanDateToISO(row.cells[4].textContent.trim());

        // Status als Zahl
        const status = Number(row.cells[7].querySelector(".status-select").value);

        // Datumsfilter prüfen
        let dateMatch = true;
        if (fromDate && toDate) dateMatch = rowDate >= fromDate && rowDate <= toDate;
        else if (fromDate)      dateMatch = rowDate >= fromDate;
        else if (toDate)        dateMatch = rowDate <= toDate;

        // Status-Filter prüfen
        let statusMatch = fStatus === null ? true : status === fStatus;

        // Gesamtes Match
        const match =
            nr.includes(fNr) &&
            kunde.includes(fKunde) &&
            statusMatch &&
            dateMatch;

        row.style.display = match ? "" : "none";
    });
}



// Rechnungen beim Laden der Seite füllen
ladeRechnungen();

document.addEventListener("DOMContentLoaded", () => {
  const toggleButtonRechnung = document.getElementById("toggleButtonRechnung");
  const rechnungBereich = document.getElementById("rechnungBereich");

  toggleButtonRechnung.addEventListener("click", () => {
    // Button optisch toggeln
    toggleButtonRechnung.classList.toggle("active");

    const current = window.getComputedStyle(rechnungBereich).display;
    rechnungBereich.style.display = current === "none" ? "grid" : "none";
  });
});



// Optional: sicherstellen, dass DOMContentLoaded auch abgedeckt ist
document.addEventListener("DOMContentLoaded", () => {
    // vorhandener DOMContentLoaded-Code ...
    
    // Filter einmal anwenden, wenn Inputs schon Werte enthalten
    filterRechnungen();
});

// Mahnung-Button klicken
document.addEventListener("click", async function(e) {
  if (e.target.classList.contains("mahnung-btn")) {
    const rechnungId = e.target.dataset.id;

    // Abfrage, ob wirklich Mahnung erstellt werden soll
    if (!confirm("Möchten Sie wirklich eine Mahnung für diese Rechnung erstellen?")) return;

    // Prompt für Kommentar
    let kommentar = prompt("Kommentar für die Mahnung (optional):", "");
    if (kommentar === null) return; // Abbrechen


    try {
      // 1️⃣ Aktuelle Anzahl der Mahnungen für diese Rechnung abrufen
      const response = await fetch(`/api/rechnungen/${rechnungId}/mahnungen`);
      const mahnungen = await response.json();
      const neueMahnungNr = mahnungen.length + 1; // fortlaufend

      // 2️⃣ Mahnung erstellen
      const res = await fetch("/api/mahnungen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rechnung_id: rechnungId,
          datum: new Date().toISOString().split("T")[0],
          timestamp: new Date().toISOString(),
          kommentar: kommentar || "",
          mahnungsnr: neueMahnungNr // hier speichern
        })
      });

      const data = await res.json();

      if (data.success) {
        showToast(`Mahnung Nr. ${neueMahnungNr} erfolgreich erstellt!`);
        if (typeof ladeMahnungen === "function") {
          ladeMahnungen(rechnungId); // Tabelle aktualisieren
        }
      } else {
        alert("Fehler beim Erstellen der Mahnung");
      }

    } catch (err) {
      console.error(err);
      alert("Fehler beim Erstellen der Mahnung");
    }
  }
});


document.querySelectorAll('#mahnungenproRechnungBody td[contenteditable="true"]').forEach(cell => {
  cell.addEventListener('blur', async (e) => {
    const tr = e.target.closest('tr[data-mahnung-id]');
    const mahnungId = tr.dataset.mahnungId;

    const updatedData = {
      kommentar: tr.querySelector('.kommentar-cell')?.innerText || "",
      verzugszinsenProz: parseFloat(tr.querySelector('.verzugszinsen-cell')?.innerText) || 0,
      verzugszinsen: parseFloat(tr.querySelector('.verzugszinsen-cell')?.innerText) || 0,
      mahnspesen: parseFloat(tr.querySelector('.mahnspesen-cell')?.innerText) || 0
    };

    try {
      const res = await fetch(`/api/mahnungen/${mahnungId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedData)
      });

      if (!res.ok) {
        alert("Fehler beim Speichern der Mahnung");
      }
    } catch (err) {
      console.error(err);
      alert("Fehler beim Speichern der Mahnung");
    }
  });
});

// Helder für filter speichern 
function saveRechnungUIState(rechnungId) {
    const state = {
        rechnungId: rechnungId,
        filterNr: document.getElementById("filterRechnungsNr").value,
        filterKunde: document.getElementById("filterRechnungsKunde").value,
        filterStatus: document.getElementById("filterRechnungsStatus").value,
        filterVon: document.getElementById("RechnungsDatumVon").value,
        filterBis: document.getElementById("RechnungsDatumBis").value
    };
    localStorage.setItem(RECHNUNG_UI_STATE_KEY, JSON.stringify(state));
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