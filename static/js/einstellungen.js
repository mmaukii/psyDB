// Datenbank Passwort ändern
document.getElementById("changeDbPassphraseBtn").addEventListener("click", () => {
    const current = document.getElementById("dbPassphraseCurrent").value;
    const next = document.getElementById("dbPassphraseNew").value;
    const confirm = document.getElementById("dbPassphraseNewConfirm").value;

    if (!current || !next || !confirm) {
        alert("Bitte alle Passwortfelder ausfüllen!");
        return;
    }
    if (next !== confirm) {
        alert("Neue Passwörter stimmen nicht überein!");
        return;
    }

    fetch('/api/passphrase', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            current_password: current,
            new_password: next
        })
    }).then(response => response.json())
    .then(data => {
        if (data.message) {
            alert("Datenbank Passwort geändert!");
            document.getElementById("dbPassphraseCurrent").value = "";
            document.getElementById("dbPassphraseNew").value = "";
            document.getElementById("dbPassphraseNewConfirm").value = "";
        } else {
            alert("Fehler: " + data.error);
        }
    }).catch(err => {
        console.error("Fehler:", err);
        alert("Fehler beim Ändern des Passworts!");
    });
});
// Kopie von standorte.js, angepasst auf einstellungen
function loadEinstellungen() {
    fetch('/api/standorte')
        .then(res => res.json())
        .then(data => {
            const tbody = document.querySelector("#standorteTable tbody");
            tbody.innerHTML = "";
            data.forEach(s => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td contenteditable="true" data-field="name">${s.name || ""}</td>
                    <td contenteditable="true" data-field="adresse">${s.adresse || ""}</td>
                    <td contenteditable="true" data-field="plz">${s.plz || ""}</td>
                    <td contenteditable="true" data-field="ort">${s.ort || ""}</td>
                    <td contenteditable="true" data-field="email">${s.email || ""}</td>
                    <td contenteditable="true" data-field="kuerzel">${s.kuerzel || ""}</td>
                    <td contenteditable="true" data-field="bankname">${s.bankname || ""}</td>
                    <td contenteditable="true" data-field="bic">${s.bic || ""}</td>
                    <td contenteditable="true" data-field="iban">${s.iban || ""}</td>
                    <td contenteditable="true" data-field="kontoName">${s.kontoName || ""}</td>
                    <td style="text-align:center;">
                        <input type="checkbox" class="standardCheckbox" ${s.standard ? "checked" : ""} title="Standard-Einstellung">
                    </td>
                    <td>
                        <button class="deleteBtn" title="Datensatz löschen">🗑️</button>
                    </td>
                `;
                const standardCheckbox = tr.querySelector('.standardCheckbox');
                standardCheckbox.addEventListener('change', function() {
                    if (this.checked) {
                        document.querySelectorAll('.standardCheckbox').forEach(cb => {
                            if (cb !== this) cb.checked = false;
                        });
                        fetch(`/api/standorte/${s.id}`, {
                            method: "PUT",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ standard: 1 })
                        }).then(() => {
                            fetch('/api/standorte')
                                .then(res => res.json())
                                .then(standorte => {
                                    standorte.forEach(st => {
                                        if (st.id !== s.id && st.standard) {
                                            fetch(`/api/standorte/${st.id}`, {
                                                method: "PUT",
                                                headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ standard: 0 })
                                            });
                                        }
                                    });
                                });
                        });
                    } else {
                        this.checked = true;
                    }
                });
                tbody.appendChild(tr);
                tr.querySelectorAll('td[contenteditable="true"]').forEach(td => {
                    td.addEventListener("blur", () => {
                        const field = td.dataset.field;
                        const value = td.textContent;
                        fetch(`/api/standorte/${s.id}`, {
                            method: "PUT",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ [field]: value })
                        });
                    });
                    td.addEventListener("keydown", (ev) => {
                        if (ev.key === "Enter") {
                            ev.preventDefault();
                            td.blur();
                        }
                    });
                });
                tr.querySelector(".deleteBtn").addEventListener("click", () => {
                    if (confirm("Standort wirklich löschen?")) {
                        fetch(`/api/standorte/${s.id}`, { method: "DELETE" })
                            .then(() => loadEinstellungen());
                    }
                });
            });
        });
}

function loadDruckvorlagen() {
    fetch('/api/druckvorlagen')
        .then(res => res.json())
        .then(data => {
            const tbody = document.querySelector("#druckvorlagenTable tbody");
            tbody.innerHTML = "";
            data.forEach(v => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td contenteditable="true" data-field="name">${v.name || ""}</td>
                    <td contenteditable="true" data-field="kuerzel">${v.kuerzel || ""}</td>
                    <td>
                        <div class="pfadCell">
                            <input type="text" class="pfadInput" data-field="pfad" value="${v.pfad || ""}" readonly>
                            <input type="file" class="pfadFile" title="Datei auswählen">
                        </div>
                    </td>
                    <td>
                        <button class="deleteDruckvorlageBtn" title="Datensatz löschen">🗑️</button>
                    </td>
                `;
                tbody.appendChild(tr);
                tr.querySelectorAll('td[contenteditable="true"]').forEach(td => {
                    td.addEventListener("blur", () => {
                        const field = td.dataset.field;
                        const value = td.textContent;
                        fetch(`/api/druckvorlagen/${v.id}`, {
                            method: "PUT",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ [field]: value })
                        });
                    });
                    td.addEventListener("keydown", (e) => {
                        if (e.key === "Enter") {
                            e.preventDefault();
                            td.blur();
                        }
                    });
                });
                const pfadInput = tr.querySelector(".pfadInput");
                const pfadFile = tr.querySelector(".pfadFile");
                pfadFile.addEventListener("change", () => {
                    if (pfadFile.files && pfadFile.files[0]) {
                        const filename = pfadFile.files[0].name;
                        const relativePath = `Vorlagen/${filename}`;
                        pfadInput.value = relativePath;
                        fetch(`/api/druckvorlagen/${v.id}`, {
                            method: "PUT",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ pfad: relativePath })
                        });
                    }
                });
                tr.querySelector(".deleteDruckvorlageBtn").addEventListener("click", () => {
                    if (confirm("Druckvorlage wirklich löschen?")) {
                        fetch(`/api/druckvorlagen/${v.id}`, { method: "DELETE" })
                            .then(() => loadDruckvorlagen());
                    }
                });
            });
        });
}

