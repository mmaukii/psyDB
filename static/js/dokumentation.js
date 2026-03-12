// ===============================
// === GLOBALE VARIABLEN
// ===============================

let selected = {
  typ: null,   // "kunde" | "gruppe"
  id: null
};

let alleDokus = []; // alle Dokus des aktuell ausgewählten Kunden oder Gruppe
let auswahlDaten = [];

const auswahlTabelleBody = document.querySelector("#auswahlTabelle tbody");
const dokuListe = document.getElementById("dokuListe");
const searchInput = document.getElementById("search");

// ===============================
// === MODAL ELEMENTE REFERENZIEREN
// ===============================
const dokuModal = document.getElementById("fensterDoku"); // <- ID aus HTML
const dokuIdInput = document.getElementById("dokuId");
const dokuText = document.getElementById("dokuText");

// ===============================
// === INITIALISIERUNG
// ===============================

document.addEventListener("DOMContentLoaded", () => {
  ladeAuswahl();
});

// ===============================
// === AUSWAHL LADEN
// ===============================

async function ladeAuswahl() {
  try {
    const [kundenRes, gruppenRes] = await Promise.all([
      fetch("/api/kunden"),
      fetch("/api/gruppen")
    ]);

    const kunden = await kundenRes.json();
    const gruppen = await gruppenRes.json();

    auswahlDaten = [
      ...kunden.map(k => ({
        typ: "kunde",
        id: k.id,
        label: `${k.kuerzel} – ${k.nachname}`
      })),
      ...gruppen.map(g => ({
        typ: "gruppe",
        id: g.id,
        label: `${g.gruppenkuerzel} – ${g.gruppenname}`
      }))
    ];

    sortiereAuswahl(auswahlDaten);
    renderAuswahl(auswahlDaten);
    autoSelectKundeAusLocalStorage();


  } catch (err) {
    console.error("Fehler beim Laden der Auswahl:", err);
  }
}

// ===============================
// === SORTIERUNG
// ===============================

function sortiereAuswahl(daten) {
  daten.sort((a, b) => {
    if (a.typ !== b.typ) {
      return a.typ === "kunde" ? -1 : 1;
    }
    return a.label.localeCompare(b.label, "de", { sensitivity: "base" });
  });
}

// ===============================
// === RENDER
// ===============================

function renderAuswahl(daten) {
  auswahlTabelleBody.innerHTML = daten.map(item => `
    <tr data-typ="${item.typ}" data-id="${item.id}">
      <td>${item.typ === "kunde" ? "👤" : "👥"}</td>
      <td>${item.label}</td>
    </tr>
  `).join("");
}

function autoSelectKundeAusLocalStorage() {
  const selectedKundeId = localStorage.getItem("selectedKundeId");
  if (!selectedKundeId) return;

  const row = document.querySelector(
    `#auswahlTabelle tr[data-typ="kunde"][data-id="${selectedKundeId}"]`
  );

  if (row) {
    row.click(); // 🔥 triggert alles sauber
  }
}

// ===============================
// === KLICK AUF AUSWAHL
// ===============================

document.getElementById("auswahlTabelle")
  .addEventListener("click", e => {

    const row = e.target.closest("tr[data-typ]");
    if (!row) return;

    selected.typ = row.dataset.typ;
    selected.id = row.dataset.id;

    // ✅ NUR WENN KUNDE → merken
    if (selected.typ === "kunde") {
      localStorage.setItem("selectedKundeId", selected.id);
    }

    // Markierung
    document.querySelectorAll("#auswahlTabelle tr")
      .forEach(r => r.classList.remove("selected"));
    row.classList.add("selected");

    // Laden
    if (selected.typ === "kunde") {
      ladeDokusFuerKundenMitGruppen(selected.id);
    } else {
      ladeDokusFuerGruppe(selected.id);
    }
});

// ===============================
// === SUCHE
// ===============================

searchInput.addEventListener("input", () => {
  const term = searchInput.value.toLowerCase();

  const gefiltert = auswahlDaten.filter(item =>
    item.label.toLowerCase().includes(term)
  );

  renderAuswahl(gefiltert);
});

// ===============================
// === DOKU LADEN FÜR KUNDEN + GRUPPEN MIT NAMEN
// ===============================

