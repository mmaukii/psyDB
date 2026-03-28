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
                loadGruppenTabelle(jahre[jahre.length-1]);
                loadTherapieformTabelle(jahre[jahre.length-1]);
            }
        });

    function renderJahrestabelle(data) {
        let html = `<h3>Jahresübersicht</h3><table class="auswertung-table"><thead><tr>
            <th>Jahr</th><th>Einnahmen gesamt</th><th>USt-pflichtig</th><th>nicht USt-pflichtig</th>
            <th>abgehaltene Termine</th><th>Stunden</th><th>abgesagte Termine</th>
            <th>abgehaltene Gruppen</th><th>Gruppen-Stunden</th><th>abgesagte Gruppen</th>
        </tr></thead><tbody>`;

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
    }

    function renderJahresDropdown(jahre) {
        let html = `<label for="auswertung-jahr-select">Jahr wählen: </label><select id="auswertung-jahr-select" style="width: 80px;">`;
        for (const j of jahre) {
            html += `<option value="${j}">${j}</option>`;
        }
        html += '</select>';
        document.getElementById('auswertung-jahresauswahl').innerHTML = html;
        document.getElementById('auswertung-jahr-select').addEventListener('change', function() {
            loadKundenTabelle(this.value);
            loadGruppenTabelle(this.value);
            loadTherapieformTabelle(this.value);
        });
    }
        function loadTherapieformTabelle(jahr) {
            fetch(`/api/auswertung/therapieformen?jahr=${jahr}`)
                .then(res => res.json())
                .then(data => renderTherapieformTabelle(data, jahr));
        }

        function renderTherapieformTabelle(data, jahr) {
            let html = `<h3>Therapieformen-Auswertung für ${jahr}</h3><table class="auswertung-table"><thead><tr>
                <th>Therapieform</th><th>Einnahmen gesamt</th><th>USt-pflichtig</th><th>nicht USt-pflichtig</th>
                <th>abgehaltene Termine</th><th>Stunden</th><th>abgesagte Termine</th>
            </tr></thead><tbody>`;
            
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
        }
    function loadGruppenTabelle(jahr) {
        fetch(`/api/auswertung/gruppen?jahr=${jahr}`)
            .then(res => res.json())
            .then(data => renderGruppenTabelle(data, jahr));
    }

    function renderGruppenTabelle(data, jahr) {
        let html = `<h3>Gruppen-Auswertung für ${jahr}</h3><table class="auswertung-table"><thead><tr>
            <th>Kürzel</th><th>Einnahmen gesamt</th><th>USt-pflichtig</th><th>nicht USt-pflichtig</th>
            <th>abgehaltene Termine</th><th>Stunden</th><th>abgesagte Termine</th>
        </tr></thead><tbody>`;
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
    }

    function loadKundenTabelle(jahr) {
        fetch(`/api/auswertung/kunden?jahr=${jahr}`)
            .then(res => res.json())
            .then(data => renderKundenTabelle(data, jahr));
    }

    function renderKundenTabelle(data, jahr) {
        let html = `<h3>Kunden-Auswertung für ${jahr}</h3><table class="auswertung-table"><thead><tr>
            <th>Kürzel</th><th>Einnahmen gesamt</th><th>USt-pflichtig</th><th>nicht USt-pflichtig</th>
            <th>abgehaltene Termine</th><th>Stunden</th><th>abgesagte Termine</th>
        </tr></thead><tbody>`;

        // Summen-Variablen initialisieren
        let sum_einnahmen_gesamt = 0;
        let sum_einnahmen_umsatzsteuerpflichtig = 0;
        let sum_einnahmen_nicht_umsatzsteuerpflichtig = 0;
        let sum_abgehaltene_termine = 0;
        let sum_abgehaltene_termine_min = 0;
        let sum_abgesagte_termine = 0;

        for (const row of data) {
            html += `<tr>
                <td >${row.kuerzel}</td>
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
    }
});