document.getElementById("addStandortBtn").addEventListener("click", () => {
    const tbody = document.querySelector("#standorteTable tbody");
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td contenteditable="true" data-field="name"></td>
        <td contenteditable="true" data-field="adresse"></td>
        <td contenteditable="true" data-field="plz"></td>
        <td contenteditable="true" data-field="ort"></td>
        <td contenteditable="true" data-field="email"></td>
        <td contenteditable="true" data-field="kuerzel"></td>
        <td contenteditable="true" data-field="bankname"></td>
        <td contenteditable="true" data-field="bic"></td>
        <td contenteditable="true" data-field="iban"></td>
        <td contenteditable="true" data-field="kontoName"></td>
        <td>
            <button class="saveBtn" title="Speichern">💾</button>
        </td>
    `;
    tbody.appendChild(tr);
    tr.querySelector(".saveBtn").addEventListener("click", () => {
        const cells = tr.querySelectorAll('td[contenteditable="true"]');
        const newData = {};
        cells.forEach(td => newData[td.dataset.field] = td.textContent);
        fetch("/api/standorte", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newData)
        }).then(() => loadEinstellungen());
    });
});

document.addEventListener("DOMContentLoaded", () => {
    loadEinstellungen();
    loadDruckvorlagen();
    loadProgrammvariablen();
});

document.getElementById("addDruckvorlageBtn").addEventListener("click", () => {
    const tbody = document.querySelector("#druckvorlagenTable tbody");
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td contenteditable="true" data-field="name"></td>
        <td contenteditable="true" data-field="kuerzel"></td>
        <td>
            <div class="pfadCell">
                <input type="text" class="pfadInput" data-field="pfad" readonly>
                <input type="file" class="pfadFile" title="Datei auswählen">
            </div>
        </td>
        <td>
            <button class="saveDruckvorlageBtn" title="Speichern">💾</button>
        </td>
    `;
    tbody.appendChild(tr);
    const pfadInput = tr.querySelector(".pfadInput");
    const pfadFile = tr.querySelector(".pfadFile");
    pfadFile.addEventListener("change", () => {
        if (pfadFile.files && pfadFile.files[0]) {
            const filename = pfadFile.files[0].name;
            pfadInput.value = `Vorlagen/${filename}`;
        }
    });
    tr.querySelector(".saveDruckvorlageBtn").addEventListener("click", () => {
        const nameCell = tr.querySelector('td[contenteditable="true"]');
        const newData = {
            name: nameCell ? nameCell.textContent : "",
            pfad: pfadInput.value
        };
        fetch("/api/druckvorlagen", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newData)
        }).then(() => loadDruckvorlagen());
    });
});

