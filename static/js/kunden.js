// === LEISTUNGEN/THERAPIEFORMEN DYNAMISCH LADEN ===
async function ladeTherapieformenKunden() {
    const select = document.getElementById("therapieform");
    if (!select) return;
    select.innerHTML = '<option value="">– bitte wählen –</option>';
    try {
        const res = await fetch("/api/leistungen");
        if (!res.ok) throw new Error("Fehler beim Laden der Leistungen");
        const leistungen = await res.json();
        leistungen.filter(l => !l.gruppe).forEach(l => {
            // value: l.value, text: l.bezeichnung
            const opt = document.createElement("option");
            opt.value = l.value;
            opt.textContent = l.bezeichnung;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error("Fehler beim Laden der Leistungen:", err);
        // Fallback: Option anzeigen
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "(Leistungen nicht ladbar)";
        select.appendChild(opt);
    }
}

document.addEventListener('DOMContentLoaded', ladeTherapieformenKunden);
let selectedKundeId = localStorage.getItem("selectedKundeId");
let isInitialLoad = true; //damit neu laden Kunde erkannt wird und dann nicht autoamatisch regeloadet

const kundentabelle = document.getElementById("kundentabelle");
const termineProKundeListe = document.getElementById("termineProKundeListe");
const form = document.getElementById("kundenForm");
const search = document.getElementById("search");
const kundenDokuText = document.getElementById("kundenDokuText");
const kundenDokuSaveBtn = document.getElementById("kundenDokuSaveBtn");
const mailKundeBtn = document.getElementById("mailKundeBtn");
const kuerzelInput = document.getElementById("kuerzel");
let kuerzelInvalid = false;
let kuerzelInvalidValue = "";

if (mailKundeBtn) {
    mailKundeBtn.addEventListener("click", () => {
        const email = (form.email.value || "").trim();
        if (!email) {
            alert("Keine E-Mail-Adresse für den Kunden vorhanden.");
            return;
        }

        const subject = "Info";
        const body = "Guten Tag!\n\n";
        const mailto = `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        window.location.href = mailto;
    });
}

if (kuerzelInput) {
    kuerzelInput.addEventListener("input", () => {
        kuerzelInvalid = false;
        kuerzelInvalidValue = "";
    });

    kuerzelInput.addEventListener("focus", async () => {
        console.log("Kürzel Input Fokus - automatische Generierung prüfen");
        if (kuerzelInput.value.trim() !== "") return;
        // Prüfe Programmvariable
        let autoKuerzel = await ladeProgrammvariableNachName("auto_kuerzel_kunden");
        if (String(autoKuerzel) !== "1") return;

        // Hole Vorname und Nachname
        const vorname = (form.vorname.value || "").trim();
        const nachname = (form.nachname.value || "").trim();
        if (!vorname || !nachname) return;

        // Hilfsfunktion: ersten Konsonanten nach dem 1. Buchstaben
        function ersterKonsonant(str) {
            const VOKALE = "aeiouäöüAEIOUÄÖÜ";
            for (let i = 1; i < str.length; i++) {
                if (VOKALE.indexOf(str[i]) === -1 && /[a-zA-ZäöüÄÖÜ]/.test(str[i])) {
                    return str[i];
                }
            }
            return "";
        }
        let k = "";
        k += vorname[0] || "";
        k += ersterKonsonant(vorname) || "";
        k += nachname[0] || "";
        k += ersterKonsonant(nachname) || "";
        k = k.toUpperCase();

        // Hole alle bestehenden Kürzel aus der Kundentabelle
        const alleKuerzel = Array.from(document.querySelectorAll("#kundentabelle tbody tr"))
            .map(row => (row.dataset.kuerzel || "").toUpperCase());

        let kandidat = k;
        let nummer = 1;
        while (alleKuerzel.includes(kandidat)) {
            kandidat = k + nummer;
            nummer++;
        }
        kuerzelInput.value = kandidat;
    });

    kuerzelInput.addEventListener("blur", async () => {
        const kuerzel = (kuerzelInput.value || "").trim();
        if (!kuerzel) return;
        const original = (kuerzelInput.dataset.original || "").toLowerCase();
        if (kuerzel.toLowerCase() === original) return;
        if (kuerzelInvalid && kuerzel.toLowerCase() === kuerzelInvalidValue) {
            return;
        }

        try {
            const res = await fetch("/api/kunden");
            if (!res.ok) throw new Error("Fehler beim Laden der Kunden");
            const kunden = await res.json();
            const currentId = form.id.value ? String(form.id.value) : "";
            const kuerzelLower = kuerzel.toLowerCase();
            const exists = kunden.find(k => String(k.kuerzel || "").toLowerCase() === kuerzelLower && String(k.id) !== currentId);
            if (exists) {
                alert("Kürzel ist bereits vergeben!");
                kuerzelInvalid = true;
                kuerzelInvalidValue = kuerzelLower;
                kuerzelInput.focus();
                kuerzelInput.select();
            }
        } catch (err) {
            console.error(err);
        }
    });
}

///Bereich Kunden über filter Auswählen und Formualr verwalten
// Filterfunktion
search.addEventListener("input", () => {
    const term = search.value.toLowerCase();
    kundentabelle.querySelectorAll("tbody tr").forEach(row => {
        const kuerzel = row.dataset.kuerzel.toLowerCase();
        const nachname = row.dataset.nachname.toLowerCase(); // dataset muss vorhanden sein
        row.style.display = (kuerzel.includes(term) || nachname.includes(term)) ? "" : "none";
    });
});

// Klick auf Kundenzeile
kundentabelle.addEventListener("click", async (e) => {
    const row = e.target.closest("tr[data-id]");
    if (!row) return;
    
    const kundeId = row.dataset.id;

     // ✅ Gruppen des Kunden laden
    await ladeGruppenDesKunden(kundeId);

    // ✅ dauerhaft speichern
    localStorage.setItem("selectedKundeId", kundeId);
    console.log("Selected Kunde ID gespeichert:", kundeId);

    // Standort laden und Wert setzen
    const standortId = row.dataset.standort_id || "";
    await loadStandorteDropdown(standortId);

    // Druckvorlage laden und Wert setzen
    const druckvorlageId = row.dataset.druckvorlage_id || "";
    await loadDruckvorlagenDropdown(druckvorlageId);


    // Visuelle Markierung
    kundentabelle.querySelectorAll("tr").forEach(r => r.classList.remove("selected"));
    row.classList.add("selected");
    console.log("Kunde ausgewählt:", row.dataset.id);
    console.log("Kundendaten:", row.dataset);

    // Formular füllen
    form.id.value = row.dataset.id || "";
    form.nachname.value = row.dataset.nachname || "";
    form.vorname.value = row.dataset.vorname || "";
    form.email.value = row.dataset.email || "";
    form.adresse.value = row.dataset.adresse || "";
    form.plz.value = row.dataset.plz || "";
    form.ort.value = row.dataset.ort || "";
    form.kuerzel.value = row.dataset.kuerzel || "";
    if (kuerzelInput) {
        kuerzelInput.dataset.original = (row.dataset.kuerzel || "").toLowerCase();
    }
    form.stundensatz.value = row.dataset.stundensatz || "";
    form.dauer_min.value = row.dataset.dauer_min || "";
    form.standortKuerzel.value = standortId;
    form.druckvorlageId.value = druckvorlageId;
    form.geschlecht.value = row.dataset.geschlecht || "";
    form.therapieform.value = row.dataset.therapieform || "";
    form.gebdatum.value = row.dataset.gebdatum || "";
    form.ust.checked = row.dataset.ust === "1" || row.dataset.ust === "true";
    if (kundenDokuText) {
        kundenDokuText.value = row.dataset.doku || "";
    }
    form.rechnungTextObenVorgabe.value = row.dataset.rechnungtextobenvorgabe || "";
    form.rechnungTextUntenVorgabe.value = row.dataset.rechnungtextuntenvorgabe || "";
    form.aktiv.checked = row.dataset.aktiv === "1" || row.dataset.aktiv === "true";
    form.svnr.value = row.dataset.svnr || "";
    form.krankenkasse.value = row.dataset.krankenkasse || "";
    form.diagnose.value = row.dataset.diagnose || "";
    
    
    // Termine laden
    await reloadTermineFuerKunde(row.dataset.id);

});

//laden der Terminetabelle
async function reloadTermineFuerKunde(kundeId) {
    try {
        const response = await fetch(`/api/termine/kunde_rnr/${kundeId}`);
        if (!response.ok) throw new Error("Fehler beim Laden der Termine");
        
        const termine = await response.json();
        console.log("Geladene Termine für Kunde", kundeId, termine);
        if (termine.length === 0) {
            termineProKundeListe.innerHTML =
                `<tr><td colspan="6">Keine Termine vorhanden.</td></tr>`;
            return;
        }


        termineProKundeListe.innerHTML = termine.map(st => {
            // Datum formatieren
            const datumParts = st.datum.split("-");
            const datumDeutsch = `${datumParts[2]}.${datumParts[1]}.${datumParts[0]}`;

            // Betrag formatieren
            let betragNum = parseFloat(st.betrag);
            let betragFormatted = isNaN(betragNum) ? "" : new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(betragNum);

            // Zeitfelder in lokale Zeit umwandeln (Datum für Zeitzonen-Korrektheit berücksichtigen)
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

            // Buttons: je nach Status
            let buttons = "";
            if (st.abgesagt) {
                buttons = `<button class="restoreBtntermineproKunde table-btn" data-id="${st.id}" title="Termin wiederherstellen">📅↩️</button>`;
                buttons += `<button class="deleteBtntermineproKunde table-btn" data-id="${st.id}" title="Datensatz löschen">🗑️</button>`;
            } else {
                if (st.rechnungsnr) {
                    buttons = `<button class="dokuBtntermineproKunde table-btn" data-id="${st.id}" title="Doku Eintrag erstellen/bearbeiten">📚</button>`;
                } else {
                    buttons = `
                        <button class="editBtntermineproKunde table-btn" data-id="${st.id}" title="Datensatz editieren">🛠️</button>
                        <button class="dokuBtntermineproKunde table-btn" data-id="${st.id}" title="Doku Eintrag erstellen/bearbeiten">📚</button>
                        <button class="absageBtntermineproKunde table-btn" data-id="${st.id}" title="Ereignis absagen">🚫</button>
                        <button class="deleteBtntermineproKunde table-btn" data-id="${st.id}" title="Datensatz löschen">🗑️</button>
                    `;
                }
            }

            // Zeile zurückgeben, Klasse "abgesagt" setzen, optional display:none wenn Toggle aktiv
            const rowStyle = (st.abgesagt && toggleAbgesagtBtn.dataset.show === "false") ? "display:none;" : "";

            return `
                <tr data-id="${st.id}" class="${st.abgesagt ? 'abgesagt' : ''}" style="${rowStyle}">
                    <th align="center">${datumDeutsch}</th>
                    <td align="center">${localStart}</td>
                    <td align="center">${localEnd}</td>
                    <td>${st.beschreibung}</td>
                    <td align="right">${betragFormatted} €</td>
                    <td>${buttons}</td>
                </tr>
            `;
        }).join("");

        hideAbgesagteRows(); // falls Toggle aktiv
    } catch (err) {
        console.error(err);
        termineProKundeListe.innerHTML =
            `<tr><td colspan="6">Fehler beim Laden der Termine.</td></tr>`;
    }
}

//zeilen ein ausblenden
const toggleButton = document.getElementById("toggleButton");
const kundenBereich = document.getElementById("kundenBereich");

toggleButton.addEventListener("click", () => {
    const isHidden = kundenBereich.style.display === "none" || kundenBereich.style.display === "";

    if (isHidden) {
        // Bereich einblenden
        kundenBereich.style.display = "grid";
        toggleButton.classList.add("active"); // Rahmen aktiv
    } else {
        // Bereich ausblenden
        kundenBereich.style.display = "none";
        toggleButton.classList.remove("active"); // Rahmen weg
    }
});

// Neuer Kunde
document.getElementById("neuBtn").addEventListener("click", () => {
    localStorage.removeItem("selectedKundeId");

    form.reset();
    form.id.value = "";
    form.aktiv.checked = true;  // ⭐ aktiv standardmäßig anhaken
    if (kundenDokuText) {
        kundenDokuText.value = "";
    }
    if (kuerzelInput) {
        kuerzelInput.dataset.original = "";
    }

    // Standard-Standort automatisch vorwählen
    fetch('/api/standorte')
        .then(res => res.json())
        .then(standorte => {
            const standardStandort = standorte.find(s => s.standard);
            if (standardStandort) {
                const standortSelect = document.getElementById('standortKuerzel');
                if (standortSelect) standortSelect.value = standardStandort.id;
            }
        });

    // Standardtexte für Rechnung oben/unten aus Programmvariablen laden
    Promise.all([
        fetch('/api/programmvariablen/by-name/rechnung_text_oben').then(r => r.ok ? r.json() : {wert: ""}).catch(() => ({wert: ""})),
        fetch('/api/programmvariablen/by-name/rechnung_text_unten').then(r => r.ok ? r.json() : {wert: ""}).catch(() => ({wert: ""}))
    ]).then(([oben, unten]) => {
        if (form.rechnungTextObenVorgabe) form.rechnungTextObenVorgabe.value = oben.wert || "";
        if (form.rechnungTextUntenVorgabe) form.rechnungTextUntenVorgabe.value = unten.wert || "";
    });

    kundentabelle.querySelectorAll("tr").forEach(r => r.classList.remove("selected"));
    termineProKundeListe.innerHTML = "";

    // ✅ Kundenbereich einblenden
    kundenBereich.style.display = "grid";

    reloadKundenTabelle();
});


// Kunde löschen
document.getElementById("loeschenBtn").addEventListener("click", async () => {
    const id = form.id.value;
    if (!id) return alert("Kein Kunde ausgewählt.");

    // Auswahl-Dialog: Nur Kunde löschen oder auch alle Termine?
    // Dialog mit Buttons statt prompt
    const dialog = document.createElement("div");
    dialog.style.position = "fixed";
    dialog.style.left = "0";
    dialog.style.top = "0";
    dialog.style.width = "100vw";
    dialog.style.height = "100vh";
    dialog.style.background = "rgba(0,0,0,0.3)";
    dialog.style.display = "flex";
    dialog.style.alignItems = "center";
    dialog.style.justifyContent = "center";
    dialog.style.zIndex = 9999;

    dialog.innerHTML = `
        <div style="background:#fff;padding:2em;border-radius:8px;box-shadow:0 2px 12px #0002;max-width:90vw;">
            <div style="margin-bottom:1em;">
                <b>Wie möchten Sie fortfahren?</b><br>
                <small>Termine mitlöschen um auch Doku mitzulöschen. Wählen Sie eine Option</small>
            </div>
            <button id="kundeNurLoeschenBtn" style="margin-right:1em;">Nur Kunde löschen</button>
            <button id="kundeUndTermineLoeschenBtn" style="margin-right:1em;">Kunde und ALLE Termine löschen</button>
            <button id="abbrechenBtn">Abbrechen</button>
        </div>
    `;
    document.body.appendChild(dialog);

    // Promise für Auswahl
    const auswahl = await new Promise(resolve => {
        dialog.querySelector("#kundeNurLoeschenBtn").onclick = () => resolve("1");
        dialog.querySelector("#kundeUndTermineLoeschenBtn").onclick = () => resolve("2");
        dialog.querySelector("#abbrechenBtn").onclick = () => resolve(null);
    });

    dialog.remove();

    if (!auswahl) return; // Abbruch
    if (auswahl !== "1" && auswahl !== "2") {
        alert("Ungültige Eingabe. Vorgang abgebrochen.");
        return;
    }

    if (auswahl === "2") {
        // Alle Termine des Kunden löschen
        try {
            // Hole alle Termine für den Kunden
            const termineRes = await fetch(`/api/termine/kunde_rnr/${id}`);
            if (!termineRes.ok) throw new Error("Fehler beim Laden der Termine");
            const termine = await termineRes.json();
            showToast("Termin wird gelöscht", null );
            for (const termin of termine) {
                // Einzelnen Termin löschen
                
                await fetch(`/api/termine/${termin.id}`, { method: "DELETE" });
            }
        } catch (err) {
            alert("Fehler beim Löschen der Termine: " + err.message);
            return;
        }
    }

    
    showToast("Klient wird gelöscht", null );
    const response = await fetch(`/api/kunden/${id}`, { method: "DELETE" });

    if (!response.ok) {
        alert("Fehler beim Löschen");
        return;
    }
    //ui anpassen
    const row = kundentabelle.querySelector(`tr[data-id='${id}']`);
    if (row) row.remove();
    form.reset();
});



//Termine löschen mit button aus Tabelle Termine
const termineProKundeListeElement = document.getElementById("termineProKundeListe");
termineProKundeListeElement.addEventListener("click", async (e) => {
    //lösch Buttone gedrückt
    if (e.target.classList.contains("deleteBtntermineproKunde")) {
        const id = e.target.dataset.id;
        // Optional: Rückfrage zur Sicherheit
        if (!confirm("Soll dieser Eintrag wirklich gelöscht werden?")) return;

        try {
            const res =  await fetch(`api/termine/${id}`, { method: "DELETE" });
            if (res.ok) {
                e.target.closest("tr").remove(); // Zeile aus Tabelle löschen
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
    if (e.target.classList.contains("editBtntermineproKunde")) {
        //das skript sollte nach termineModal.js verschoben werden
        const id = e.target.dataset.id;
        console.log("Termin bearbeiten, ID:", id);
     
        const response = await fetch(`/api/termine/${id}`);
		if (!response.ok) throw new Error("Fehler beim Laden der Termine");
		const stunde = await response.json();
        console.log("Geladene Termin:", stunde);
        openfensterTerminAnpassen({
            stundensatz: stunde.betrag || "",
            beschreibung: stunde.beschreibung || "",
            datum: stunde.datum || "",
            utc_starttime: stunde.utc_starttime || "",
            utc_endtime: stunde.utc_endtime || "",
            stundeId: stunde.id || "",
            kundeId: id || "",
            therapieform: stunde.therapieform || "",
            ust: stunde.ust || "0",
            push_termin: 1,  // ✅ Push-Flag für das Backend
        });
        
        
    }


    if (e.target.classList.contains("absageBtntermineproKunde")) {
        const stundeId = e.target.dataset.id;
        // --- Doku-Eintrag abfragen ---
        let dokuText = prompt("Optional: Doku-Eintrag zur Absage hinzufügen (leer lassen für keinen Eintrag):", "");
        if (dokuText === null) return; // Abbruch

        // --- Fetch im Hintergrund ---
        fetch(`/api/termine/${stundeId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ abgesagt: 1, doku: dokuText })
        })
        .then(res => {
            if (!res.ok) throw new Error("Fehler beim Absagen");
            return res.text();
        })
        .then(result => {
            // Nach erfolgreicher Absage Tabelle neu laden, damit die Button-Logik korrekt ist
            const kundeId = document.getElementById("kundenForm").id.value;
            reloadTermineFuerKunde(kundeId);
        })
        .catch(err => {
            console.error(err);
            alert("Absage konnte nicht gespeichert werden!");
        });
    }
    // ===============================
    // 📚 DOKU BUTTON GEDRÜCKT
    // ===============================
    if (e.target.classList.contains("dokuBtntermineproKunde")) {
        const termineId = e.target.dataset.id;
        console.log("Doku Button gedrückt für Termin ID:", termineId);
        const res = await fetch(`/api/termine/${termineId}`);
        if (!res.ok) {
            alert("Fehler beim Laden der Doku!");
            return;
        }
         const stunde = await res.json();

        console.log("📚 Doku öffnen für Termin:", termineId);

        openFensterDoku({
            termineId,
            doku : stunde.doku || ""
        });
    }


        // Wiederherstellen-Button gedrückt
        if (e.target.classList.contains("restoreBtntermineproKunde")) {
            console.log("Termin wiederherstellen, ID:", e.target.dataset.id);
            const stundeId = e.target.dataset.id;
            if (!confirm("Soll dieser Termin wirklich wiederhergestellt werden?")) return;
            const row = e.target.closest("tr");
            // UI sofort anpassen
            row.classList.remove("abgesagt");
            // Fetch im Hintergrund
            try {
                const res = await fetch(`/api/termine/${stundeId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ abgesagt: null })
                });
                if (!res.ok) throw new Error("Fehler beim Wiederherstellen");
                // Toggle-Status für abgesagte Zeilen merken
                const showAbgesagte = toggleAbgesagtBtn.dataset.show;
                // Tabelle neu laden, damit Buttons und Status stimmen
                const kundeId = document.getElementById("kundenForm").id.value;
                await reloadTermineFuerKunde(kundeId);
                // Toggle-Status wiederherstellen
                toggleAbgesagtBtn.dataset.show = showAbgesagte;
                if (showAbgesagte === "true") {
                    toggleAbgesagtBtn.textContent = "Abgesagte ausblenden";
                    // Alle abgesagten Zeilen einblenden
                    document.querySelectorAll("#termineProKundeListe tr.abgesagt").forEach(row => {
                        row.style.display = "";
                    });
                } else {
                    toggleAbgesagtBtn.textContent = "Abgesagte anzeigen";
                    hideAbgesagteRows();
                }
            } catch (err) {
                alert("Fehler beim Wiederherstellen: " + err.message);
            }
        }
});

document.addEventListener("kalenderTermineAnpassung", function (e) {
    console.log("📅 Termin gespeichert, Kalender aktualisieren", e.detail);

    reloadTermineFuerKunde(document.getElementById("kundenForm").id.value); // einfach, zuverlässig
});


// Referenz auf Button holen
const toggleAbgesagtBtn = document.getElementById("toggleAbgesagtBtn");

// Startzustand: abgesagte Zeilen verstecken (auch bei dynamisch geladenen)
function hideAbgesagteRows() {
  document.querySelectorAll("#termineProKundeListe tr.abgesagt").forEach(row => {
    row.style.display = "none";
  });
  console.log("Abgesagte Zeilen ausgeblendet");
}
hideAbgesagteRows();

// Klick-Event für Toggle-Button
toggleAbgesagtBtn.addEventListener("click", () => {
  const currentlyShown = toggleAbgesagtBtn.dataset.show === "true";
  const rows = document.querySelectorAll("#termineProKundeListe tr.abgesagt");

  rows.forEach(row => {
    row.style.display = currentlyShown ? "none" : "";
  });

  toggleAbgesagtBtn.dataset.show = (!currentlyShown).toString();
  toggleAbgesagtBtn.textContent = currentlyShown
    ? "Abgesagte anzeigen"
    : "Abgesagte ausblenden";
});

// Falls Zeilen später dynamisch eingefügt werden → MutationObserver nutzen
const observer = new MutationObserver(() => {
  if (toggleAbgesagtBtn.dataset.show === "false") {
    hideAbgesagteRows();
  }
});
observer.observe(document.getElementById("termineProKundeListe"), { childList: true });

// Tab Umschalten im Kundenbereich
document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab");
    const contents = document.querySelectorAll(".tab-content");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            document.getElementById(tab.dataset.tab).classList.add("active");

            if (toggleAbgesagtBtn) {
                toggleAbgesagtBtn.style.display = tab.dataset.tab === "kunden-termine" ? "" : "none";
            }
        });
    });
});

// Kunden-Doku speichern
if (kundenDokuSaveBtn) {
    kundenDokuSaveBtn.addEventListener("click", async () => {
        const id = form.id.value;
        if (!id) {
            alert("Bitte zuerst einen Kunden auswählen!");
            return;
        }
        const doku = kundenDokuText ? kundenDokuText.value : "";

        try {
            const response = await fetch(`/api/kunden/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ doku })
            });
            const data = await response.json();

            if (!data.success) {
                alert(data.error || "Fehler beim Speichern");
                return;
            }

            const row = kundentabelle.querySelector(`tr[data-id='${id}']`);
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

