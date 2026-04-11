let calendar = null; // global, damit auf den Kalender zugegriffen werden kann
let calendarInitialized = sessionStorage.getItem("kalenderInitialized") === "1";
//xx

function showToast(text = "Gespeichert!", durationMs = 2000) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = text;
    toast.classList.add("show");

    if (durationMs !== null) {
        setTimeout(() => {
            toast.classList.remove("show");
        }, durationMs);
    }
}

async function syncPraxisKalender() {
    if (!navigator.onLine) {
        showToast("Offline: Sync nicht möglich!", 2000);
        return;
    }
    const startedAt = performance.now();
    showToast("Sync Termine läuft …", null);
    const res = await fetch("/api/calendar/sync", { method: "POST" });
    if (!res.ok) {
        return;
    }

    const duration = ((performance.now() - startedAt) / 1000).toFixed(1);
    showToast(`Sync Termine ✅ (${duration}s)`);

    calendar.refetchEvents(); // lokale
}

document.getElementById('syncButton').addEventListener('click', syncPraxisKalender);
document.getElementById('syncExterneButton').addEventListener('click', async () => {
    
    if (!navigator.onLine) {
        showToast("Offline: Sync nicht möglich!", 2000);
        return;
    }
    
    const startedAt = performance.now();
    showToast("Sync Extern läuft …", null);
    await refreshExternalCache();
    const src = calendar.getEventSourceById('externalEvents');
    if (src) {
        src.refetch();
    }
    const duration = ((performance.now() - startedAt) / 1000).toFixed(1);
    showToast(`Sync Extern ✅ (${duration}s)`);
});

