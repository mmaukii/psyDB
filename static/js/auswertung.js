document.addEventListener('DOMContentLoaded', function() {
    // Nur auf der Auswertungsseite aktiv
    if (!document.getElementById('auswertung-jahrestabelle')) return;

    // 1. Jahrestabelle laden und anzeigen
    fetch('/api/auswertung/jahrestabelle')
        .then(res => res.json())
        .then(data => {
            renderJahrestabelle(data);
        });

        // Rechnungs-Tabelle Bereich vorbereiten
        if (document.getElementById('auswertung-rechnungstabelle')) {
            // Standard: höchstes Jahr vorauswählen
            fetch('/api/auswertung/jahre')
                .then(res => res.json())
                .then(jahre => {
                    if (jahre.length > 0) {
                        const maxJahr = Math.max(...jahre.map(Number));
                        loadRechnungsTabelle(maxJahr);
                        // Dropdown für Rechnungsjahr
                        let html = `<label for="auswertung-rechnungsjahr-select">Jahr wählen: </label><select id="auswertung-rechnungsjahr-select" style="width: 80px;">`;
                        for (const j of jahre) {
                            html += `<option value="${j}"${j == maxJahr ? ' selected' : ''}>${j}</option>`;
                        }
                        html += '</select>';
                        const jahrAuswahlElem = document.getElementById('auswertung-rechnungsjahr-auswahl');
                        if (jahrAuswahlElem) {
                            jahrAuswahlElem.innerHTML = html;
                            const jahrSelectElem = document.getElementById('auswertung-rechnungsjahr-select');
                            if (jahrSelectElem) {
                                jahrSelectElem.addEventListener('change', function() {
                                    loadRechnungsTabelle(this.value);
                                });
                            }
                        }
                    }
                });
        }

        function loadRechnungsTabelle(jahr) {
            fetch('/api/rechnungen/mit-kunde')
                .then(res => res.json())
                .then(data => {
                    // Nach Jahr filtern
                    console.log("länge", data.length);
                    const gefiltert = data.filter(r => {
                        if (!r.datum) return false;
                        // Datum im Format YYYY-MM-DD
                        return r.datum.startsWith(jahr.toString());
                    });
                    console.log("gefiltert", gefiltert.length);
                    renderRechnungsTabelle(gefiltert, jahr);
                });
        }


        function renderRechnungsTabelle(data, jahr) {
            // Daten sind bereits nach Jahr gefiltert
            console.log("renderRechnungsTabelle", data);
            let html = `<h3>Rechnungen für ${jahr}</h3>`;
            // Sortierbare Spalten definieren
            const columns = [
                { key: 'rechnungsnr', label: 'Rechnungsnr' },
                { key: 'datum', label: 'Datum' },
                { key: 'kuerzel', label: 'Kürzel' },
                { key: 'zahlungsverweis', label: 'Zahlungsverweis' },
                { key: 'offen', label: 'Offener Betrag' },
                { key: 'bezahlt', label: 'Bezahlter Betrag' }
            ];
            // Sortierstatus merken
            if (!window.rechnungSort) window.rechnungSort = { col: null, asc: true };
            function sortData(colKey) {
                if (window.rechnungSort.col === colKey) {
                    window.rechnungSort.asc = !window.rechnungSort.asc;
                } else {
                    window.rechnungSort.col = colKey;
                    window.rechnungSort.asc = true;
                }
                data.sort((a, b) => {
                    let va, vb;
                    if (colKey === 'offen') {
                        va = (!a.bezahlt || a.bezahlt == 0) ? (a.betrag || 0) : 0;
                        vb = (!b.bezahlt || b.bezahlt == 0) ? (b.betrag || 0) : 0;
                    } else if (colKey === 'bezahlt') {
                        va = (a.bezahlt && a.bezahlt != 0) ? (a.betrag || 0) : 0;
                        vb = (b.bezahlt && b.bezahlt != 0) ? (b.betrag || 0) : 0;
                    } else {
                        va = a[colKey] || '';
                        vb = b[colKey] || '';
                    }
                    if (typeof va === 'string' && typeof vb === 'string') {
                        return window.rechnungSort.asc ? va.localeCompare(vb) : vb.localeCompare(va);
                    } else {
                        return window.rechnungSort.asc ? va - vb : vb - va;
                    }
                });
                renderRechnungsTabelle(data, jahr);
            }
            html += `<table class="auswertung-table"><thead><tr>`;
            columns.forEach(col => {
                let icon = '';
                if (window.rechnungSort.col === col.key) {
                    icon = window.rechnungSort.asc ? '▲' : '▼';
                } else {
                    icon = '↕';
                }
                html += `<th style="cursor:pointer;user-select:none;" onclick="window.rechnungSortCol && window.rechnungSortCol('${col.key}')">${col.label} <span style='font-size:0.8em;'>${icon}</span></th>`;
            });
            html += `</tr></thead><tbody>`;
            let sum_offen = 0;
            let sum_bezahlt = 0;
            for (const r of data) {
                let offen = (!r.bezahlt || r.bezahlt == 0) ? (r.betrag || 0) : 0;
                let bezahlt = (r.bezahlt && r.bezahlt != 0) ? (r.betrag || 0) : 0;
                sum_offen += offen;
                sum_bezahlt += bezahlt;
                html += `<tr>` +
                    `<td>${r.rechnungsnr || ''}</td>` +
                    `<td>${r.datum ? r.datum.substring(0,10) : ''}</td>` +
                    `<td>${r.kuerzel || ''}</td>` +
                    `<td>${r.zahlungsverweis || ''}</td>` +
                    `<td style=\"text-align:right;\">${offen > 0 ? offen.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' €' : ''}</td>` +
                    `<td style=\"text-align:right;\">${bezahlt > 0 ? bezahlt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' €' : ''}</td>` +
                    `</tr>`;
            }
            html += `<tr style="font-weight:bold;background:#f0f0f0;"><td colspan="4">Summe</td><td style="text-align:right;">${sum_offen.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td><td style="text-align:right;">${sum_bezahlt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td></tr>`;
            html += '</tbody></table>';
              document.getElementById('auswertung-rechnungstabelle').innerHTML = html;
              // Globale Sortierfunktion für OnClick
              window.rechnungSortCol = sortData;
        }

    // 2. Jahresauswahl laden
    fetch('/api/auswertung/jahre')
        .then(res => res.json())
        .then(jahre => {
            renderJahresDropdown(jahre);
            if (jahre.length > 0) {
                loadKundenTabelle(jahre[jahre.length-1]); // Standard: letztes Jahr
                loadGruppenTabelle(jahre[jahre.length-1]);
                loadTherapieformTabelle(jahre[jahre.length-1]);
            }
        });

    function renderJahrestabelle(data) {
        // Sortierbare Spalten
        const columns = [
            { key: 'jahr', label: 'Jahr' },
            { key: 'einnahmen_gesamt', label: 'Einnahmen gesamt' },
            { key: 'einnahmen_umsatzsteuerpflichtig', label: 'USt-pflichtig' },
            { key: 'einnahmen_nicht_umsatzsteuerpflichtig', label: 'nicht USt-pflichtig' },
            { key: 'abgehaltene_termine', label: 'verrechnete Termine' },
            { key: 'abgehaltene_termine_min', label: 'Arbeitszeit(h)' },
            { key: 'abgesagte_termine', label: 'abgesagte Termine' },
            { key: 'abgehaltene_gruppentermine', label: 'verrechnete Gruppen' },
            { key: 'abgehaltene_gruppentermine_min', label: 'Gruppen-Stunden' },
            { key: 'abgesagte_gruppentermine', label: 'abgesagte Gruppen' }
        ];
        if (!window.jahresSort) window.jahresSort = { col: null, asc: true };
        function sortData(colKey) {
            if (window.jahresSort.col === colKey) {
                window.jahresSort.asc = !window.jahresSort.asc;
            } else {
                window.jahresSort.col = colKey;
                window.jahresSort.asc = true;
            }
            data.sort((a, b) => {
                let va = a[colKey] || 0;
                let vb = b[colKey] || 0;
                if (typeof va === 'string' && typeof vb === 'string') {
                    return window.jahresSort.asc ? va.localeCompare(vb) : vb.localeCompare(va);
                } else {
                    return window.jahresSort.asc ? va - vb : vb - va;
                }
            });
            renderJahrestabelle(data);
        }
        let html = `<h3>Jahresübersicht</h3><table class="auswertung-table"><thead><tr>`;
        columns.forEach(col => {
            let icon = '';
            if (window.jahresSort.col === col.key) {
                icon = window.jahresSort.asc ? '▲' : '▼';
            } else {
                icon = '↕';
            }
            html += `<th style=\"cursor:pointer;user-select:none;\" onclick=\"window.jahresSortCol && window.jahresSortCol('${col.key}')\">${col.label} <span style='font-size:0.8em;'>${icon}</span></th>`;
        });
        html += `</tr></thead><tbody>`;

        // Summen-Variablen initialisieren
        let sum_einnahmen_gesamt = 0;
        let sum_einnahmen_umsatzsteuerpflichtig = 0;
        let sum_einnahmen_nicht_umsatzsteuerpflichtig = 0;
        let sum_abgehaltene_termine = 0;
        let sum_abgehaltene_termine_min = 0;
        let sum_abgesagte_termine = 0;
        let sum_abgehaltene_gruppentermine = 0;
        let sum_abgehaltene_gruppentermine_min = 0;
        let sum_abgesagte_gruppentermine = 0;

        for (const row of data) {
            html += `<tr>
                <td>${row.jahr}</td>
                <td style="text-align:right;">${row.einnahmen_gesamt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.einnahmen_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.einnahmen_nicht_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.abgehaltene_termine}</td>
                <td style="text-align:right;">${(row.abgehaltene_termine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                <td style="text-align:right;">${row.abgesagte_termine}</td>
                <td style="text-align:right;">${row.abgehaltene_gruppentermine}</td>
                <td style="text-align:right;">${(row.abgehaltene_gruppentermine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                <td style="text-align:right;">${row.abgesagte_gruppentermine}</td>
            </tr>`;
            sum_einnahmen_gesamt += row.einnahmen_gesamt;
            sum_einnahmen_umsatzsteuerpflichtig += row.einnahmen_umsatzsteuerpflichtig;
            sum_einnahmen_nicht_umsatzsteuerpflichtig += row.einnahmen_nicht_umsatzsteuerpflichtig;
            sum_abgehaltene_termine += row.abgehaltene_termine;
            sum_abgehaltene_termine_min += row.abgehaltene_termine_min;
            sum_abgesagte_termine += row.abgesagte_termine;
            sum_abgehaltene_gruppentermine += row.abgehaltene_gruppentermine;
            sum_abgehaltene_gruppentermine_min += row.abgehaltene_gruppentermine_min;
            sum_abgesagte_gruppentermine += row.abgesagte_gruppentermine;
        }

        // Summenzeile hinzufügen
        html += `<tr style="font-weight:bold;background:#f0f0f0;">
            <td>Summe</td>
            <td style="text-align:right;">${sum_einnahmen_gesamt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
            <td style="text-align:right;">${sum_einnahmen_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
            <td style="text-align:right;">${sum_einnahmen_nicht_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
            <td style="text-align:right;">${sum_abgehaltene_termine}</td>
            <td style="text-align:right;">${(sum_abgehaltene_termine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
            <td style="text-align:right;">${sum_abgesagte_termine}</td>
            <td style="text-align:right;">${sum_abgehaltene_gruppentermine}</td>
            <td style="text-align:right;">${(sum_abgehaltene_gruppentermine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
            <td style="text-align:right;">${sum_abgesagte_gruppentermine}</td>
        </tr>`;

        html += '</tbody></table>';
        document.getElementById('auswertung-jahrestabelle').innerHTML = html;
        window.jahresSortCol = sortData;
    }

    function renderJahresDropdown(jahre) {
        const maxJahr = Math.max(...jahre.map(Number));
        let html = `<label for="auswertung-jahr-select">Jahr wählen: </label><select id="auswertung-jahr-select" style="width: 80px;">`;
        for (const j of jahre) {
            html += `<option value="${j}"${j == maxJahr ? ' selected' : ''}>${j}</option>`;
        }
        html += '</select>';
        document.getElementById('auswertung-jahresauswahl').innerHTML = html;
        const jahrSelectElem = document.getElementById('auswertung-jahr-select');
        if (jahrSelectElem) {
            jahrSelectElem.addEventListener('change', function() {
                const jahr = this.value;
                loadKundenTabelle(jahr);
                loadGruppenTabelle(jahr);
                loadTherapieformTabelle(jahr);
                // Rechnungsjahresauswahl und Tabelle aktualisieren
                updateRechnungsjahrDropdown(jahr);
            });
        }
        // Initialdaten für höchstes Jahr laden
        loadKundenTabelle(maxJahr);
        loadGruppenTabelle(maxJahr);
        loadTherapieformTabelle(maxJahr);
        updateRechnungsjahrDropdown(maxJahr);
    }

    // Neue Hilfsfunktion, um Rechnungsjahr-Dropdown und Tabelle zu aktualisieren
    function updateRechnungsjahrDropdown(selectedJahr) {
        fetch('/api/auswertung/jahre')
            .then(res => res.json())
            .then(jahre => {
                let html = `<label for="auswertung-rechnungsjahr-select">Jahr wählen: </label><select id="auswertung-rechnungsjahr-select" style="width: 80px;">`;
                for (const j of jahre) {
                    html += `<option value="${j}"${j == selectedJahr ? ' selected' : ''}>${j}</option>`;
                }
                html += '</select>';
                const jahrAuswahlElem = document.getElementById('auswertung-rechnungsjahr-auswahl');
                if (jahrAuswahlElem) {
                    jahrAuswahlElem.innerHTML = html;
                    const jahrSelectElem = document.getElementById('auswertung-rechnungsjahr-select');
                    if (jahrSelectElem) {
                        jahrSelectElem.addEventListener('change', function() {
                            loadRechnungsTabelle(this.value);
                        });
                    }
                }
                // Tabelle für das gewählte Jahr laden
                loadRechnungsTabelle(selectedJahr);
            });
    }
        function loadTherapieformTabelle(jahr) {
            fetch(`/api/auswertung/therapieformen?jahr=${jahr}`)
                .then(res => res.json())
                .then(data => renderTherapieformTabelle(data, jahr));
        }

        function renderTherapieformTabelle(data, jahr) {
            // Sortierbare Spalten
            const columns = [
                { key: 'therapieform_bezeichnung', label: 'Therapieform' },
                { key: 'einnahmen_gesamt', label: 'Einnahmen gesamt' },
                { key: 'einnahmen_umsatzsteuerpflichtig', label: 'USt-pflichtig' },
                { key: 'einnahmen_nicht_umsatzsteuerpflichtig', label: 'nicht USt-pflichtig' },
                { key: 'abgehaltene_termine', label: 'verrechnete Termine' },
                { key: 'abgehaltene_termine_min', label: 'Arbeitszeit(h)' },
                { key: 'abgesagte_termine', label: 'abgesagte Termine' }
            ];
            if (!window.therapieSort) window.therapieSort = { col: null, asc: true };
            function sortData(colKey) {
                if (window.therapieSort.col === colKey) {
                    window.therapieSort.asc = !window.therapieSort.asc;
                } else {
                    window.therapieSort.col = colKey;
                    window.therapieSort.asc = true;
                }
                data.sort((a, b) => {
                    let va = a[colKey] || a['therapieform'] || 0;
                    let vb = b[colKey] || b['therapieform'] || 0;
                    if (typeof va === 'string' && typeof vb === 'string') {
                        return window.therapieSort.asc ? va.localeCompare(vb) : vb.localeCompare(va);
                    } else {
                        return window.therapieSort.asc ? va - vb : vb - va;
                    }
                });
                renderTherapieformTabelle(data, jahr);
            }
            let html = `<h3>Therapieformen-Auswertung für ${jahr}</h3><table class="auswertung-table"><thead><tr>`;
            columns.forEach(col => {
                let icon = '';
                if (window.therapieSort.col === col.key) {
                    icon = window.therapieSort.asc ? '▲' : '▼';
                } else {
                    icon = '↕';
                }
                html += `<th style=\"cursor:pointer;user-select:none;\" onclick=\"window.therapieSortCol && window.therapieSortCol('${col.key}')\">${col.label} <span style='font-size:0.8em;'>${icon}</span></th>`;
            });
            html += `</tr></thead><tbody>`;
            
            // Summen-Variablen initialisieren
            let sum_einnahmen_gesamt = 0;
            let sum_einnahmen_umsatzsteuerpflichtig = 0;
            let sum_einnahmen_nicht_umsatzsteuerpflichtig = 0;
            let sum_abgehaltene_termine = 0;
            let sum_abgehaltene_termine_min = 0;
            let sum_abgesagte_termine = 0;
            console.log(data);
            for (const row of data) {
                html += `<tr>
                    <td>${row.therapieform_bezeichnung || row.therapieform}</td>
                    <td style="text-align:right;">${row.einnahmen_gesamt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                    <td style="text-align:right;">${row.einnahmen_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                    <td style="text-align:right;">${row.einnahmen_nicht_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                    <td style="text-align:right;">${row.abgehaltene_termine}</td>
                    <td style="text-align:right;">${(row.abgehaltene_termine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                    <td style="text-align:right;">${row.abgesagte_termine}</td>
                </tr>`;
                sum_einnahmen_gesamt += row.einnahmen_gesamt;
                sum_einnahmen_umsatzsteuerpflichtig += row.einnahmen_umsatzsteuerpflichtig;
                sum_einnahmen_nicht_umsatzsteuerpflichtig += row.einnahmen_nicht_umsatzsteuerpflichtig;
                sum_abgehaltene_termine += row.abgehaltene_termine;
                sum_abgehaltene_termine_min += row.abgehaltene_termine_min;
                sum_abgesagte_termine += row.abgesagte_termine;
            }

            // Summenzeile hinzufügen
            html += `<tr style="font-weight:bold;background:#f0f0f0;">
                <td>Summe</td>
                <td style="text-align:right;">${sum_einnahmen_gesamt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${sum_einnahmen_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${sum_einnahmen_nicht_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${sum_abgehaltene_termine}</td>
                <td style="text-align:right;">${(sum_abgehaltene_termine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                <td style="text-align:right;">${sum_abgesagte_termine}</td>
            </tr>`;

            html += '</tbody></table>';
            document.getElementById('auswertung-therapieformtabelle').innerHTML = html;
            window.therapieSortCol = sortData;
        }
    function loadGruppenTabelle(jahr) {
        fetch(`/api/auswertung/gruppen?jahr=${jahr}`)
            .then(res => res.json())
            .then(data => renderGruppenTabelle(data, jahr));
    }

    function renderGruppenTabelle(data, jahr) {
        // Sortierbare Spalten
        const columns = [
            { key: 'kuerzel', label: 'Kürzel' },
            { key: 'einnahmen_gesamt', label: 'Einnahmen gesamt' },
            { key: 'einnahmen_umsatzsteuerpflichtig', label: 'USt-pflichtig' },
            { key: 'einnahmen_nicht_umsatzsteuerpflichtig', label: 'nicht USt-pflichtig' },
            { key: 'abgehaltene_termine', label: 'verrechnete Termine' },
            { key: 'abgehaltene_termine_min', label: 'Arbeitszeit(h)' },
            { key: 'abgesagte_termine', label: 'abgesagte Termine' }
        ];
        if (!window.gruppenSort) window.gruppenSort = { col: null, asc: true };
        function sortData(colKey) {
            if (window.gruppenSort.col === colKey) {
                window.gruppenSort.asc = !window.gruppenSort.asc;
            } else {
                window.gruppenSort.col = colKey;
                window.gruppenSort.asc = true;
            }
            data.sort((a, b) => {
                let va = a[colKey] || 0;
                let vb = b[colKey] || 0;
                if (typeof va === 'string' && typeof vb === 'string') {
                    return window.gruppenSort.asc ? va.localeCompare(vb) : vb.localeCompare(va);
                } else {
                    return window.gruppenSort.asc ? va - vb : vb - va;
                }
            });
            renderGruppenTabelle(data, jahr);
        }
        let html = `<h3>Gruppen-Auswertung für ${jahr}</h3><table class="auswertung-table"><thead><tr>`;
        columns.forEach(col => {
            let icon = '';
            if (window.gruppenSort.col === col.key) {
                icon = window.gruppenSort.asc ? '▲' : '▼';
            } else {
                icon = '↕';
            }
            html += `<th style=\"cursor:pointer;user-select:none;\" onclick=\"window.gruppenSortCol && window.gruppenSortCol('${col.key}')\">${col.label} <span style='font-size:0.8em;'>${icon}</span></th>`;
        });
        html += `</tr></thead><tbody>`;
        for (const row of data) {
            html += `<tr>
                <td>${row.kuerzel}</td>
                <td style="text-align:right;">${row.einnahmen_gesamt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.einnahmen_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.einnahmen_nicht_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.abgehaltene_termine}</td>
                <td style="text-align:right;">${(row.abgehaltene_termine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                <td style="text-align:right;">${row.abgesagte_termine}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        document.getElementById('auswertung-gruppentabelle').innerHTML = html;
        window.gruppenSortCol = sortData;
    }

    function loadKundenTabelle(jahr) {
        fetch(`/api/auswertung/kunden?jahr=${jahr}`)
            .then(res => res.json())
            .then(data => renderKundenTabelle(data, jahr));
    }

    function renderKundenTabelle(data, jahr) {
        // Sortierbare Spalten
        const columns = [
            { key: 'kuerzel', label: 'Kürzel' },
            { key: 'einnahmen_gesamt', label: 'Einnahmen gesamt' },
            { key: 'einnahmen_umsatzsteuerpflichtig', label: 'USt-pflichtig' },
            { key: 'einnahmen_nicht_umsatzsteuerpflichtig', label: 'nicht USt-pflichtig' },
            { key: 'abgehaltene_termine', label: 'verrechnete Termine' },
            { key: 'abgehaltene_termine_min', label: 'Arbeitszeit(h)' },
            { key: 'abgesagte_termine', label: 'abgesagte Termine' }
        ];
        if (!window.kundenSort) window.kundenSort = { col: null, asc: true };
        function sortData(colKey) {
            if (window.kundenSort.col === colKey) {
                window.kundenSort.asc = !window.kundenSort.asc;
            } else {
                window.kundenSort.col = colKey;
                window.kundenSort.asc = true;
            }
            data.sort((a, b) => {
                let va = a[colKey] || 0;
                let vb = b[colKey] || 0;
                if (typeof va === 'string' && typeof vb === 'string') {
                    return window.kundenSort.asc ? va.localeCompare(vb) : vb.localeCompare(va);
                } else {
                    return window.kundenSort.asc ? va - vb : vb - va;
                }
            });
            renderKundenTabelle(data, jahr);
        }
        let html = `<h3>Kunden-Auswertung für ${jahr}</h3><table class="auswertung-table"><thead><tr>`;
        columns.forEach(col => {
            let icon = '';
            if (window.kundenSort.col === col.key) {
                icon = window.kundenSort.asc ? '▲' : '▼';
            } else {
                icon = '↕';
            }
            html += `<th style=\"cursor:pointer;user-select:none;\" onclick=\"window.kundenSortCol && window.kundenSortCol('${col.key}')\">${col.label} <span style='font-size:0.8em;'>${icon}</span></th>`;
        });
        html += `</tr></thead><tbody>`;

        // Summen-Variablen initialisieren
        let sum_einnahmen_gesamt = 0;
        let sum_einnahmen_umsatzsteuerpflichtig = 0;
        let sum_einnahmen_nicht_umsatzsteuerpflichtig = 0;
        let sum_abgehaltene_termine = 0;
        let sum_abgehaltene_termine_min = 0;
        let sum_abgesagte_termine = 0;

        for (const row of data) {
            html += `<tr>
                <td>${row.kuerzel}</td>
                <td style="text-align:right;">${row.einnahmen_gesamt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.einnahmen_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.einnahmen_nicht_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
                <td style="text-align:right;">${row.abgehaltene_termine}</td>
                <td style="text-align:right;">${(row.abgehaltene_termine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
                <td style="text-align:right;">${row.abgesagte_termine}</td>
            </tr>`;
            sum_einnahmen_gesamt += row.einnahmen_gesamt;
            sum_einnahmen_umsatzsteuerpflichtig += row.einnahmen_umsatzsteuerpflichtig;
            sum_einnahmen_nicht_umsatzsteuerpflichtig += row.einnahmen_nicht_umsatzsteuerpflichtig;
            sum_abgehaltene_termine += row.abgehaltene_termine;
            sum_abgehaltene_termine_min += row.abgehaltene_termine_min;
            sum_abgesagte_termine += row.abgesagte_termine;
        }

        // Summenzeile hinzufügen
        html += `<tr style="font-weight:bold;background:#f0f0f0;">
            <td>Summe</td>
            <td style="text-align:right;">${sum_einnahmen_gesamt.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
            <td style="text-align:right;">${sum_einnahmen_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
            <td style="text-align:right;">${sum_einnahmen_nicht_umsatzsteuerpflichtig.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} €</td>
            <td style="text-align:right;">${sum_abgehaltene_termine}</td>
            <td style="text-align:right;">${(sum_abgehaltene_termine_min/60).toLocaleString('de-DE', {minimumFractionDigits: 1, maximumFractionDigits: 1})}</td>
            <td style="text-align:right;">${sum_abgesagte_termine}</td>
        </tr>`;

        html += '</tbody></table>';
        document.getElementById('auswertung-kundentabelle').innerHTML = html;
        window.kundenSortCol = sortData;
    }
});