function loadStandorteDropdown(selectedId = null) {
    const select = document.getElementById('standortKuerzel');
    select.innerHTML = '<option value="">-- bitte wählen --</option>';

    return fetch('/api/standorte')
        .then(res => res.json())
        .then(data => {
            data.forEach(s => {
                const option = document.createElement('option');
                option.value = s.id;       // ID speichern
                option.textContent = s.kuerzel; 
                select.appendChild(option);
            });

            if (selectedId) {
                select.value = selectedId; // Wert direkt setzen
            }
        })
        .catch(err => console.error('Fehler beim Laden der Standorte:', err));
}

function loadDruckvorlagenDropdown(selectedId = null) {
    const select = document.getElementById('druckvorlageId');
    if (!select) return Promise.resolve();

    select.innerHTML = '<option value="">-- bitte wählen --</option>';

    return fetch('/api/druckvorlagen')
        .then(res => res.json())
        .then(data => {
            data.forEach(v => {
                const option = document.createElement('option');
                option.value = v.id;
                option.textContent = v.name || v.pfad || `Vorlage ${v.id}`;
                select.appendChild(option);
            });

            if (selectedId) {
                select.value = selectedId;
            }
        })
        .catch(err => console.error('Fehler beim Laden der Druckvorlagen:', err));
}
const kundenForm = document.getElementById("kundenForm");
const saveBtn = document.getElementById("saveBtn");

