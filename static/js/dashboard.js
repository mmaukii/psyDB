// Praxiskalender-Button: Async Sync mit Toast wie im Kalender-Tab

document.addEventListener("DOMContentLoaded", function() {
    const btn = document.getElementById("praxiskalenderButton");
    if (btn) {
        btn.addEventListener("click", async function() {
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
        });
    }
});
