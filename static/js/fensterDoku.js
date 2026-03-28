// ===============================
// === DOKU MODAL (ZENTRAL) ===
// ===============================
const fensterDoku = document.getElementById("fensterDoku");
const dokuForm    = document.getElementById("dokuForm");

// ===============================
// === GLOBALE MODAL API ===
// ===============================
window.openFensterDoku = function ({
    termineId = "",
    gruppentermineId = "",
    doku = "",
    pers_doku = ""
}) {
    console.log("📚 Öffne Doku");
    console.log({  termineId, gruppentermineId ,doku, pers_doku});

    dokuForm.reset();

    document.getElementById("termineId").value = termineId || "";
    document.getElementById("gruppentermineId").value = gruppentermineId || "";
    document.getElementById("dokuText").value = pers_doku ? `${doku || ""}\n\n*****\n\n${pers_doku}` : (doku || "");



    // Titel anpassen
    const title = document.getElementById("dokuModalTitle");
    if (gruppentermineId) {
        title.textContent = "Dokumentation – Gruppe";
    } else {
        title.textContent = "Dokumentation – Einzelstunde";
    }

    fensterDoku.style.display = "block";
};

// ===============================
// === SCHLIESSEN ===
// ===============================
window.closeFensterDoku = function () {
    fensterDoku.style.display = "none";
};

document.addEventListener("DOMContentLoaded", () => {
    const closeBtn = fensterDoku.querySelector(".close");
    if (closeBtn) {
        closeBtn.addEventListener("click", closeFensterDoku);
    }
});

// ===============================
// === SPEICHERN ===
// ===============================
document.addEventListener("DOMContentLoaded", () => {
    if (!dokuForm) return;

    dokuForm.addEventListener("submit", async e => {
        e.preventDefault();

        const data = Object.fromEntries(new FormData(dokuForm));
        // Dokutext aufteilen auf unterschiedliche Dokues
         [data.doku, data.pers_doku] = (text => {
            const m = text.split(/\n*\*{3,}\n*/);
            return [m[0]?.trim() || "", m[1]?.trim() || ""];
            })(document.getElementById("dokuText").value);

        console.log("💾 Speichere Doku:", data);

        let url, method;

        if (data.termineId) {
            // Einzelstunde UPDATE
            url = `/api/termine/${data.termineId}`;
            method = "PUT";
        }  if ( data.gruppentermineId) {
            // Gruppentermin UPDATE
            url = `/api/gruppentermine/${data.gruppentermineId}`;
            method = "PUT";
        } 

        console.log(`➡️ ${method} ${url}`);

        const res = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        if (!res.ok) {
            alert("❌ Fehler beim Speichern der Doku");
            return;
        }

        const result = await res.json();
        console.log("✅ Doku gespeichert:", result);

        closeFensterDoku();

        // Globales Event (optional)
        document.dispatchEvent(
            new CustomEvent("dokuGespeichert", {
                detail: result
            })
        );
    });
});