if (saveBtn) {
    saveBtn.addEventListener("click", (e) => {
        e.preventDefault();
        if (kundenForm) {
            kundenForm.requestSubmit();
        }
    });
}

kundenForm.addEventListener("submit", async (e) => {
    e.preventDefault(); // Page reload verhindern

    const formData = new FormData(kundenForm);
    const jsonData = Object.fromEntries(formData.entries());
    // Zusätzliche Felder explizit übernehmen (falls nicht automatisch enthalten)
    jsonData.svnr = kundenForm.querySelector('[name="svnr"]').value || "";
    jsonData.krankenkasse = kundenForm.querySelector('[name="krankenkasse"]').value || "";
    jsonData.diagnose = kundenForm.querySelector('[name="diagnose"]').value || "";

    // Checkbox-Felder prüfen
    jsonData.aktiv = kundenForm.querySelector('[name="aktiv"]').checked ? "1" : "0";
    jsonData.ust = kundenForm.querySelector('[name="ust"]').checked ? "1" : "0";

    // Pflichtfelder prüfen
    const requiredFields = ["nachname", "kuerzel", "standort_id", "therapieform"];
    const missingFields = requiredFields.filter(f => !jsonData[f] || jsonData[f].trim() === "");
    if (missingFields.length > 0) {
        alert("Bitte folgende Pflichtfelder ausfüllen: " + missingFields.join(", "));
        return;
    }

    // Gruppen übernehmen
    const ausgewaehlteGruppenIds = ausgewaehlteGruppen.map(g => g.id);

    // Prüfen, ob es ein bestehender Kunde ist
    const id = formData.get("id");
    const method = id ? "PUT" : "POST";
    const url = id ? `/api/kunden/${id}` : "/api/kunden";

    // stundensatz formatieren
    if (jsonData.stundensatz) {
        jsonData.stundensatz = parseFloat(jsonData.stundensatz.replace(/\./g, "").replace(",", "."));
    }

    try {
        // 1️⃣ Kunde speichern / anlegen

        // Wiederherstellen-Button gedrückt
        if (e.target.classList.contains("restoreBtntermineproKunde")) {
            console.log("Termin wiederherstellen, ID:", e.target.dataset.id);
            const stundeId = e.target.dataset.id;
            if (!confirm("Soll dieser Termin wirklich wiederhergestellt werden?")) return;
            const row = e.target.closest("tr");
            // UI sofort anpassen
            row.classList.remove("abgesagt");
            // Fetch im Hintergrund
            try {
                const res = await fetch(`/api/termine/${stundeId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ abgesagt: null })
                });
                if (!res.ok) throw new Error("Fehler beim Wiederherstellen");
                // Tabelle neu laden, damit Buttons und Status stimmen
                const kundeId = document.getElementById("kundenForm").id.value;
                await reloadTermineFuerKunde(kundeId);
            } catch (err) {
                alert("Fehler beim Wiederherstellen: " + err.message);
            }
        }
        const response = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(jsonData)
        });
        const data = await response.json();

        if (!data.success) {
            alert(data.error || "Fehler beim Speichern");
            return;
        }

        const kundeId = id || data.id; // Wenn neu angelegt, ID aus Antwort

        // 2️⃣ Gruppen aktualisieren (nur wenn Kunde existiert)
        console.log("Ausgewählte Gruppen IDs:", ausgewaehlteGruppenIds);
        //if (ausgewaehlteGruppenIds.length > 0) {
            await fetch(`/api/kunden/${kundeId}/gruppen`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ gruppen_ids: ausgewaehlteGruppenIds })
            });
        //}

        await reloadKundenTabelle();
        showToast("Gespeichert!");
    } catch (err) {
        console.error("Fehler beim Speichern:", err);
        alert("Fehler beim Speichern. Siehe Konsole für Details.");
    }
});




document.getElementById("kundenAktivFilter").addEventListener("change", () => {
    ersteZeileAusgewaehlt = false; // optional
    reloadKundenTabelle();
});

let ersteZeileAusgewaehlt = false; // Flag, um nur einmal auszuwählen

async function reloadKundenTabelle() {
    const filter = document.getElementById("kundenAktivFilter").value;

    let url;
    switch (filter) {
        case "aktiv":
            url = "/api/kunden/aktiv";
            break;
        case "inaktiv":
            url = "/api/kunden/inaktiv";
            break;
        case "alle":
        default:
            url = "/api/kunden";
    }

    const res = await fetch(url);
    const kunden = await res.json();
    console.log("Geladene Kunden:", kunden);
    // Sortieren nach Kürzel alphabetisch
    kunden.sort((a, b) => {
        const kuerzelA = a.kuerzel.toLowerCase();
        const kuerzelB = b.kuerzel.toLowerCase();
        if (kuerzelA < kuerzelB) return -1;
        if (kuerzelA > kuerzelB) return 1;
        return 0;
    });

    const tbody = document.querySelector("#kundentabelle tbody");
    tbody.innerHTML = kunden.map(k => {
    // stundensatz formatieren
    let stundensatzNum = parseFloat(k.stundensatz);
    let stundensatzFormatted = isNaN(stundensatzNum) ? "" : new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(stundensatzNum);

    return `
        <tr
            data-id="${k.id}"
            data-nachname="${k.nachname}"
            data-vorname="${k.vorname}"
            data-email="${k.email}"
            data-adresse="${k.adresse}"
            data-plz="${k.plz}"
            data-ort="${k.ort}"
            data-stundensatz="${stundensatzFormatted}"
            data-dauer_min="${k.dauer_min || ''}"
            data-kuerzel="${k.kuerzel}"
            data-geschlecht="${k.geschlecht}"
            data-therapieform="${k.therapieform}"
            data-gebdatum="${k.gebdatum}"
            data-ust="${k.ust}"
            data-standort_id="${k.standort_id}"
            data-doku="${k.doku}"
            data-rechnungTextObenVorgabe="${k.rechnungTextObenVorgabe}"
            data-rechnungTextUntenVorgabe="${k.rechnungTextUntenVorgabe}"
            data-aktiv="${k.aktiv}"
            data-druckvorlage_id="${k.druckvorlage_id || ''}"
            data-svnr="${k.svnr || ''}"
            data-krankenkasse="${k.krankenkasse || ''}"
            data-diagnose="${k.diagnose || ''}" >  
            <td>${k.kuerzel}</td>
        </tr>
    `}).join("");

    // --- Kunde nach Reload automatisch auswählen ---
    const selectedKundeId = localStorage.getItem("selectedKundeId");

    let rowToSelect = null;

    // Nur wenn gespeicherte ID existiert
    if (selectedKundeId) {
        rowToSelect = tbody.querySelector(`tr[data-id="${selectedKundeId}"]`);
    }

    // Fallback NUR beim ersten Laden der Seite
    if (!rowToSelect && isInitialLoad) {
        rowToSelect = tbody.querySelector("tr[data-id]");
    }

    // Klick nur wenn wir wirklich was haben
    if (rowToSelect) {
        rowToSelect.click();
    }

    // nach erstem Durchlauf: kein Initial Load mehr
    isInitialLoad = false;

    }

// Aufruf beim initialen Laden
document.addEventListener('DOMContentLoaded', () => {
    kundenBereich.style.display = "none";
    loadStandorteDropdown();
    loadDruckvorlagenDropdown();
    reloadKundenTabelle();
});

async function ladeKunde(id) {
    const response = await fetch(`/api/kunden/${id}`);
    const k = await response.json();
    console.log("Geladener Kunde:", k);


    kundenForm.nachname.value = k.nachname || "";
    kundenForm.vorname.value = k.vorname || "";
    kundenForm.email.value = k.email || "";
    form.rechnungTextObenVorgabe.value = row.dataset.rechnungtextobenvorgabe || "";
    form.rechnungTextUntenVorgabe.value = row.dataset.rechnungtextuntenvorgabe || "";
    if (kundenDokuText) {
        kundenDokuText.value = k.doku || "";
    }
}



function showToast(text = "Gespeichert!", anchorElement = null, type = "info") {
    const toast = document.getElementById("toast");
    toast.textContent = text;
    toast.classList.remove("toast-warn");
    if (type === "warn") {
        toast.classList.add("toast-warn");
    }
    toast.classList.add("show");

    // Positionieren, falls ein Anker-Element übergeben wurde
    if (anchorElement) {
        const rect = anchorElement.getBoundingClientRect();
        toast.style.position = "fixed";
        toast.style.left = `${rect.left + window.scrollX}px`;
        toast.style.top = `${rect.top + window.scrollY - toast.offsetHeight - 8}px`;
        toast.style.zIndex = 2000;
    } else {
        toast.style.position = "";
        toast.style.left = "";
        toast.style.top = "";
        toast.style.zIndex = "";
    }

    const duration = type === "warn" ? 4000 : 2000;
    setTimeout(() => {
        toast.classList.remove("show");
        // Nach Ausblenden zurücksetzen
        setTimeout(() => {
            if (anchorElement) {
                toast.style.position = "";
                toast.style.left = "";
                toast.style.top = "";
                toast.style.zIndex = "";
            }
            toast.classList.remove("toast-warn");
        }, 300);
    }, duration);
}


async function ladeProgrammvariableNachName(name) {
    const res = await fetch(`api/programmvariablen/by-name/${name}`);
    const data = await res.json();
    return data.wert;
}

// Neuer Termin Button
neuTerminBtn.addEventListener("click", async () => {
    if (!form.id.value) {
        alert("Bitte zuerst einen Kunden auswählen!");
        return;
    }

    const id = form.id.value;
    const res = await fetch(`/api/kunden/${id}`);
    const kunde = await res.json();

    let beschreibung = "";
    // Beachte: kunde.therapieform kann als String ("1") oder Zahl (1) kommen
    switch (String(kunde.therapieform)) {
        case "1": {
            const dauer = await ladeProgrammvariableNachName("einzel_zeit");
            beschreibung = "Einzeltherapie á " + dauer + " min";
            break;
        }
        case "2": {
            const dauer = await ladeProgrammvariableNachName("paar_zeit");
            beschreibung = "Paartherapie á " + dauer + " min";
            break;
        }
        case "3": {
            const dauer = await ladeProgrammvariableNachName("familie_zeit");
            beschreibung = "Familientherapie á " + dauer + " min";
            break;
        }
        case "4": {
            const dauer = await ladeProgrammvariableNachName("gruppe_zeit");
            beschreibung = "Gruppentherapie á " + dauer + " min";
            break;
        }
        case "5": {
            const dauer = await ladeProgrammvariableNachName("einzelsupervision_zeit");
            beschreibung = "Einzelsupervision á " + dauer + " min";
            break;
        }
        case "6": {
            const dauer = await ladeProgrammvariableNachName("gruppensupervision_zeit");
            beschreibung = "Gruppensupervision á " + dauer + " min";
            break;
        }
        case "7": {
            const dauer = await ladeProgrammvariableNachName("einzelselbesterfahrung_zeit");
            beschreibung = "Einzelselbsterfahrung á " + dauer + " min";
            break;
        }
        case "8": {
            const dauer = await ladeProgrammvariableNachName("gruppenselbsterfahrung_zeit");
            beschreibung = "Gruppenselbsterfahrung á " + dauer + " min";
            break;
        }
        case "9": {
            const dauer = await ladeProgrammvariableNachName("coaching_zeit");
            beschreibung = "Coaching á " + dauer + " min";
            break;
        }
        case "10": {
            beschreibung = "Vortrag/Seminar/Workshop";
            break;
        }
        default:
            beschreibung = "";
    }

    openfensterTerminAnpassen({
        kundeId: id,
        stundensatz: kunde.stundensatz || "",
        beschreibung,
        therapieform: kunde.therapieform || "",
        ust: kunde.ust || "0"
    });
});

// ===============================
// === HELFER: TABELLE ===
// ===============================
function renderOderUpdateZeile(stunde) {
    if (!termineListe) return;
    console.log("renderOderUpdateZeile für Termin:", stunde.id);
    console.log(termineListe);

    const html = `
        <tr data-id="${stunde.id}">
            <td>${stunde.datum || ""}</td>
            <td>${stunde.utc_starttime || ""}</td>
            <td>${stunde.utc_endtime || ""}</td>
            <td>${stunde.beschreibung || ""}</td>
            <td>${stunde.betrag || ""}</td>
            <td>
                <button class="editBtntermineproKunde table-btn" data-id="${stunde.id}" title="Datensatz editieren">🛠️</button>
                <button class="deleteBtntermineproKunde table-btn" data-id="${stunde.id}" title="Datensatz löschen">🗑️</button>
                <button class="absageBtntermineproKunde table-btn" data-id="${stunde.id}" title="Ereignis absagen">🚫</button>
                <button class="dokuBtntermineproKunde table-btn" data-id="${st.id}" title="Doku Eintrag erstellen/bearbeiten">📚</button>
            </td>
        </tr>
    `;

    const row = termineListe.querySelector(`tr[data-id="${stunde.id}"]`);
    row ? row.outerHTML = html : termineListe.insertAdjacentHTML("beforeend", html);
}

async function ladeGruppenDesKunden(kundeId) {
	const res = await fetch(`api/kunden/${kundeId}/gruppen`);
	const gruppen = await res.json();

	document.getElementById("gruppenTags").innerHTML = "";
	ausgewaehlteGruppen = [];

	gruppen.forEach(addGruppe);
}

let ausgewaehlteGruppen = [];
let alleGruppen = []; // alle Gruppen aus Backend

// Tags anzeigen
function addGruppe(gruppe) {
	if (ausgewaehlteGruppen.some(g => g.id === gruppe.id)) return;

	ausgewaehlteGruppen.push(gruppe);

	const tag = document.createElement("span");
	tag.className = "tag";

	// Tag-Content mit optionalem Betrag
	tag.innerHTML = `
		${gruppe.gruppenkuerzel}<button type="button">✕</button>
	`;

	// ❌ Button
	tag.querySelector("button").onclick = () => {
		ausgewaehlteGruppen = ausgewaehlteGruppen.filter(g => g.id !== gruppe.id);
		tag.remove();
	};

	// Betrag editierbar
	const betragInput = tag.querySelector(".tag-betrag");
	if (betragInput) {
		betragInput.addEventListener("input", (e) => {
			gruppe.betrag = parseFloat(e.target.value) || 0;
		});
	}

	document.getElementById("gruppenTags").appendChild(tag);
}

// Autovervollständigung
const input = document.getElementById("gruppenInput");
const suggestions = document.getElementById("gruppenSuggestions");

let selectedIndex = -1; // für Keyboard Navigation

// Input Event
input.addEventListener("input", () => {
	const value = input.value.toLowerCase().trim();
	suggestions.innerHTML = "";
	selectedIndex = -1;

	if (!value) return;

	// Filter passende Gruppen
	const matches = alleGruppen.filter(g =>
		g.gruppenname.toLowerCase().includes(value) ||
		g.gruppenkuerzel.toLowerCase().includes(value)
	);

	// Liste erstellen
	matches.forEach((g, i) => {
		const li = document.createElement("li");
		li.textContent = `${g.gruppenname} (${g.gruppenkuerzel})`;
		li.dataset.id = g.id;

		li.addEventListener("click", () => {
			addGruppe(g);
			input.value = "";
			suggestions.innerHTML = "";
		});

		suggestions.appendChild(li);
	});
});

// Keyboard Navigation
input.addEventListener("keydown", (e) => {
	const items = suggestions.querySelectorAll("li");
	if (!items.length) return;

	if (e.key === "ArrowDown") {
		selectedIndex = (selectedIndex + 1) % items.length;
		updateActive(items);
		e.preventDefault();
	} else if (e.key === "ArrowUp") {
		selectedIndex = (selectedIndex - 1 + items.length) % items.length;
		updateActive(items);
		e.preventDefault();
	} else if (e.key === "Enter") {
		if (selectedIndex >= 0) {
			const g = alleGruppen.find(g => g.id == items[selectedIndex].dataset.id);
			addGruppe(g);
			input.value = "";
			suggestions.innerHTML = "";
			e.preventDefault();
		}
	}
});

function updateActive(items) {
	items.forEach((li, i) => li.classList.toggle("active", i === selectedIndex));
}

// Click außerhalb schließt Dropdown
document.addEventListener("click", (e) => {
	if (!input.contains(e.target) && !suggestions.contains(e.target)) {
		suggestions.innerHTML = "";
	}
});

// Gruppen vom Backend laden (Autocomplete)
async function ladeAlleGruppen() {
	const res = await fetch("api/gruppen"); // dein Endpoint
	alleGruppen = await res.json();
}
ladeAlleGruppen();

// Gruppen eines Kunden laden
async function ladeGruppenDesKunden(kundeId) {
	const res = await fetch(`api/kunden/${kundeId}/gruppen`);
	const gruppen = await res.json();

	document.getElementById("gruppenTags").innerHTML = "";
	ausgewaehlteGruppen = [];

	gruppen.forEach(addGruppe);
}

//Stundensatz bei neue Kunden nach Auswahl therapieform automatisch befüllen
async function ladeProgrammvariableNachName(name) {
    const res = await fetch(`api/programmvariablen/by-name/${name}`);
    const data = await res.json();
    return data.wert;
}

document.addEventListener("change", async function (e) {
    if (e.target.id === "therapieform") {
        const stundensatzInput = document.getElementById("stundensatz");
        const dauerInput = document.getElementById("dauer_min");
        if (!stundensatzInput && !dauerInput) return;

        // Hole die Leistungen und suche die passende
        try {
            const res = await fetch("/api/leistungen");
            if (!res.ok) throw new Error("Fehler beim Laden der Leistungen");
            const leistungen = await res.json();
            const leistung = leistungen.find(l => String(l.value) === String(e.target.value));
            if (!leistung) return;
            const standardWert = leistung.betrag;
            const standardDauer = leistung.dauer_min;
            console.log(leistungen)
            console.log("Standardwert für ausgewählte Therapieform:", standardWert);
            console.log("Standarddauer für ausgewählte Therapieform:", standardDauer);

            // === Stundensatz ===
            if (stundensatzInput) {
                const currentValue = (stundensatzInput.value || "").trim();
                if (!currentValue) {
                    stundensatzInput.value = standardWert;
                } else {
                    const normalizeNumber = (val) => {
                        const n = parseFloat(String(val).replace(",", "."));
                        return Number.isFinite(n) ? n : null;
                    };
                    const currentNum = normalizeNumber(currentValue);
                    const standardNum = normalizeNumber(standardWert);
                    const isDifferent = (currentNum !== null && standardNum !== null)
                        ? currentNum !== standardNum
                        : currentValue !== String(standardWert);
                    if (isDifferent) {
                        let therapieText = leistung.bezeichnung || "dieser";
                        if (confirm(`Der eingegebene Betrag (${currentValue}) weicht vom Standardbetrag für ${therapieText} (${standardWert}) ab. Soll der Standardbetrag übernommen werden?`)) {
                            stundensatzInput.value = standardWert;
                        }
                    }
                }
            }

            // === Dauer ===
            if (dauerInput) {
                const currentDauer = (dauerInput.value || "").trim();
                if (!currentDauer) {
                    dauerInput.value = standardDauer;
                } else {
                    const normalizeNumber = (val) => {
                        const n = parseInt(String(val).replace(/\D/g, ""), 10);
                        return Number.isFinite(n) ? n : null;
                    };
                    const currentNum = normalizeNumber(currentDauer);
                    const standardNum = normalizeNumber(standardDauer);
                    const isDifferent = (currentNum !== null && standardNum !== null)
                        ? currentNum !== standardNum
                        : currentDauer !== String(standardDauer);
                    if (isDifferent) {
                        let therapieText = leistung.bezeichnung || "dieser";
                        if (confirm(`Die eingegebene Dauer (${currentDauer}) weicht von der Standarddauer für ${therapieText} (${standardDauer}) ab. Soll die Standarddauer übernommen werden?`)) {
                            dauerInput.value = standardDauer;
                        }
                    }
                }
            }
        } catch (err) {
            console.error("Fehler beim Laden der Leistungen für Standardbetrag und Dauer:", err);
        }
    }
});
