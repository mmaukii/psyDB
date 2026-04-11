// === LEISTUNGEN/THERAPIEFORMEN DYNAMISCH LADEN ===
async function ladeTherapieformen() {
    const select = document.getElementById("terminTherapieform");
    if (!select) return;
    select.innerHTML = '<option value="">– bitte wählen –</option>';
    try {
        const res = await fetch("/api/leistungen");
        if (!res.ok) throw new Error("Fehler beim Laden der Leistungen");
        const leistungen = await res.json();
        leistungen.forEach(l => {
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
// ===============================
// === TERMIN MODAL (ZENTRAL) ===
// ===============================
// console.log("definiere openNeufensterermineanpassen");
const fenstertermineanpassen = document.getElementById("fensterTerminAnpassen");
const terminForm  = document.getElementById("terminForm");
//const closeBtn    = fenstertermineanpassen?.querySelector(".close");
const termineListe = document.getElementById("termineProKundeListe");

// 🔧 Flags um zu verhindern, dass Listener mehrfach hinzugefügt werden
let endzeitListenerInitialized = false;

// ===============================
// === GLOBALE MODAL API ===
// ===============================



// 🔓 Öffnen (neu oder bearbeiten)
// neue fensterTermineAnpassenfunktionen
window.openfensterTerminAnpassen = async function ({
    kundeId="",
    gruppeId="",
    stundeId ="",
    stundensatz = "",
    beschreibung = "",
    datum = "",
    startzeit = "",
    endzeit = "",
    therapieform = "",
    ust = "0"
}) {


    terminForm.reset();
    await ladeTherapieformen();
    // console.log("🆕 Neuer Termin für Kunde:", kundeId);

    if (datum === "") {
        // 📅 Datum: heute + 6 Tage
        const heute = new Date();
        heute.setDate(heute.getDate() + 6);
        datum = heute.toISOString().split("T")[0];
    }
    document.getElementById("datum").value = datum;


    if (startzeit === "") {
        // ⏰ Startzeit: aktuelle Stunde abgerundet
        const jetzt = new Date();
        document.getElementById("startzeit").value = `${String(jetzt.getHours()).padStart(2, "0")}:00`;
    } else {
        document.getElementById("startzeit").value = startzeit;
    }

    if (endzeit !== "") {
        document.getElementById("endzeit").value = endzeit;
    } else {
        berechneEndzeit(); // Automatische Berechnung
    }

    if (stundeId){ //wenn Termin zum verändern geklickt
        let response;
        // console.log("Vorhandener Termin geklickt")

        if (gruppeId) {
            response = await fetch(`/api/gruppentermine/${stundeId}`);
        } else {
            response = await fetch(`/api/termine/${stundeId}`);
        }

        if (!response.ok) throw new Error("Fehler beim Laden der Termine");

        const termin = await response.json();
        // console.log("Termindaten: ", termin);
        beschreibung = termin.beschreibung;
        betrag = termin.betrag
        therapieform = termin.therapieform;
        ust = termin.ust;
        console.log("Termindaten geladen für ID:", termin);
        // console.log("🆕 Neuer Termin für Kunde:", kundeId);
        console.log("Beschreibung aus DB:", beschreibung);
        console.log("therapieform aus DB:", therapieform);
        console.log("ust aus DB:", ust);
    }


    // 💰 stundensatz (Priorität: Übergabe > Kunde > leer)
    document.getElementById("betrag").value =new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(stundensatz)|| "";

    // 📚 Beschreibung (Priorität: Übergabe > leer)
    document.getElementById("beschreibung").value =beschreibung || "";

    // 📚 Termin ID (Priorität: Übergabe > leer)
    document.getElementById("terminId").value =  stundeId || "";

    // 🆔 Kunde ID (nur bei neu )
    document.getElementById("kundeId").value = kundeId || "";

    // 🆔 Gruppe ID (nur bei neu )
    document.getElementById("gruppeId").value = gruppeId || "";

    document.getElementById("terminTherapieform").value = therapieform || "";

    document.getElementById("terminUst").checked = ust === 1 ? true : false;

    // 🔓 Modal öffnen
    fenstertermineanpassen.style.display = "block";

    // Serientermin-Ebene immer ausblenden beim Öffnen
    const serieOptions = document.getElementById("serieOptions");
    if (serieOptions) {
        serieOptions.style.display = "none";
        // Optional: Checkbox zurücksetzen
        const istSerieCheckbox = document.getElementById("istSerie");
        if (istSerieCheckbox) istSerieCheckbox.checked = false;
    }

    
    // 🕐 Listener für automatische Endzeit-Berechnung (nur einmal setzen)
    if (!endzeitListenerInitialized) {
        const startzeitInput = document.getElementById("startzeit");
        const beschreibungInput = document.getElementById("beschreibung");
        
        if (startzeitInput) {
            startzeitInput.addEventListener("change", berechneEndzeit);
            startzeitInput.addEventListener("input", berechneEndzeit);
        }
        
        if (beschreibungInput) {
            beschreibungInput.addEventListener("change", berechneEndzeit);
            beschreibungInput.addEventListener("input", berechneEndzeit);
        }
        
        endzeitListenerInitialized = true;
    }

    // Ein-/Ausblenden der Buttons je nach stundeId
    const deleteBtn = document.getElementById("deleteTerminBtn");
    const absageBtn = document.getElementById("absageTerminBtn");

    if (stundeId) {
        if (deleteBtn) deleteBtn.style.display = "inline-block";
        if (absageBtn) absageBtn.style.display = "inline-block";
        // 🚫 Serientermine nur bei neuen Terminen
        document.getElementById("serieSection").style.display = "none";
    } else {
        if (deleteBtn) deleteBtn.style.display = "none";
        if (absageBtn) absageBtn.style.display = "none";
        // ✅ Serientermine nur bei neuen Terminen anzeigen
        document.getElementById("serieSection").style.display = "block";
        // Serientermin-Listener setzen
        setupSerieListener();
    }

};



// 🔒 Schließen
window.closefenstertermineanpassen = function () {
    fenstertermineanpassen.style.display = "none";
};

// ⏱️ Endzeit automatisch berechnen
function berechneEndzeit() {
    const startzeitInput = document.getElementById("startzeit");
    const endzeitInput = document.getElementById("endzeit");
    const beschreibungInput = document.getElementById("beschreibung");
    const dauerMinInput = document.getElementById("dauer_min");

    if (!startzeitInput || !endzeitInput || !startzeitInput.value) return;

    const startzeit = startzeitInput.value;
    const beschreibung = beschreibungInput?.value || "";

    // Dauer zuerst aus dem Feld dauer_min nehmen, falls vorhanden und gültig
    let dauerMinuten = 50; // Default Einzeltherapie
    if (dauerMinInput && dauerMinInput.value && !isNaN(parseInt(dauerMinInput.value))) {
        dauerMinuten = parseInt(dauerMinInput.value);
    } else if (beschreibung.includes("Paartherapie") || beschreibung.includes("Paar")) {
        dauerMinuten = 90;
    } else if (beschreibung.includes("Gruppentherapie") || beschreibung.includes("Gruppe")) {
        // Dauer wird aus der Beschreibung extrahiert, z.B. "Gruppentherapie á 60 min"
        const match = beschreibung.match(/(\d+)\s*min/);
        if (match) {
            dauerMinuten = parseInt(match[1]);
        } else {
            dauerMinuten = 60; // Default für Gruppe
        }
    }

    const [stunden, minuten] = startzeit.split(":").map(Number);
    const ende = new Date();
    ende.setHours(stunden);
    ende.setMinutes(minuten + dauerMinuten);

    const endeStr = `${String(ende.getHours()).padStart(2,"0")}:${String(ende.getMinutes()).padStart(2,"0")}`;
    endzeitInput.value = endeStr;
}



// ===============================
// === SERIENTERMINE ===
// ===============================
function setupSerieListener() {
    const istSerieCheckbox = document.getElementById("istSerie");
    const serieOptions = document.getElementById("serieOptions");
    const datumInput = document.getElementById("datum");
    const serieIntervallInput = document.getElementById("serieIntervall");
    const serieAnzahlInput = document.getElementById("serieAnzahl");
    const enddatumDisplay = document.getElementById("enddatumDisplay");

    function updateEnddatum() {
        const startDatum = datumInput.value;
        const intervall = parseInt(serieIntervallInput.value) || 1;
        const anzahl = parseInt(serieAnzahlInput.value) || 1;

        if (!startDatum) {
            enddatumDisplay.textContent = "-";
            return;
        }

        const start = new Date(startDatum);
        const end = new Date(start);
        // Berechne: (anzahl - 1) * intervall Wochen
        end.setDate(end.getDate() + ((anzahl - 1) * intervall * 7));

        const enddatumFormatted = end.toLocaleDateString("de-DE");
        enddatumDisplay.textContent = enddatumFormatted;
    }

    istSerieCheckbox.addEventListener("change", () => {
        serieOptions.style.display = istSerieCheckbox.checked ? "block" : "none";
        if (istSerieCheckbox.checked) {
            updateEnddatum();
        }
    });

    datumInput.addEventListener("change", updateEnddatum);
    serieIntervallInput.addEventListener("change", updateEnddatum);
    serieIntervallInput.addEventListener("input", updateEnddatum);
    serieAnzahlInput.addEventListener("change", updateEnddatum);
    serieAnzahlInput.addEventListener("input", updateEnddatum);
}
// ===============================
// === MODAL EVENTS ===
// ===============================

document.addEventListener('DOMContentLoaded', () => {
    const popup = document.getElementById("fensterTerminAnpassen");
    if (!popup) return;

    const closeBtn = popup.querySelector(".close");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            popup.style.display = "none";
        });
    }

    // 🖱️ DRAG & DROP Funktionalität für Modal
    const modalHeader = document.getElementById("modalHeader");
    const modalContent = document.getElementById("modalContent");
    
    if (modalHeader) {
        let isDragging = false;
        let offsetX = 0;
        let offsetY = 0;

        modalHeader.addEventListener("mousedown", (e) => {
            isDragging = true;
            const rect = modalContent.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            modalHeader.style.opacity = "0.8";
        });

        document.addEventListener("mousemove", (e) => {
            if (isDragging) {
                modalContent.style.position = "fixed";
                modalContent.style.left = (e.clientX - offsetX) + "px";
                modalContent.style.top = (e.clientY - offsetY) + "px";
                popup.style.display = "block";
            }
        });

        document.addEventListener("mouseup", () => {
            isDragging = false;
            if (modalHeader) {
                modalHeader.style.opacity = "1";
            }
        });
    }
});

// stunde löschen & absagen/entfallen
document.addEventListener("DOMContentLoaded", () => {
    // Löschen
    const deleteBtn = document.getElementById("deleteTerminBtn");
    if (deleteBtn) {
        deleteBtn.addEventListener("click", async () => {
            showToast("Termin in Bearbeitung", null);
            const terminId = document.getElementById("terminId").value;
            const kundeId  = document.getElementById("kundeId").value;
            const gruppeId = document.getElementById("gruppeId").value;
            if (!terminId) return;
            if (!confirm("Termin wirklich löschen?")) return;
            let url;
            let termintyp;
            if (gruppeId) {
                url = `/api/gruppentermine/${terminId}`;
                termintyp = "gruppentermin";
            } else {
                url = `/api/termine/${terminId}`;
                termintyp = "termin"
            }
            try {
                // 1️⃣ WebDAV-Event löschen
                const res1 = await fetch(`/api/kalender/webcal/${termintyp}/${terminId}`, {
                    method: "DELETE"
                });
                if (res1.status >= 500) {
                    throw new Error("Fehler beim Löschen des WebDAV-Events (Server-Fehler)");
                }
                // 2️⃣ Aus Datenbank löschen
                const res2 = await fetch(url, { method: "DELETE" });
                if (!res2.ok) {
                    throw new Error("Fehler beim Löschen aus der Datenbank");
                }
                const data2 = await res2.json();
                closefenstertermineanpassen();
                document.dispatchEvent(
                    new CustomEvent("kalenderTermineAnpassung", {
                        detail: { terminId }
                    })
                );
                if (typeof calendar !== "undefined" && calendar && typeof calendar.refetchEvents === "function") {
                    calendar.refetchEvents(); // neu zeichnen
                }
                alert("✅ Termin wurde gelöscht");
            } catch (err) {
                console.error("🗑️ Fehler beim Löschen:", err);
                alert(`❌ ${err.message}`);
            }
        });
    }

    // Absage/Entfallen
    const absageBtn = document.getElementById("absageTerminBtn");
    if (absageBtn) {
        absageBtn.addEventListener("click", async () => {
            console.log("Absage/Entfallen Button geklickt");
            showToast("Termin in Bearbeitung", null);
            const terminId = document.getElementById("terminId").value;
            const kundeId  = document.getElementById("kundeId").value;
            const gruppeId = document.getElementById("gruppeId").value;
            if (!terminId) return;
            if (!confirm("Termin wirklich absagen/entfallen?")) return;
            let url, payload;
            if (gruppeId) {
                url = `/api/gruppentermine/${terminId}`;
                payload = { entfallen: new Date().toISOString() };
            } else {
                url = `/api/termine/${terminId}`;
                payload = { abgesagt: new Date().toISOString() };
            }
            try {
                const res = await fetch(url, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error("Fehler beim Absagen/Entfallen");
                closefenstertermineanpassen();
                document.dispatchEvent(
                    new CustomEvent("kalenderTermineAnpassung", {
                        detail: { terminId }
                    })
                );
                if (typeof calendar !== "undefined" && calendar && typeof calendar.refetchEvents === "function") {
                    calendar.refetchEvents();
                }
                alert("✅ Termin wurde abgesagt/entfallen");
            } catch (err) {
                console.error("🛑 Fehler beim Absagen/Entfallen:", err);
                alert(`❌ ${err.message}`);
            }
        });
    }
});



// ===============================
// === SPEICHERN (NEU / UPDATE) ===
// ===============================
document.addEventListener("DOMContentLoaded", () => {
    const terminForm = document.getElementById("terminForm");
    if (!terminForm) {
        console.error("❌ terminForm nicht gefunden");
        return;
    }
    
    
    terminForm.addEventListener("submit", async e => {
        e.preventDefault();
        

       
        console.log("Formular abgesendet, Daten werden verarbeitet...");

        const formData = new FormData(terminForm);
        const data = Object.fromEntries(formData);

        // Zeitfelder: lokale Zeit -> UTC für Speicherung
 
        data.startzeit = data.startzeit ;
        data.endzeit = data.endzeit;
        data.ust = document.getElementById("terminUst").checked ? 1 : 0;
        if (data.kunde_id==""){
            delete data.kunde_id;       
        }
        if (data.gruppe_id==""){
            delete data.gruppe_id;       
        }

        data.push_termin = 1;
        data.betrag = parseFloat(data.betrag.replace(/\./g, "").replace(",", "."));

        // 🔄 Serientermine verarbeiten
        const istSerie = document.getElementById("istSerie").checked;
        let termineDaten = [data];
        if (istSerie) {
            const intervall = parseInt(document.getElementById("serieIntervall").value) || 1;
            const anzahl = parseInt(document.getElementById("serieAnzahl").value) || 1;
            const startDatum = new Date(data.datum);
            termineDaten = [];
            for (let i = 0; i < anzahl; i++) {
                const terminDatum = new Date(startDatum);
                terminDatum.setDate(terminDatum.getDate() + (i * intervall * 7));
                const neuerTermin = { ...data };
                neuerTermin.datum = terminDatum.toISOString().split("T")[0];
                // UTC-Zeiten für das jeweilige Datum berechnen
                neuerTermin.startzeit = localInputTimeToUTCStr(neuerTermin.datum, data.startzeit);
                neuerTermin.endzeit = localInputTimeToUTCStr(neuerTermin.datum, data.endzeit);
                
                termineDaten.push(neuerTermin);
            }
        }

        let url, method;
        const kundeId  = data.kundeId || data.kunde_id || null;
        const gruppeId = data.gruppeId || data.gruppe_id || null;
        console.log("Verarbeite Termin mit Daten:", data);
        if (data.terminId && data.kundeId) { //wenn termine und kunde vorhanden
            // console.log("🔄 Update Termin ID:", data.terminId);
            url = `/api/termine/${data.terminId}`;
            method = "PUT";
        }else if  (data.terminId && data.gruppeId) { //gruppentermin bearbeiten
            // console.log("🔄 Update Termin ID:", data.terminId);
            url = `/api/gruppentermine/${data.terminId}`;
            method = "PUT"; 
        } else if (gruppeId) { //gruppentermin erstellen
            // console.log("➕ Neue Termine für Gruppe ID:", gruppeId);
            url = `/api/gruppentermine/${gruppeId}`;
            method = "POST";
        } else {
            // console.log("➕ Neue Termine für Kunde ID:", kundeId);
            url = `/api/termine/${kundeId}`;
            method = "POST";
        }

        // Modal schließen NACH allen Speicherungen
            closefenstertermineanpassen();

        try {
            // 🔁 Alle Termine nacheinander speichern
            for (let termin of termineDaten) {
                // console.log(`Sende ${method} an ${url} für Datum: ${termin.datum}`);
                showToast("Termin in Bearbeitung", null);
                const res = await fetch(url, {
                    method,
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(termin)
                });

                if (!res.ok) {
                    alert(`❌ Fehler beim Speichern von Termin ${termin.datum}`);
                    return;
                }

                const stunde = await res.json();
                // console.log("Gespeicherter Termin:", stunde);
            }

            

            // 📣 GLOBAL sagen: „Termine gespeichert"
            document.dispatchEvent(
                new CustomEvent("kalenderTermineAnpassung", {
                    detail: { success: true, count: termineDaten.length }
                })
            );
            // console.log("neuladen")
            if (typeof calendar !== "undefined" && calendar && typeof calendar.refetchEvents === "function") {
                calendar.refetchEvents(); // neu zeichnen
            }
        } catch (err) {
            console.error(err);
            alert("❌ Fehler beim Speichern");
        }
    });
});