function loadProgrammvariablen() {
    fetch('/api/programmvariablen')
        .then(res => res.json())
        .then(data => {
            const tbody = document.querySelector("#programmvariablenTable tbody");
            tbody.innerHTML = "";
            // Logo-File laden und anzeigen
            const logoFile = data.find(v => v.name === "logo_file");
            if (logoFile && logoFile.wert) {
                let cleanPath = logoFile.wert.replace('/static/images/', '/static/');
                cleanPath = cleanPath.replace(/^\/static\//, 'Vorlagen/');
                document.getElementById("logoFileInput").value = cleanPath;
            } else {
                document.getElementById("logoFileInput").value = '';
            }
            // Standardtexte separat sammeln
            const standardtextVars = [
                "rechnung_text_oben", "rechnung_text_unten",
                "mahnung1_text_oben", "mahnung1_text_unten",
                "mahnung2_text_oben", "mahnung2_text_unten",
                "rechnung_text_email","mahnung_text_email"
            ];
            const standardtexte = [];
            data.forEach(v => {
                if (v.name === "logo_file") return;
                if (standardtextVars.includes(v.name)) {
                    standardtexte.push(v);
                    return;
                }
                const tr = document.createElement("tr");
                let tdContent = "";
                if (v.checkbox === true || v.checkbox === 1 || v.checkbox === "1") {
                    const checked = v.wert == "1" ? "checked" : "";
                    tdContent = `<input type="checkbox" data-field="wert" data-id="${v.id}" ${checked}>`;
                } else {
                    tdContent = `<td contenteditable="true" data-field="wert" data-id="${v.id}">${v.wert || ""}</td>`;
                }
                tr.innerHTML = `
                    <td>${v.bezeichnung}</td>
                    ${tdContent}
                `;
                tbody.appendChild(tr);
            });
            // Standardtexte in eigene Tabelle rendern
            const stdTbody = document.querySelector("#standardtexteTable tbody");
            stdTbody.innerHTML = "";
            standardtexte.forEach(v => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${v.bezeichnung}</td>
                    <td><textarea data-field="wert" data-id="${v.id}" style="width:100%;height:100px;">${v.wert || ""}</textarea></td>
                `;
                stdTbody.appendChild(tr);
            });
        });
}

// Logo-File Picker Handler
// ...existing code...

// Programmvariablen speichern
document.getElementById("saveProgrammvariablenBtn").addEventListener("click", () => {
    const tbody = document.querySelector("#programmvariablenTable tbody");
    const updates = [];

    tbody.querySelectorAll("tr").forEach(tr => {
        const checkbox = tr.querySelector('input[type="checkbox"][data-field="wert"]');
        if (checkbox) {
            const id = checkbox.dataset.id;
            const wert = checkbox.checked ? "1" : "0";
            updates.push({ id: parseInt(id), wert: wert });
        } else {
            const td = tr.querySelector('td[data-field="wert"]');
            if (td) {
                const id = td.dataset.id;
                const wert = td.textContent;
                updates.push({ id: parseInt(id), wert: wert });
            }
        }
    });

    Promise.all(updates.map(update =>
        fetch(`/api/programmvariablen/${update.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ wert: update.wert })
        })
    )).then(() => {
        alert("Gespeichert!");
        loadProgrammvariablen();
    }).catch(err => {
        console.error("Fehler beim Speichern:", err);
        alert("Fehler beim Speichern!");
    });
});

