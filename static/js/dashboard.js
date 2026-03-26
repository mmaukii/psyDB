// Praxiskalender-Button: Async Sync mit Toast wie im Kalender-Tab

document.addEventListener("DOMContentLoaded", function() {
    async function syncCalendar() {
        console.log("Sync Termine gestartet");
        const startedAt = performance.now();
        showToast("Sync Termine läuft …", null);
        try {
            const res = await fetch("/api/calendar/sync", { method: "POST" });
            if (!res.ok) throw new Error("Fehler beim Sync");
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
        syncCalendar();
        localStorage.setItem("dashboardCalendarSynced", "1");
    }

    // Button-Handler wie gehabt
    const btn = document.getElementById("praxiskalenderButton");
    if (btn) {
        btn.addEventListener("click", function() {
            syncCalendar();
            // Nach manuellem Sync kann das Flag wieder entfernt werden, falls gewünscht:
            // localStorage.removeItem("dashboardCalendarSynced");
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
                logoImg.src = logoVar.wert;
                logoImg.style.display = "block";
            } else {
                logoImg.style.display = "none";
            }
        }).catch(err => {
            console.error("Fehler beim Laden des Logos:", err);
        });
});
