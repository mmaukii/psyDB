// Praxiskalender-Button: Async Sync mit Toast wie im Kalender-Tab

document.addEventListener("DOMContentLoaded", function() {
    async function syncCalendar(interactive = false) {
        if (!navigator.onLine) {
            showToast("Offline: Sync nicht möglich!", 2000);
            return;
        }
        console.log("Sync Termine gestartet");
        const startedAt = performance.now();
        showToast("Sync Termine läuft …", null);
        try {
            const requestSync = async (missingEventAction = null, missingEventActions = null) => {
                const payload = { interactive };
                if (missingEventAction) {
                    payload.missing_event_action = missingEventAction;
                }
                if (missingEventActions && Object.keys(missingEventActions).length) {
                    payload.missing_event_actions = missingEventActions;
                }

                const res = await fetch("/api/calendar/sync", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) throw new Error("Fehler beim Sync");
                return await res.json();
            };

            let data = await requestSync();

            if (interactive && data.requires_missing_action) {
                const actions = await window.askMissingOnlineEventsAction(data.missing_events || []);
                if (!actions) {
                    showToast("Sync abgebrochen", 2000);
                    return;
                }
                data = await requestSync(null, actions);
            }

            const duration = ((performance.now() - startedAt) / 1000).toFixed(1);
            showToast(`Sync Termine ✅ (${duration}s)`);
            setTimeout(() => {
                window.location.reload();
            }, 1200);
        } catch (e) {
            showToast("Sync Fehler!", 2000);
        }
    }


    // Sync nur beim ersten Laden ausführen, nicht bei jedem Tab-Reload
    if (!localStorage.getItem("dashboardCalendarSynced")) {
        syncCalendar(false);
        localStorage.setItem("dashboardCalendarSynced", "1");
    }

    // Button-Handler wie gehabt
    const btn = document.getElementById("praxiskalenderButton");
    if (btn) {
        btn.addEventListener("click", function() {
            syncCalendar(true);
        });
    }
});

// Logo beim Laden anzeigen
document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/programmvariablen')
        .then(res => res.json())
        .then(data => {
            const logoVar = data.find(v => v.name === "logo_file");
            const logoImg = document.getElementById("dashboardLogo");
            
            if (logoVar && logoVar.wert) {
                logoImg.src = `/api/logo-file?ts=${Date.now()}`;
                logoImg.style.display = "block";
            } else {
                logoImg.style.display = "none";
            }
        }).catch(err => {
            console.error("Fehler beim Laden des Logos:", err);
        });
});