async function ladeDokusFuerKundenMitGruppen(kundeId) {
  dokuListe.innerHTML = "<p>Lade Dokumentation…</p>";
  const filter = document.getElementById("DokuFilter")?.value;
  try {
    // 1️⃣ Kundendaten holen
    const resKunde = await fetch(`/api/kunden/${kundeId}`);
    if (!resKunde.ok) throw new Error("Fehler beim Laden des Kunden");
    const kunde = await resKunde.json(); // {id, vorname, nachname, kuerzel,...}

    // 2️⃣ Kundendokus
    const resTermine = await fetch(`/api/termine/kunde/${kundeId}`);
    if (!resTermine.ok) throw new Error("Fehler beim Laden der Termine");
    const kundenTermine = await resTermine.json();
    
    const kundenDokus = kundenTermine
      .filter(s => s.doku && s.doku.trim())
      .map(s => ({
        dokuId: s.id,
        termineId: s.id,
        gruppentermineId: "",
        doku: s.doku,
        pers_doku: s.pers_doku,
        datum: s.datum,
        anzeigeName: `${kunde.vorname} ${kunde.nachname}`,
        type: "kunde",
        abgesagt: s.abgesagt || false
      }));

    // 3️⃣ Kundengruppen
    const resGruppen = await fetch(`/api/kunden/${kundeId}/gruppen`);
    if (!resGruppen.ok) throw new Error("Fehler beim Laden der Gruppen");
    const kundenGruppen = await resGruppen.json(); // [{id, gruppenname, ...}, ...]

    let gruppenDokus = [];
    for (const gruppe of kundenGruppen) {
      const resGruppentermine = await fetch(`/api/gruppen/${gruppe.id}/termine`);
      if (!resGruppentermine.ok) continue;
      const termine = await resGruppentermine.json();

      console.log("Gruppentermine für Gruppe",termine);

      const mitDoku = termine
        .filter(s => s.doku && s.doku.trim())
        .map(s => ({
          dokuId: s.id,
          termineId: "",
          gruppentermineId: s.id,
          doku: s.doku,
          pers_doku: s.pers_doku,
          datum: s.datum,
          anzeigeName: gruppe.gruppenname,
          type: "gruppe",
          abgesagt: s.abgesagt || false
        }));

      gruppenDokus.push(...mitDoku);
    }

    // 4️⃣ Alle Dokus kombinieren und sortieren
    alleDokus = [...kundenDokus, ...gruppenDokus];
    alleDokus.sort((a, b) => b.datum.localeCompare(a.datum));

    if (!alleDokus.length) {
      dokuListe.innerHTML = "<p>Keine Dokumentation vorhanden.</p>";
      return;
    }
    console.log("filter",filter);
    // 5️⃣ Rendern
    dokuListe.innerHTML = alleDokus.map(d => `
      <div class="doku-item" data-id="${d.dokuId}">
        <div class="doku-header">
          <div class="doku-datum">${formatDatum(d.datum)} – ${escapeHtml(d.anzeigeName)}${d.abgesagt ? ' – Stunde vom Klienten abgesagt' : ''}</div>
          <button class="doku-edit-btn" data-id="${d.dokuId}"title="Datensatz editieren">✏️</button>
        </div>
        <div class="doku-text">
          ${
            filter === "allg"
              ? escapeHtml(d.doku || "")

              : filter === "pers"
                ? escapeHtml(d.pers_doku || "")

                : `
                    ${escapeHtml(d.doku || "")}
                    <br><br>
                    <span class="doku-trenner">*****</span>
                    <br><br>
                    ${escapeHtml(d.pers_doku || "")}
                  `
          }
        </div>
      </div>
    `).join("");

  } catch (err) {
    console.error(err);
    dokuListe.innerHTML = "<p>Fehler beim Laden der Dokumentation.</p>";
  }
}

// ===============================
// === DOKU LADEN FÜR GRUPPEN (nur für Gruppen-Auswahl)
// ===============================