// Standardtexte speichern
document.getElementById("saveStandardtexteBtn").addEventListener("click", () => {
    const stdTbody = document.querySelector("#standardtexteTable tbody");
    const updates = [];

    stdTbody.querySelectorAll("tr").forEach(tr => {
        const textarea = tr.querySelector('textarea[data-field="wert"]');
        const id = textarea.dataset.id;
        const wert = textarea.value;
        updates.push({ id: parseInt(id), wert: wert });
    });

    Promise.all(updates.map(update =>
        fetch(`/api/programmvariablen/${update.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ wert: update.wert })
        })
    )).then(() => {
        alert("Standardtexte gespeichert!");
        loadProgrammvariablen();
    }).catch(err => {
        console.error("Fehler beim Speichern der Standardtexte:", err);
        alert("Fehler beim Speichern der Standardtexte!");
    });
});


// --- Leistungen (Routen) Tabelle ---
function loadLeistungen() {
    fetch('/api/leistungen')
        .then(res => res.json())
        .then(data => {
            const tbody = document.querySelector('#leistungenTable tbody');
            tbody.innerHTML = '';
            data.forEach(l => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td contenteditable="true" data-field="bezeichnung">${l.bezeichnung ?? ''}</td>
                    <td contenteditable="true" data-field="dauer_min">${l.dauer_min ?? ''}</td>
                    <td contenteditable="true" data-field="betrag">${l.betrag ?? ''}</td>
                    <td style="text-align:center;">
                        <input type="checkbox" class="gruppeCheckbox" data-field="gruppe" ${l.gruppe ? 'checked' : ''}>
                    </td>
                    <td><button class="deleteLeistungBtn" title="Löschen">🗑️</button></td>
                `;
                tbody.appendChild(tr);
                // Edit handler for text fields
                tr.querySelectorAll('td[contenteditable="true"]').forEach(td => {
                    td.addEventListener('blur', () => {
                        const field = td.dataset.field;
                        const value = td.textContent;
                        fetch(`/api/leistungen/${l.id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ [field]: value })
                        });
                    });
                    td.addEventListener('keydown', ev => {
                        if (ev.key === 'Enter') {
                            ev.preventDefault();
                            td.blur();
                        }
                    });
                });
                // Edit handler for gruppe checkbox
                const gruppeCheckbox = tr.querySelector('.gruppeCheckbox');
                if (gruppeCheckbox) {
                    gruppeCheckbox.addEventListener('change', () => {
                        fetch(`/api/leistungen/${l.id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ gruppe: gruppeCheckbox.checked ? 1 : 0 })
                        });
                    });
                }
                // Delete handler
                tr.querySelector('.deleteLeistungBtn').addEventListener('click', () => {
                    if (confirm('Leistung wirklich löschen?')) {
                        fetch(`/api/leistungen/${l.id}`, { method: 'DELETE' })
                            .then(() => loadLeistungen());
                    }
                });
            });
        });
}

document.getElementById('addLeistungBtn').addEventListener('click', () => {
    const tbody = document.querySelector('#leistungenTable tbody');
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td contenteditable="true" data-field="bezeichnung"></td>
        <td contenteditable="true" data-field="dauer_min"></td>
        <td contenteditable="true" data-field="betrag"></td>
        <td style="text-align:center;">
            <input type="checkbox" class="gruppeCheckbox" data-field="gruppe">
        </td>
        <td><button class="saveLeistungBtn" title="Speichern">💾</button></td>
    `;
    tbody.appendChild(tr);
    tr.querySelector('.saveLeistungBtn').addEventListener('click', () => {
        const cells = tr.querySelectorAll('td[contenteditable="true"]');
        const newData = {};
        cells.forEach(td => newData[td.dataset.field] = td.textContent);
        // Gruppe-Checkbox Wert hinzufügen
        const gruppeCheckbox = tr.querySelector('.gruppeCheckbox');
        newData.gruppe = gruppeCheckbox && gruppeCheckbox.checked ? 1 : 0;
        fetch('/api/leistungen', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newData)
        }).then(() => loadLeistungen());
    });
});

document.addEventListener('DOMContentLoaded', function() {
	const btn = document.getElementById('rewriteCalendarBtn');
	const status = document.getElementById('rewriteCalendarStatus');
	if (btn) {
		btn.addEventListener('click', function() {
			btn.disabled = true;
			status.textContent = 'Bitte warten...';
			fetch('api/kalender/force_rewrite_all', {method: 'POST'})
				.then(r => r.json())
				.then(data => {
					if (data.success) {
						status.textContent = 'Fertig! ' + (data.logs ? data.logs.join(' | ') : '');
					} else {
						status.textContent = 'Fehler: ' + (data.error || 'Unbekannt');
					}
				})
				.catch(e => {
					status.textContent = 'Fehler beim Senden: ' + e;
				})
				.finally(() => {
					btn.disabled = false;
				});
		});
	}
    loadLeistungen();
});
