// Toast-Funktion global verfügbar machen
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

function escapeDialogHtml(text) {
    return String(text ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatGermanDate(dateString) {
    if (!dateString) return "";
    const match = String(dateString).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return String(dateString);
    return `${match[3]}.${match[2]}.${match[1]}`;
}

window.askMissingOnlineEventsAction = function (events = []) {
    return new Promise(resolve => {
        const overlay = document.createElement("div");
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.background = "rgba(0, 0, 0, 0.35)";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.style.zIndex = "10000";

        overlay.innerHTML = `
            <div style="background: white; width: min(460px, 90vw); max-height: 80vh; overflow: auto; border-radius: 10px; box-shadow: 0 16px 40px rgba(0,0,0,0.25); padding: 16px;">
                <h3 style="margin-top: 0; margin-bottom: 6px; font-size: 1.05rem;">Online gelöschte Termine gefunden</h3>
                <p id="missingEventsCounter" style="margin: 0 0 10px 0; color: #666; font-size: 0.92rem;"></p>
                <div id="missingEventsDetails" style="line-height: 1.4; margin-bottom: 12px;"></div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; margin-top: 12px;">
                    <button type="button" id="missingEventsIgnoreBtn" class="table-btn">Nichts tun</button>
                    <button type="button" id="missingEventsStatusBtn" class="table-btn">Status setzen</button>
                    <button type="button" id="missingEventsRestoreBtn" class="table-btn">Online wiederherstellen</button>
                    <button type="button" id="missingEventsDeleteBtn" class="table-btn" style="background: #c0392b; color: white;">in DB Löschen</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        const counter = overlay.querySelector("#missingEventsCounter");
        const details = overlay.querySelector("#missingEventsDetails");
        const statusBtn = overlay.querySelector("#missingEventsStatusBtn");
        const actions = {};
        let index = 0;

        const finish = value => {
            overlay.remove();
            resolve(value);
        };

        const renderCurrentEvent = () => {
            const event = events[index];
            if (!event) {
                finish(actions);
                return;
            }

            statusBtn.textContent = event.typ === "gruppe"
                ? "Auf entfallen stellen"
                : "Auf abgesagt stellen";

            const detailsList = [
                event.name ? `<p style="margin: 0 0 6px 0;"><strong>Name:</strong> ${escapeDialogHtml(event.name)}</p>` : "",
                event.datum ? `<p style="margin: 0 0 6px 0;"><strong>Datum:</strong> ${escapeDialogHtml(formatGermanDate(event.datum))}</p>` : "",
                [event.startzeit, event.endzeit].filter(Boolean).join(" – ")
                    ? `<p style="margin: 0 0 6px 0;"><strong>Zeit:</strong> ${escapeDialogHtml([event.startzeit, event.endzeit].filter(Boolean).join(" – "))}</p>`
                    : "",
                event.beschreibung ? `<p style="margin: 0;"><strong>Beschreibung:</strong> ${escapeDialogHtml(event.beschreibung)}</p>` : ""
            ].filter(Boolean).join("");

            details.innerHTML = `
                <p style="margin: 0 0 10px 0; font-size: 0.95rem;">Dieser Termin ist online gelöscht worden. Was soll damit passieren?</p>
                <div style="padding: 10px 12px; border-radius: 8px; background: #f8f9fb; border: 1px solid #e1e5eb; font-size: 0.95rem;">
                    ${detailsList || '<p style="margin: 0;">Keine Details verfügbar.</p>'}
                </div>
            `;
        };

        const selectAction = action => {
            const event = events[index];
            if (!event?.uid) {
                finish(null);
                return;
            }
            actions[event.uid] = action;
            index += 1;
            renderCurrentEvent();
        };

        overlay.querySelector("#missingEventsIgnoreBtn").addEventListener("click", () => selectAction("ignore"));
        statusBtn.addEventListener("click", () => {
            const event = events[index];
            selectAction(event?.typ === "gruppe" ? "entfallen" : "abgesagt");
        });
        overlay.querySelector("#missingEventsRestoreBtn").addEventListener("click", () => selectAction("restore"));
        overlay.querySelector("#missingEventsDeleteBtn").addEventListener("click", () => selectAction("delete"));

        renderCurrentEvent();
    });
};

window.askChangedOnlineEventsAction = function (events = []) {
    return new Promise(resolve => {
        const overlay = document.createElement("div");
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.background = "rgba(0, 0, 0, 0.35)";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.style.zIndex = "10000";

        overlay.innerHTML = `
            <div style="background: white; width: min(500px, 90vw); max-height: 80vh; overflow: auto; border-radius: 10px; box-shadow: 0 16px 40px rgba(0,0,0,0.25); padding: 16px;">
                <h3 style="margin-top: 0; margin-bottom: 6px; font-size: 1.05rem;">Verschobener Termin gefunden</h3>
                <p id="changedEventsCounter" style="margin: 0 0 10px 0; color: #666; font-size: 0.92rem;"></p>
                <div id="changedEventsDetails" style="line-height: 1.4; margin-bottom: 12px;"></div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; margin-top: 12px;">
                    <button type="button" id="changedEventsIgnoreBtn" class="table-btn">Nichts tun</button>
                    <button type="button" id="changedEventsOnlineBtn" class="table-btn">Online-Termin übernehmen</button>
                    <button type="button" id="changedEventsDatabaseBtn" class="table-btn">Datenbanktermin übernehmen</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        const counter = overlay.querySelector("#changedEventsCounter");
        const details = overlay.querySelector("#changedEventsDetails");
        const actions = {};
        let index = 0;

        const finish = value => {
            overlay.remove();
            resolve(value);
        };

        const formatTimeRange = (datum, startzeit, endzeit) => {
            const parts = [formatGermanDate(datum), [startzeit, endzeit].filter(Boolean).join(" – ")].filter(Boolean);
            return parts.join(" · ");
        };

        const renderCurrentEvent = () => {
            const event = events[index];
            if (!event) {
                finish(actions);
                return;
            }


            details.innerHTML = `
                <p style="margin: 0 0 10px 0; font-size: 0.95rem;">Der Termin wurde online verschoben. Welche Version soll gelten?</p>
                <div style="padding: 10px 12px; border-radius: 8px; background: #f8f9fb; border: 1px solid #e1e5eb; font-size: 0.95rem; margin-bottom: 10px;">
                    ${event.name ? `<p style="margin: 0 0 6px 0;"><strong>Name:</strong> ${escapeDialogHtml(event.name)}</p>` : ""}
                    ${event.beschreibung ? `<p style="margin: 0;"><strong>Beschreibung:</strong> ${escapeDialogHtml(event.beschreibung)}</p>` : ""}
                </div>
                <div style="display: grid; grid-template-columns: 1fr; gap: 8px;">
                    <div style="padding: 10px 12px; border-radius: 8px; background: #eef7ff; border: 1px solid #cfe3f7; font-size: 0.95rem;">
                        <p style="margin: 0 0 4px 0;"><strong>Online</strong></p>
                        <p style="margin: 0;">${escapeDialogHtml(formatTimeRange(event.online_datum, event.online_startzeit, event.online_endzeit) || "Keine Daten")}</p>
                    </div>
                    <div style="padding: 10px 12px; border-radius: 8px; background: #f7f7f7; border: 1px solid #dddddd; font-size: 0.95rem;">
                        <p style="margin: 0 0 4px 0;"><strong>Datenbank</strong></p>
                        <p style="margin: 0;">${escapeDialogHtml(formatTimeRange(event.db_datum, event.db_startzeit, event.db_endzeit) || "Keine Daten")}</p>
                    </div>
                </div>
            `;
        };

        const selectAction = action => {
            const event = events[index];
            if (!event?.uid) {
                finish(null);
                return;
            }
            actions[event.uid] = action;
            index += 1;
            renderCurrentEvent();
        };

        overlay.querySelector("#changedEventsIgnoreBtn").addEventListener("click", () => selectAction("ignore"));
        overlay.querySelector("#changedEventsOnlineBtn").addEventListener("click", () => selectAction("online"));
        overlay.querySelector("#changedEventsDatabaseBtn").addEventListener("click", () => selectAction("database"));

        renderCurrentEvent();
    });
};

window.askNewOnlineEventsAction = function (events = []) {
    return new Promise(resolve => {
        const overlay = document.createElement("div");
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.background = "rgba(0, 0, 0, 0.35)";
        overlay.style.display = "flex";
        overlay.style.alignItems = "center";
        overlay.style.justifyContent = "center";
        overlay.style.zIndex = "10000";

        overlay.innerHTML = `
            <div style="background: white; width: min(460px, 90vw); max-height: 80vh; overflow: auto; border-radius: 10px; box-shadow: 0 16px 40px rgba(0,0,0,0.25); padding: 16px;">
                <h3 style="margin-top: 0; margin-bottom: 6px; font-size: 1.05rem;">Neuer Online-Termin gefunden</h3>
                <p id="newEventsCounter" style="margin: 0 0 10px 0; color: #666; font-size: 0.92rem;"></p>
                <div id="newEventsDetails" style="line-height: 1.4; margin-bottom: 12px;"></div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; margin-top: 12px;">
                    <button type="button" id="newEventsIgnoreBtn" class="table-btn">Nichts tun</button>
                    <button type="button" id="newEventsDeleteBtn" class="table-btn" style="background: #c0392b; color: white;">Online löschen</button>
                    <button type="button" id="newEventsTakeBtn" class="table-btn">Übernehmen</button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        const counter = overlay.querySelector("#newEventsCounter");
        const details = overlay.querySelector("#newEventsDetails");
        const actions = {};
        let index = 0;

        const finish = value => {
            overlay.remove();
            resolve(value);
        };

        const renderCurrentEvent = () => {
            const event = events[index];
            if (!event) {
                finish(actions);
                return;
            }

            counter.textContent = `Termin ${index + 1} von ${events.length}`;

            const detailsList = [
                event.name ? `<p style="margin: 0 0 6px 0;"><strong>Name:</strong> ${escapeDialogHtml(event.name)}</p>` : "",
                event.datum ? `<p style="margin: 0 0 6px 0;"><strong>Datum:</strong> ${escapeDialogHtml(formatGermanDate(event.datum))}</p>` : "",
                [event.startzeit, event.endzeit].filter(Boolean).join(" – ")
                    ? `<p style="margin: 0 0 6px 0;"><strong>Zeit:</strong> ${escapeDialogHtml([event.startzeit, event.endzeit].filter(Boolean).join(" – "))}</p>`
                    : "",
                event.beschreibung ? `<p style="margin: 0;"><strong>Beschreibung:</strong> ${escapeDialogHtml(event.beschreibung)}</p>` : ""
            ].filter(Boolean).join("");

            details.innerHTML = `
                <p style="margin: 0 0 10px 0; font-size: 0.95rem;">Dieser Termin wurde online neu angelegt. Was soll damit passieren?</p>
                <div style="padding: 10px 12px; border-radius: 8px; background: #f8f9fb; border: 1px solid #e1e5eb; font-size: 0.95rem;">
                    ${detailsList || '<p style="margin: 0;">Keine Details verfügbar.</p>'}
                </div>
            `;
        };

        const selectAction = action => {
            const event = events[index];
            if (!event?.uid) {
                finish(null);
                return;
            }
            actions[event.uid] = action;
            index += 1;
            renderCurrentEvent();
        };

        overlay.querySelector("#newEventsIgnoreBtn").addEventListener("click", () => selectAction("ignore"));
        overlay.querySelector("#newEventsDeleteBtn").addEventListener("click", () => selectAction("delete"));
        overlay.querySelector("#newEventsTakeBtn").addEventListener("click", () => selectAction("take"));

        renderCurrentEvent();
    });
};

const APP_TITLE = "psyDB";

function updateBrowserTabTitle(activeTabText = "") {
    const activeNavLink = document.querySelector(".nav-link.active");
    const navTitle = activeNavLink ? activeNavLink.textContent.trim() : "";
    const tabTitle = activeTabText ? activeTabText.trim() : "";

    let title = APP_TITLE;
    if (navTitle && tabTitle) {
        title = `${navTitle} - ${tabTitle}`;
    } else if (navTitle) {
        title = `${navTitle}`;
    } else if (tabTitle) {
        title = `${tabTitle} `;
    }

    document.title = title;
}

// Tab Umschalten
const tabs = document.querySelectorAll(".tab");
const contents = document.querySelectorAll(".tab-content");

tabs.forEach(tab => {
    tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");

        contents.forEach(c => c.classList.remove("active"));
        const content = document.getElementById(tab.dataset.tab);
        if (content) {
            content.classList.add("active");
        }

        updateBrowserTabTitle(tab.textContent);
    });
});


document.addEventListener("DOMContentLoaded", () => {
    const links = document.querySelectorAll(".nav-link");
    const currentPath = window.location.pathname;

    links.forEach(link => {
        const href = link.getAttribute("href");
        if (href === "/" && currentPath === "/") {
            link.classList.add("active");
        } else if (href !== "/" && currentPath.startsWith(href)) {
            link.classList.add("active");
        }
    });

    const activeTab = document.querySelector(".tab.active");
    updateBrowserTabTitle(activeTab ? activeTab.textContent : "");
});