document.addEventListener('DOMContentLoaded', async function() {
    var calendarEl = document.getElementById('calendar');
    var selectedEvent = null;
    var popupMode = null; // "new" oder "edit"
    var lastClickTime = 0;

    function formatTimeForInput(date) {
        if (!date) return "00:00";
        let d = new Date(date);
        let h = String(d.getHours()).padStart(2, "0");
        let m = String(d.getMinutes()).padStart(2, "0");
        return `${h}:${m}`;
    }
    calendar = new FullCalendar.Calendar(calendarEl, {
        height: "auto",
        expandRows: true,
        initialView: 'dayGridMonth',
        locale: 'de',
        firstDay: 1, // 0 = Sonntag, 1 = Montag
        editable: true,
        selectable: true,
        // Zeitanzeige in 24h-Format
    slotLabelFormat: {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    },
    scrollTime: '08:00:00',
    eventTimeFormat: {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    },

        
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        buttonText: {
            today: 'Heute',
            month: 'Monat',
            week: 'Woche',
            day: 'Tag'
        },
        datesSet: function(info) {
            if (info.view.type.startsWith('dayGrid')) {
                calendarEl.classList.add('is-daygrid');
                calendarEl.classList.remove('is-timegrid');
                calendar.setOption('height', 'auto');
            } else {
                calendarEl.classList.add('is-timegrid');
                calendarEl.classList.remove('is-daygrid');
                calendar.setOption('height', '85vh');
            }
            calendar.updateSize();
        },
       

        // 🟢 Bestehendes Event bearbeiten
        eventClick: function(info) {
            const selectedEvent = info.event;

             // 🔹 Prüfen, ob das Event extern/readonly ist
            if (selectedEvent.extendedProps?.readonly) {
                return; // Fenster nicht öffnen
            }

            function toUtcTimeString(date) {
                if (!date) return "00:00";
                const utcHours = String(date.getUTCHours()).padStart(2, "0");
                const utcMinutes = String(date.getUTCMinutes()).padStart(2, "0");
                return `${utcHours}:${utcMinutes}`;
            }
            

            openfensterTerminAnpassen({
                stundensatz: selectedEvent.extendedProps?.betrag || "",
                beschreibung: selectedEvent.extendedProps?.beschreibung || "",
                datum: selectedEvent.startStr.split("T")[0],
                startzeit: toUtcTimeString(selectedEvent.start),
                endzeit: toUtcTimeString(selectedEvent.end),
                stundeId: selectedEvent.id || "",
                kundeId: selectedEvent.extendedProps?.kunde_id || "",
                gruppeId: selectedEvent.extendedProps?.gruppe_id || ""
            });
            //kunden und gruppenfelder ausblenden
            const gruppeWrapper = document.getElementById("gruppeWrapper").style.display = "none";
            const kundeWrapper = document.getElementById("kundeWrapper").style.display = "none";

        
        },

        // 🟢 Event per Drag verschieben
        eventDrop: function(info) {
            updateEvent(info.event);
        },

        // 🟢 Drag-Auswahl → neuer Termin
        select: function(info) {
            selectedEvent = null;
            popupMode = "new";

            function extractTime(str) {
                if (!str || !str.includes("T")) return "00:00";
                let time = str.split("T")[1].split("+")[0];
                return time.substring(0,5);
            }
        },

        // 🟢 Doppelklick → neuer Termin
        dateClick: function(info) {
            let now = new Date().getTime();
            if (now - lastClickTime < 400) { // innerhalb 400ms = Doppelklick

                // Aktuelle Stunde ermitteln
                const jetzt = new Date();
                const aktuelleStunde = `${String(jetzt.getHours()).padStart(2, "0")}:00`;

                openfensterTerminAnpassen({
                    stundensatz:  "",
                    beschreibung: "",
                    datum: info.dateStr,
                    startzeit: aktuelleStunde,
                    endzeit: ""
                });
            }

        // 🟢 Kunden-Wrapper sichtbar machen
        const kundeWrapper = document.getElementById("kundeWrapper");
        const kundeSelect = document.getElementById("kunde");

        if (kundeWrapper && kundeSelect) {
            kundeWrapper.style.display = "block";

            // Select vorher leeren
            kundeSelect.innerHTML = '<option value="">– Kunde wählen –</option>';

            // Kunden über API laden
            fetch("/api/kunden/aktiv")
                .then(res => res.json())
                .then(kunden => {
                    kunden.forEach(k => {
                        const opt = document.createElement("option");
                        opt.value = k.id;
                        opt.textContent = `${k.vorname} ${k.nachname}`;
                        kundeSelect.appendChild(opt);
                    });
                })
                .catch(err => console.error("Fehler beim Laden der Kunden:", err));
        }

        // 🟢 Gruppen-Wrapper sichtbar machen
        const gruppeWrapper = document.getElementById("gruppeWrapper");
        const gruppeSelect = document.getElementById("gruppe");

        if (gruppeWrapper && gruppeSelect) {
            gruppeWrapper.style.display = "block";
            // Select vorher leeren
            gruppeSelect.innerHTML = '<option value="">– Gruppe wählen –</option>';

            // Kunden über API laden
            fetch("/api/gruppen/aktiv")
                .then(res => res.json())
                .then(kunden => {
                    kunden.forEach(k => {
                        const opt = document.createElement("option");
                        opt.value = k.id;
                        opt.textContent = `${k.gruppenkuerzel}`;
                        gruppeSelect.appendChild(opt);
                    });
                })
                .catch(err => console.error("Fehler beim Laden der Gruppe:", err));
        }
            lastClickTime = now;
        }
    });

    calendar.render();

    await initEvents();
    calendar.refetchEvents();

    if (!calendarInitialized) {
        await syncPraxisKalender();
        await loadExternEvents(true); // Cache mit Force füllen
        calendar.refetchEvents();
        calendarInitialized = true;
        sessionStorage.setItem("kalenderInitialized", "1");
        document.querySelectorAll('.toast').forEach(toast => {
            toast.remove(); // entfernt das Element
            // oder toast.style.display = 'none'; // nur unsichtbar machen
        });
    }

    // 🔄 Event aktualisieren (Drag)
    function updateEvent(event) {
        console.log(event);
        if (event._def.extendedProps.kunde_id) {
            // Zeit in UTC umrechnen
            function toUtcTimeString(date) {
                if (!date) return "00:00";
                const utcHours = String(date.getUTCHours()).padStart(2, "0");
                const utcMinutes = String(date.getUTCMinutes()).padStart(2, "0");
                return `${utcHours}:${utcMinutes}`;
            }
            console.log("aktualisiere Termin ID", event.id);

            fetch('/api/termine/' + event.id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    datum: event.startStr.split("T")[0],
                    startzeit: toUtcTimeString(event.start),
                    endzeit: toUtcTimeString(event.end),
                    beschreibung: event.summary,
                    betrag: event.extendedProps?.betrag ?? null,
                    push_termin : 1, //um Kalender zu aktualisieren
                    caldav_uid: event.extendedProps?.caldav_uid ?? null
                })
            })
            .then(res => {
                if (!res.ok) throw new Error("Fehler beim Aktualisieren");
                return res.json();
            })
            .then(() => calendar.refetchEvents())
            .catch(err => console.error(err));  
        } else if (event._def.extendedProps.gruppe_id) {
            console.log("aktualisiere Gruppentermin ID", event.id);
            fetch('/api/gruppentermine/' + event.id, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    datum: event.startStr.split("T")[0],
                    startzeit: toUtcTimeString(event.start),
                    endzeit: toUtcTimeString(event.end),
                    beschreibung: event.title,
                    betrag: event.extendedProps?.betrag ?? null,
                    push_termin: 1 // Damit der Push an CalDAV erfolgt
                })    
            })
            
            .then(res => {
                if (!res.ok) throw new Error("Fehler beim Aktualisieren");
                return res.json();
            })
            .then(() => calendar.refetchEvents())
            .catch(err => console.error(err)); 
            console.log("angepasst")
        }       
    }   
});
let externalEventSource = null;
let externalVisible = true; // aktuell sichtbar