async function ladeDokusFuerGruppe(gruppeId) {
  dokuListe.innerHTML = "<p>Lade Dokumentation…</p>";
  const filter = document.getElementById("DokuFilter")?.value;

  try {
    const resGruppe = await fetch(`/api/gruppen/${gruppeId}`);
    if (!resGruppe.ok) throw new Error("Fehler beim Laden der Gruppe");
    const gruppe = await resGruppe.json(); // {id, gruppenname, gruppenkuerzel,...}

    const resGruppentermine = await fetch(`/api/gruppen/${gruppeId}/termine`);
    if (!resGruppentermine.ok) throw new Error("Fehler beim Laden der Gruppentermine");
    const gruppentermine = await resGruppentermine.json();

    const mitDoku = gruppentermine
      .filter(s => s.doku && s.doku.trim())
      .map(s => ({
        dokuId: s.id,
        termineId: "",
        gruppentermineId: s.id,
        doku: s.doku,
        pers_doku: s.pers_doku,
        datum: s.datum,
        anzeigeName: gruppe.gruppenname,
        type: "gruppe"
      }))
      .sort((a, b) => b.datum.localeCompare(a.datum));

    alleDokus = mitDoku;

    if (!alleDokus.length) {
      dokuListe.innerHTML = "<p>Keine Dokumentation vorhanden.</p>";
      return;
    }

    dokuListe.innerHTML = alleDokus.map(d => `
      <div class="doku-item" data-id="${d.dokuId}">
        <div class="doku-header">
          <div class="doku-datum">${formatDatum(d.datum)} – ${escapeHtml(d.anzeigeName)}</div>
          <button class="doku-edit-btn" data-id="${d.dokuId}">✏️ Ändern</button>
        </div>
        <div class="doku-text">
          ${
            filter === "allg"
              ? escapeHtml(d.doku || "")

              : filter === "pers"
                ? escapeHtml(d.pers_doku || "")

                : `
                    ${escapeHtml(d.doku || "")}
                    <br><br>
                    <span class="doku-trenner">*****</span>
                    <br><br>
                    ${escapeHtml(d.pers_doku || "")}
                  `
          }
        </div>
      </div>
    `).join("");

  } catch (err) {
    console.error(err);
    dokuListe.innerHTML = "<p>Fehler beim Laden der Gruppen-Dokumentation.</p>";
  }
}

// ===============================
// === KLICK AUF ÄNDERN-BUTTON
// ===============================

dokuListe.addEventListener("click", e => {
  const btn = e.target.closest(".doku-edit-btn");
  if (!btn) return;

  const doku = alleDokus.find(d => d.dokuId == btn.dataset.id);
  if (!doku) return;

  console.log("Ändern-Button geklickt:", btn);
  console.log("Gefundene Doku:", doku);

  openFensterDoku({
            termineId: doku.termineId,
            gruppentermineId: doku.gruppentermineId,
            doku: doku.doku || "",
            pers_doku : doku.pers_doku || "",
        });
});

// ===============================
// === HELFER
// ===============================

function formatDatum(datum) {
  if (!datum) return "";
  const [y, m, d] = datum.split("-");
  return `${d}.${m}.${y}`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}



dokuForm.addEventListener("submit", async e => {
  e.preventDefault();

  const termineId = dokuForm.querySelector("#termineId").value;
  const gruppentermineId = dokuForm.querySelector("#gruppentermineId").value;
  const neuerText = dokuText.value;

  try {
    let url;
    let method = "PUT"; // oder PATCH, je nach API
    let body = { doku: neuerText };

    if (termineId) {
      url = `/api/termine/${termineId}`; // bestehender Kunden-Termine Endpunkt
    } else if (gruppentermineId) {
      url = `/api/gruppentermine/${gruppentermineId}`; // bestehender Gruppen-Termine Endpunkt
    } else {
      throw new Error("Keine gültige Termine-ID vorhanden");
    }

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    if (!res.ok) throw new Error("Fehler beim Speichern der Doku");

    // Modal schließen
    dokuModal.style.display = "none";

    // Dokus aktualisieren
    if (selected.typ === "kunde") {
      ladeDokusFuerKundenMitGruppen(selected.id);
    } else {
      ladeDokusFuerGruppe(selected.id);
    }

  } catch (err) {
    console.error("Fehler beim Speichern:", err);
    alert("Fehler beim Speichern der Doku. Siehe Konsole.");
  }
});

//akutaliserung bei Filterwechsel
document.getElementById("DokuFilter").addEventListener("change", () => {
  if (!selected.id) return;

  if (selected.typ === "kunde") {
    ladeDokusFuerKundenMitGruppen(selected.id);
  } else {
    ladeDokusFuerGruppe(selected.id);
  }
});
