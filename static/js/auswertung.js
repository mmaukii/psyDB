document.addEventListener('DOMContentLoaded', function() {
    // Nur auf der Auswertungsseite aktiv
    if (!document.getElementById('auswertung-jahrestabelle')) return;

    // 1. Jahrestabelle laden und anzeigen
    fetch('/api/auswertung/jahrestabelle')
        .then(res => res.json())
        .then(data => {
            renderJahrestabelle(data);
        });

    // 2. Jahresauswahl laden
    fetch('/api/auswertung/jahre')
        .then(res => res.json())
        .then(jahre => {
            renderJahresDropdown(jahre);
            if (jahre.length > 0) {
                loadKundenTabelle(jahre[jahre.length-1]); // Standard: letztes Jahr
            }
        });

    function renderJahrestabelle(data) {
        let html = `<h3>Jahresübersicht</h3><table class="auswertung-table"><thead><tr>
            <th>Jahr</th><th>Einnahmen gesamt</th><th>USt-pflichtig</th><th>nicht USt-pflichtig</th>
            <th>abgehaltene Termine</th><th>Minuten</th><th>abgesagte Termine</th>
            <th>abgehaltene Gruppen</th><th>Gruppen-Minuten</th><th>abgesagte Gruppen</th>
        </tr></thead><tbody>`;
        for (const row of data) {
            html += `<tr>
                <td>${row.jahr}</td>
                <td>${row.einnahmen_gesamt.toFixed(2)} €</td>
                <td>${row.einnahmen_umsatzsteuerpflichtig.toFixed(2)} €</td>
                <td>${row.einnahmen_nicht_umsatzsteuerpflichtig.toFixed(2)} €</td>
                <td>${row.abgehaltene_termine}</td>
                <td>${row.abgehaltene_termine_min}</td>
                <td>${row.abgesagte_termine}</td>
                <td>${row.abgehaltene_gruppentermine}</td>
                <td>${row.abgehaltene_gruppentermine_min}</td>
                <td>${row.abgesagte_gruppentermine}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        document.getElementById('auswertung-jahrestabelle').innerHTML = html;
    }

    function renderJahresDropdown(jahre) {
        let html = `<label for="auswertung-jahr-select">Jahr wählen: </label><select id="auswertung-jahr-select">`;
        for (const j of jahre) {
            html += `<option value="${j}">${j}</option>`;
        }
        html += '</select>';
        document.getElementById('auswertung-jahresauswahl').innerHTML = html;
        document.getElementById('auswertung-jahr-select').addEventListener('change', function() {
            loadKundenTabelle(this.value);
        });
    }

    function loadKundenTabelle(jahr) {
        fetch(`/api/auswertung/kunden?jahr=${jahr}`)
            .then(res => res.json())
            .then(data => renderKundenTabelle(data, jahr));
    }

    function renderKundenTabelle(data, jahr) {
        let html = `<h3>Kunden-Auswertung für ${jahr}</h3><table class="auswertung-table"><thead><tr>
            <th>Kürzel</th><th>Einnahmen gesamt</th><th>USt-pflichtig</th><th>nicht USt-pflichtig</th>
            <th>abgehaltene Termine</th><th>Minuten</th><th>abgesagte Termine</th>
        </tr></thead><tbody>`;
        for (const row of data) {
            html += `<tr>
                <td>${row.kuerzel}</td>
                <td>${row.einnahmen_gesamt.toFixed(2)} €</td>
                <td>${row.einnahmen_umsatzsteuerpflichtig.toFixed(2)} €</td>
                <td>${row.einnahmen_nicht_umsatzsteuerpflichtig.toFixed(2)} €</td>
                <td>${row.abgehaltene_termine}</td>
                <td>${row.abgehaltene_termine_min}</td>
                <td>${row.abgesagte_termine}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        document.getElementById('auswertung-kundentabelle').innerHTML = html;
    }
});