async function loadLocalEvents() {
    const res = await fetch('/api/kalender/termine_anzuzeigen');
    const data = await res.json();
    console.log("Lokale Termine geladen:", data);
    function utcToLocalTime(dateStr, utcTime) {
        if (!dateStr || !utcTime) return "";
        const [h, m, s] = utcTime.split(":");
        // Erzeuge UTC-Date
        const utcDate = new Date(Date.UTC(
            parseInt(dateStr.slice(0, 4)),
            parseInt(dateStr.slice(5, 7)) - 1,
            parseInt(dateStr.slice(8, 10)),
            h, m, s || 0
        ));
        // In lokale Zeit umwandeln und als ISO-String zurückgeben
        const localDate = new Date(utcDate.getTime() + (utcDate.getTimezoneOffset() * 60000 * -1));
        // FullCalendar erwartet ISO-String (ohne Offset)
        return localDate.toISOString().slice(0, 16);
    }
    return data.map(s => {
        // caldav_uid ggf. aus s holen, falls vorhanden
        const caldav_uid = s.caldav_uid || null;
        return {
            id: s.id,
            title: s.gruppe_id ? `👥 ${s.gruppen_kuerzel || "Gruppe"}` : (s.kunde_kuerzel || "–"),
            start: utcToLocalTime(s.datum, s.startzeit),
            end: utcToLocalTime(s.datum, s.endzeit),
            backgroundColor: s.gruppe_id ? "#4f46e5" : "#16a34a",
            borderColor: s.gruppe_id ? "#4338ca" : "#15803d",
            textColor: "#ffffff",
            editable: true,
            extendedProps: {
                ...s,                // komplette DB-Zeile
                source: "termine",  // 🔑 wichtig für Sync
                caldav_uid           // explizit hinzufügen
            }
        };
    });

    
}
const CACHE_KEY = "externalCalendarCache";

// --- Hilfsfunktion: Zeitfenster berechnen ---
function getTimeWindow() {
    const now = new Date();

    const start = new Date(now);
    start.setMonth(start.getMonth() - 1); // 1 Monat zurück

    const end = new Date(now);
    end.setFullYear(end.getFullYear() + 2); // 2 Jahre in Zukunft

    return { start, end };
}

// --- Hauptfunktionen ---
async function loadExternEvents(force = false) {
    const cached = localStorage.getItem(CACHE_KEY);

    if (cached && !force) {
        return JSON.parse(cached);
    }

    return await refreshExternalCache();
}


async function refreshExternalCache() {

    const res = await fetch('/api/kalender/extern');
    const data = await res.json();

    const { start, end } = getTimeWindow();

    // nur Events im gewünschten Zeitraum speichern
    const filtered = data
        .map(ev => ({
            id: `caldav-${ev.uid}`,
            title: ev.title,
            start: ev.start,
            end: ev.end,
            classNames: ["external-event"] // FullCalendar nutzt classNames
        }))
        .filter(ev => {
            const evDate = new Date(ev.start);
            return evDate >= start && evDate <= end;
        });

    try {
        localStorage.setItem(CACHE_KEY, JSON.stringify(filtered));
    } catch (e) {
        console.warn("⚠ Cache konnte nicht geschrieben werden:", e);
    }

    return filtered;
}




async function initEvents() {

    calendar.addEventSource({
        id: 'localEvents',
        events: async function(fetchInfo, success, failure) {
            try {
                success(await loadLocalEvents());
            } catch (e) {
                failure(e);
            }
        }
    });

    externalEventSource = calendar.addEventSource({
        id: 'externalEvents',
        events: async function(fetchInfo, success, failure) {
            try {
                success(await loadExternEvents(false)); // ❌ kein Force beim Monatswechsel
            } catch (e) {
                failure(e);
            }
        }
    });

    externalVisible = true;
}


// Toggle Checkbox
document.getElementById('toggleExterne').addEventListener('change', function(e) {
    if (!externalEventSource) return;

    const src = calendar.getEventSourceById('externalEvents');
    if (e.target.checked && !externalVisible) {
        calendar.addEventSource(externalEventSource);
        externalVisible = true;
    } else if (!e.target.checked && externalVisible && src) {
        src.remove();
        externalVisible = false;
    }
});



let popupMode = null; // "new" oder "edit"
let selectedEvent = null;

// === 1️⃣ Hilfsfunktion: Zeit in lokale HH:MM umwandeln ===
function formatTimeLocal(date) {
    const h = String(date.getHours()).padStart(2, "0");
    const m = String(date.getMinutes()).padStart(2, "0");
    return `${h}:${m}`;
}

document.addEventListener("kalenderTermineAnpassung", function (e) {
    const ev = e.detail;

    let existing = calendar.getEventById(ev.id);
    if (existing) {
        existing.remove(); // Update-Fall
    }

    calendar.addEvent(ev); // Neu oder aktualisiert
});

async function ladeKunden() {
    const select = document.getElementById("kunde");
    const wrapper = document.getElementById("kundeWrapper");

    if (!select || !wrapper) return;

    // vorher leeren
    select.innerHTML = '<option value="">– Kunde wählen –</option>';

    try {
        const res = await fetch("/api/kunden/aktiv"); // nur aktive
        const kunden = await res.json();

        kunden.forEach(k => {
            const opt = document.createElement("option");
            opt.value = k.id;
            opt.textContent = `${k.vorname} ${k.nachname}`; // oder k.kuerzel
            select.appendChild(opt);
        });

        // Wrapper anzeigen
        wrapper.style.display = "block";
    } catch (err) {
        console.error("❌ Fehler beim Laden der Kunden:", err);
    }
}

async function updateEvent(event) {
    await fetch(`/api/termine/${event.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            start: event.start.toISOString(),
            end: event.end.toISOString(),
            changestamp: new Date().toISOString(),
            push_termin : 1 //um Kalender zu aktualisieren
        })
    });
}


