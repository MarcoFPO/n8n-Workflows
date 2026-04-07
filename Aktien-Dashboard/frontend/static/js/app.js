// ─── API ──────────────────────────────────────────────────────────────────────
const api = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, data) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async put(path, data) {
    const r = await fetch(path, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async uploadFile(file) {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

// ─── Formatierung ─────────────────────────────────────────────────────────────
const fmt = {
  eur: v => v == null ? "–" : new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(v),
  pct: v => v == null ? "–" : (v >= 0 ? "+" : "") + v.toFixed(2) + "%",
  num: (v, d = 2) => v == null ? "–" : new Intl.NumberFormat("de-DE", { maximumFractionDigits: d }).format(v),
  date: s => s ? new Date(s).toLocaleDateString("de-DE") : "–",
  colorClass: v => v == null ? "" : v > 0 ? "text-green" : v < 0 ? "text-red" : "text-muted",
};

// ─── Navigation ───────────────────────────────────────────────────────────────
function navigate(page) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll("nav a").forEach(a => a.classList.remove("active"));
  document.getElementById("page-" + page)?.classList.add("active");
  document.querySelector(`nav a[data-page="${page}"]`)?.classList.add("active");
  window.location.hash = page;
  if (page === "dashboard") loadDashboard();
  else if (page === "positionen") loadPositionen();
  else if (page === "steuern") loadSteuern();
  else if (page === "transaktionen") loadTransaktionen();
  else if (page === "wertpapiere") loadWertpapiere();
}

// ─── Notification ─────────────────────────────────────────────────────────────
function notify(msg, type = "success") {
  const el = document.getElementById("notification");
  el.textContent = msg;
  el.className = `show ${type}`;
  setTimeout(() => el.classList.remove("show"), 3500);
}

// ─── Chart-Instanzen ──────────────────────────────────────────────────────────
let portfolioChart = null;
let positionChart = null;
let _portfolioHistoryData = null;  // gecacht
let _positionHistoryData = null;   // gecacht
let _positionDailyGains = null;    // daily_gains für Position (neue Logik)
let _portfolioRange = "max";
let _positionRange = "max";

function _cutoffDate(range) {
  const now = new Date();
  const map = {
    "1mo":  new Date(now.getFullYear(), now.getMonth() - 1,  now.getDate()),
    "3mo":  new Date(now.getFullYear(), now.getMonth() - 3,  now.getDate()),
    "6mo":  new Date(now.getFullYear(), now.getMonth() - 6,  now.getDate()),
    "1yr":  new Date(now.getFullYear() - 1,  now.getMonth(), now.getDate()),
    "5yr":  new Date(now.getFullYear() - 5,  now.getMonth(), now.getDate()),
    "10yr": new Date(now.getFullYear() - 10, now.getMonth(), now.getDate()),
    "20yr": new Date(now.getFullYear() - 20, now.getMonth(), now.getDate()),
  };
  return map[range] || null;
}

function _filterByRange(data, range, datumKey = "datum") {
  const cutoff = _cutoffDate(range);
  if (!cutoff) return data;
  return data.filter(d => new Date(d[datumKey]) >= cutoff);
}

// ─── DASHBOARD ────────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [summary, history] = await Promise.all([
      api.get("/api/portfolio/summary"),
      _portfolioHistoryData ? Promise.resolve(_portfolioHistoryData) : api.get("/api/portfolio/daily-gains"),
    ]);

    // Aggregiere daily_gains zu Portfolio-Snapshots (aus daily_total_* Feldern)
    const byDate = {};
    for (const item of history) {
      if (!byDate[item.datum]) {
        byDate[item.datum] = {
          datum: item.datum,
          bestandswert: item.daily_total_wert || 0,
          investiert: item.daily_total_invested || 0,
          gewinn: item.daily_total_gewinn || 0
        };
      }
    }
    _portfolioHistoryData = Object.values(byDate).sort((a, b) => a.datum.localeCompare(b.datum));

    document.getElementById("karte-depotwert").textContent = fmt.eur(summary.total_value);
    document.getElementById("karte-investiert").textContent = fmt.eur(summary.total_invested);

    const gainEl = document.getElementById("karte-gewinn");
    gainEl.textContent = fmt.eur(summary.total_gain_unrealized);
    gainEl.className = "value " + fmt.colorClass(summary.total_gain_unrealized);

    const rendEl = document.getElementById("karte-rendite");
    rendEl.textContent = fmt.pct(summary.rendite_gesamt);
    rendEl.className = "value " + fmt.colorClass(summary.rendite_gesamt);

    document.getElementById("karte-positionen").textContent = summary.anzahl_positionen;
    document.getElementById("karte-verkaeufe").textContent = summary.anzahl_verkaeufe;

    renderPortfolioChart(_filterByRange(history, _portfolioRange));
  } catch (e) {
    console.error(e);
  }
}

function renderPortfolioChart(history) {
  if (!history.length) return;
  const ctx = document.getElementById("chart-portfolio").getContext("2d");
  if (portfolioChart) portfolioChart.destroy();
  portfolioChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: history.map(h => fmt.date(h.datum)),
      datasets: [
        {
          label: "Bestandswert (EUR)",
          data: history.map(h => h.bestandswert),
          borderColor: "#34c97a",
          backgroundColor: "transparent",
          fill: false,
          tension: 0.3,
          pointRadius: 0,
        },
        {
          label: "Investiert (EUR)",
          data: history.map(h => h.investiert),
          borderColor: "#f7c948",
          backgroundColor: "transparent",
          fill: false,
          tension: 0,
          pointRadius: 0,
          stepped: "before",
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { labels: { color: "#8b90a8", font: { size: 12 } } },
        tooltip: {
          callbacks: {
            label: ctx => " " + ctx.dataset.label + ": " +
              new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(ctx.raw),
          }
        }
      },
      scales: {
        x: { ticks: { color: "#8b90a8", maxTicksLimit: 10 }, grid: { color: "#2e3248" } },
        y: {
          ticks: { color: "#8b90a8", callback: v => new Intl.NumberFormat("de-DE", { notation: "compact", style: "currency", currency: "EUR" }).format(v) },
          grid: { color: "#2e3248" },
        },
      },
    },
  });
}

// ─── POSITIONEN ───────────────────────────────────────────────────────────────
let allHoldings = [];
let positionFilter = "aktiv";

async function loadPositionen() {
  const tbody = document.getElementById("holdings-tbody");
  tbody.innerHTML = `<tr><td colspan="9" class="loading">Lade...</td></tr>`;
  try {
    allHoldings = await api.get("/api/portfolio/holdings");
    renderPositionen();
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-red">Fehler: ${e.message}</td></tr>`;
  }
}

function renderPositionen() {
  const tbody = document.getElementById("holdings-tbody");
  tbody.innerHTML = "";

  const filtered = allHoldings.filter(h => {
    if (positionFilter === "aktiv") return !h.geschlossen;
    if (positionFilter === "geschlossen") return h.geschlossen;
    return true;
  });

  for (const h of filtered) {
    const tr = document.createElement("tr");
    if (h.geschlossen) tr.classList.add("row-geschlossen");

    const nameCell = h.geschlossen
      ? `<strong>${h.bezeichnung}</strong> <span class="badge badge-geschlossen">Geschlossen</span><br><span class="text-muted">${h.wkn}</span>`
      : `<strong>${h.bezeichnung}</strong><br><span class="text-muted">${h.wkn}</span>`;

    const zeitraumInfo = h.geschlossen && h.zeitraum
      ? `<br><span class="text-muted" style="font-size:11px">${fmt.date(h.zeitraum.von)} – ${fmt.date(h.zeitraum.bis)}</span>`
      : "";

    tr.innerHTML = `
      <td>${nameCell}${zeitraumInfo}</td>
      <td class="text-right">${fmt.num(h.stueck, 4)}</td>
      <td class="text-right">${fmt.eur(h.einstand_eur)}</td>
      <td class="text-right">${fmt.eur(h.einstand_kurs)}</td>
      <td class="text-right">${h.aktueller_kurs ? fmt.eur(h.aktueller_kurs) : '<span class="text-muted">–</span>'}</td>
      <td class="text-right">${h.aktueller_wert ? fmt.eur(h.aktueller_wert) : '<span class="text-muted">–</span>'}</td>
      <td class="text-right ${fmt.colorClass(h.gewinn_unrealisiert)}">${fmt.eur(h.gewinn_unrealisiert)}</td>
      <td class="text-right ${fmt.colorClass(h.rendite_prozent)}">${fmt.pct(h.rendite_prozent)}</td>
      <td><button class="btn btn-secondary" onclick="showPositionChart('${h.wkn}','${h.bezeichnung.replace(/'/g, "\\'")}')">Chart</button></td>
    `;
    tbody.appendChild(tr);
  }

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-muted" style="text-align:center">Keine Positionen</td></tr>`;
  }

  // Filter-Buttons aktualisieren
  document.querySelectorAll(".pos-filter").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.filter === positionFilter);
  });
}

function _buildBestandInvestTimeline(preise, kaeufe, verkaeufe) {
  // Alle Events chronologisch sortiert
  const events = [
    ...kaeufe.map(k => ({ datum: k.datum, stueck: k.anzahl, kosten: k.kosten, typ: "kauf" })),
    ...verkaeufe.map(v => ({ datum: v.datum, stueck: v.stueck, kosten: 0, typ: "verkauf" })),
  ].sort((a, b) => a.datum.localeCompare(b.datum));

  let bestand = 0;
  let investiert = 0;
  let eIdx = 0;

  return preise.map(p => {
    while (eIdx < events.length && events[eIdx].datum <= p.datum) {
      const ev = events[eIdx];
      if (ev.typ === "kauf") {
        bestand += ev.stueck;
        investiert += ev.kosten;
      } else {
        if (bestand > 1e-9) {
          const ratio = Math.min(ev.stueck / bestand, 1);
          investiert -= investiert * ratio;
          bestand -= ev.stueck;
          bestand = Math.max(0, bestand);
          investiert = Math.max(0, investiert);
        }
      }
      eIdx++;
    }
    return { bestand: Math.round(bestand * 1e6) / 1e6, investiert: Math.round(investiert * 100) / 100 };
  });
}

// Neue Funktion für Charts basierend auf daily_gains (wird aus showPositionChart aufgerufen)
function _renderPositionChartFromDailyGains(dailyGains) {
  if (!dailyGains.length) return;

  const filtered = _filterByRange(dailyGains, _positionRange);
  if (!filtered.length) return;

  const labels = filtered.map(d => fmt.date(d.datum));
  const preise = filtered.map(d => d.kurs_eur);
  const bestandWert = filtered.map(d => d.wert_eur);
  const investiert = filtered.map(d => d.invested_eur);

  if (positionChart) positionChart.destroy();
  positionChart = new Chart(
    document.getElementById("chart-position").getContext("2d"),
    {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Kurs je Stück (EUR)",
            data: preise,
            borderColor: "#4f8ef7",
            backgroundColor: "transparent",
            fill: false, tension: 0.3, pointRadius: 0, yAxisID: "yKurs",
          },
          {
            label: "Bestandswert (EUR)",
            data: bestandWert,
            borderColor: "#34c97a",
            backgroundColor: "transparent",
            fill: false, tension: 0.3, pointRadius: 0,
          },
          {
            label: "Investiert (EUR)",
            data: investiert,
            borderColor: "#f7c948",
            backgroundColor: "transparent",
            fill: false, tension: 0, pointRadius: 0, stepped: "before",
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: { labels: { color: "#8b90a8", font: { size: 12 } } },
          tooltip: {
            callbacks: {
              label: ctx => " " + ctx.dataset.label + ": " +
                new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(ctx.raw),
            }
          }
        },
        scales: {
          x: { ticks: { color: "#8b90a8", maxTicksLimit: 10 }, grid: { color: "#2e3248" } },
          yKurs: {
            type: "linear", position: "left",
            ticks: { color: "#4f8ef7", callback: v => new Intl.NumberFormat("de-DE", { notation: "compact", style: "currency", currency: "EUR" }).format(v) },
            grid: { color: "#2e3248" },
            title: { display: true, text: "Kurs je Stück", color: "#4f8ef7", font: { size: 11 } },
          },
          y: {
            type: "linear", position: "right",
            ticks: { color: "#34c97a", callback: v => new Intl.NumberFormat("de-DE", { notation: "compact", style: "currency", currency: "EUR" }).format(v) },
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Gesamt (EUR)", color: "#34c97a", font: { size: 11 } },
          },
        },
      },
    }
  );
}

// Alte Funktion (wird nicht mehr verwendet, aber bleibt für backward-compatibility)
function _renderPositionChart() {
  if (!_positionHistoryData) return;
  const data = _positionHistoryData;
  const preiseFull = data.preise || [];
  const preise = _filterByRange(preiseFull, _positionRange);
  if (!preise.length) return;

  const kaeufe = data.kaeufe || [];
  const verkaeufe = data.verkaeufe || [];
  const labels = preise.map(d => fmt.date(d.datum));
  const geschlossen = !!data.zeitraum?.bis;
  const timeline = _buildBestandInvestTimeline(preise, kaeufe, verkaeufe);
  const bestandWert = preise.map((p, i) => Math.round(timeline[i].bestand * p.kurs * 100) / 100);

  if (positionChart) positionChart.destroy();
  positionChart = new Chart(
    document.getElementById("chart-position").getContext("2d"),
    {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Kurs je Stück (EUR)",
            data: preise.map(d => d.kurs),
            borderColor: geschlossen ? "#8b90a8" : "#4f8ef7",
            backgroundColor: "transparent",
            fill: false, tension: 0.3, pointRadius: 0, yAxisID: "yKurs",
          },
          {
            label: "Bestandswert (EUR)",
            data: bestandWert,
            borderColor: "#34c97a",
            backgroundColor: "transparent",
            fill: false, tension: 0.3, pointRadius: 0,
          },
          {
            label: "Investiert (EUR)",
            data: timeline.map(t => t.investiert),
            borderColor: "#f7c948",
            backgroundColor: "transparent",
            fill: false, tension: 0, pointRadius: 0, stepped: "before",
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { intersect: false, mode: "index" },
        plugins: {
          legend: { labels: { color: "#8b90a8", font: { size: 12 } } },
          tooltip: {
            callbacks: {
              label: ctx => " " + ctx.dataset.label + ": " +
                new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(ctx.raw),
            }
          }
        },
        scales: {
          x: { ticks: { color: "#8b90a8", maxTicksLimit: 10 }, grid: { color: "#2e3248" } },
          yKurs: {
            type: "linear", position: "left",
            ticks: { color: "#4f8ef7", callback: v => new Intl.NumberFormat("de-DE", { notation: "compact", style: "currency", currency: "EUR" }).format(v) },
            grid: { color: "#2e3248" },
            title: { display: true, text: "Kurs je Stück", color: "#4f8ef7", font: { size: 11 } },
          },
          y: {
            type: "linear", position: "right",
            ticks: { color: "#34c97a", callback: v => new Intl.NumberFormat("de-DE", { notation: "compact", style: "currency", currency: "EUR" }).format(v) },
            grid: { drawOnChartArea: false },
            title: { display: true, text: "Gesamt (EUR)", color: "#34c97a", font: { size: 11 } },
          },
        },
      },
    }
  );
}

async function showPositionChart(wkn, bezeichnung) {
  document.getElementById("position-chart-title").textContent = bezeichnung;
  document.getElementById("position-chart-box").style.display = "block";
  document.getElementById("position-chart-box").scrollIntoView({ behavior: "smooth", block: "nearest" });
  _positionRange = "max";
  document.querySelectorAll(".pos-range-filter").forEach(b => b.classList.toggle("active", b.dataset.range === "max"));
  try {
    const dailyGains = await api.get(`/api/portfolio/daily-gains/${wkn}`);

    if (!dailyGains.length) {
      notify("Keine Daten für " + bezeichnung, "error");
      return;
    }

    // Speichere daily_gains und nutze neue Render-Funktion
    _positionDailyGains = dailyGains;
    _renderPositionChartFromDailyGains(dailyGains);
  } catch (e) {
    notify("Kein Kursverlauf verfügbar: " + e.message, "error");
  }
}

// ─── STEUERN ──────────────────────────────────────────────────────────────────
async function loadSteuern() {
  const container = document.getElementById("steuer-container");
  container.innerHTML = `<div class="loading">Berechne...</div>`;
  try {
    const data = await api.get("/api/portfolio/tax");

    let html = "";
    for (const [jahr, s] of Object.entries(data.nach_jahr)) {
      const farbe = s.steuer > 0 ? "text-red" : "text-green";
      html += `
        <div class="steuer-jahr">
          <h3>${jahr}</h3>
          <div class="steuer-grid">
            <div class="steuer-item"><div class="label">Erlöse</div><div class="val">${fmt.eur(s.erloes)}</div></div>
            <div class="steuer-item"><div class="label">Einstand</div><div class="val">${fmt.eur(s.einstand)}</div></div>
            <div class="steuer-item"><div class="label">Gewinn (brutto)</div><div class="val ${s.gewinn_brutto >= 0 ? "text-green" : "text-red"}">${fmt.eur(s.gewinn_brutto)}</div></div>
            <div class="steuer-item"><div class="label">Steuerpflichtig*</div><div class="val">${fmt.eur(s.gewinn_steuerpflichtig)}</div></div>
            <div class="steuer-item"><div class="label">Steuerlast (26,375%)</div><div class="val ${farbe}">${fmt.eur(s.steuer)}</div></div>
          </div>
        </div>`;
    }

    if (!Object.keys(data.nach_jahr).length) {
      html = `<div class="loading">Keine realisierten Gewinne vorhanden.</div>`;
    }

    // Detail-Tabelle
    if (data.events.length) {
      html += `<h2>Einzelne Verkäufe</h2>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Datum</th><th>Bezeichnung</th><th>Stück</th>
          <th class="text-right">Erlös</th><th class="text-right">Einstand</th>
          <th class="text-right">Gewinn</th><th class="text-right">Steuer*</th>
        </tr></thead><tbody>`;
      for (const e of data.events) {
        html += `<tr>
          <td>${fmt.date(e.datum)}</td>
          <td>${e.bezeichnung}<br><span class="text-muted">${e.wkn} | TF: ${(e.teilfreistellung * 100).toFixed(0)}%</span></td>
          <td>${fmt.num(e.stueck_verkauft, 4)}</td>
          <td class="text-right">${fmt.eur(e.erloes_eur)}</td>
          <td class="text-right">${fmt.eur(e.einstand_eur)}</td>
          <td class="text-right ${fmt.colorClass(e.gewinn_brutto)}">${fmt.eur(e.gewinn_brutto)}</td>
          <td class="text-right text-red">${fmt.eur(e.steuer)}</td>
        </tr>`;
      }
      html += `</tbody></table></div>
      <p class="text-muted" style="font-size:12px;margin-top:8px">* ohne Freibeträge (Sparerpauschbetrag etc.) — TF = Teilfreistellung</p>`;
    }

    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="text-red">Fehler: ${e.message}</div>`;
  }
}

// ─── TRANSAKTIONEN ────────────────────────────────────────────────────────────
let txPage = 0;
let txTypeFilter = null;

async function loadTransaktionen(reset = true) {
  if (reset) txPage = 0;
  const tbody = document.getElementById("tx-tbody");
  tbody.innerHTML = `<tr><td colspan="7" class="loading">Lade...</td></tr>`;
  try {
    const params = new URLSearchParams({ limit: 100, offset: txPage * 100 });
    if (txTypeFilter) params.append("tx_type", txTypeFilter);
    const data = await api.get("/api/transactions?" + params);

    tbody.innerHTML = "";
    for (const tx of data.items) {
      const typBadge = {
        kauf: "badge-kauf",
        verkauf: "badge-verkauf",
        uebertrag_ein: "badge-uebertrag",
        uebertrag_aus: "badge-uebertrag",
        waehrungsumbuchung: "badge-sonstig",
      }[tx.transaction_type] || "badge-sonstig";

      tbody.innerHTML += `<tr>
        <td>${fmt.date(tx.buchungstag)}</td>
        <td>${tx.bezeichnung}<br><span class="text-muted">${tx.wkn}</span></td>
        <td><span class="badge ${typBadge}">${tx.transaction_type}</span></td>
        <td class="text-right">${fmt.num(tx.stueck, 4)}</td>
        <td class="text-right">${tx.ausfuehrungskurs ? fmt.num(tx.ausfuehrungskurs, 2) + " " + tx.waehrung : "–"}</td>
        <td class="text-right ${tx.umsatz_eur < 0 ? "text-red" : ""}">${fmt.eur(tx.umsatz_eur)}</td>
      </tr>`;
    }

    document.getElementById("tx-count").textContent = `${data.total} Transaktionen`;
    document.getElementById("tx-prev").disabled = txPage === 0;
    document.getElementById("tx-next").disabled = (txPage + 1) * 100 >= data.total;
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-red">Fehler: ${e.message}</td></tr>`;
  }
}

// ─── WERTPAPIERE ──────────────────────────────────────────────────────────────
async function loadWertpapiere() {
  const tbody = document.getElementById("sec-tbody");
  tbody.innerHTML = `<tr><td colspan="6" class="loading">Lade...</td></tr>`;
  try {
    const securities = await api.get("/api/portfolio/securities");
    tbody.innerHTML = "";
    for (const s of securities) {
      tbody.innerHTML += `<tr class="sec-row" data-wkn="${s.wkn}">
        <td><strong>${s.wkn}</strong></td>
        <td>${s.bezeichnung}</td>
        <td><input value="${s.isin || ""}" placeholder="ISIN" data-field="isin"></td>
        <td><input value="${s.yahoo_ticker || ""}" placeholder="z.B. EUNL.DE" data-field="yahoo_ticker"></td>
        <td>
          <select data-field="teilfreistellung">
            <option value="0.30" ${s.teilfreistellung == 0.30 ? "selected" : ""}>30% (Aktien)</option>
            <option value="0.15" ${s.teilfreistellung == 0.15 ? "selected" : ""}>15% (Misch)</option>
            <option value="0.00" ${s.teilfreistellung == 0.00 ? "selected" : ""}>0% (Renten)</option>
          </select>
        </td>
        <td><button class="btn btn-secondary" onclick="saveWertpapier('${s.wkn}',this)">Speichern</button></td>
      </tr>`;
    }
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-red">Fehler: ${e.message}</td></tr>`;
  }
}

async function saveWertpapier(wkn, btn) {
  const row = btn.closest("tr");
  const data = {};
  row.querySelectorAll("[data-field]").forEach(el => {
    data[el.dataset.field] = el.tagName === "SELECT" ? parseFloat(el.value) : el.value;
  });
  try {
    await api.put(`/api/portfolio/securities/${wkn}`, data);
    notify("Gespeichert: " + wkn);
  } catch (e) {
    notify("Fehler: " + e.message, "error");
  }
}

// ─── UPLOAD ───────────────────────────────────────────────────────────────────
function initUpload() {
  const area = document.getElementById("upload-area");
  const input = document.getElementById("file-input");
  const log = document.getElementById("import-log");

  area.addEventListener("click", () => input.click());
  area.addEventListener("dragover", e => { e.preventDefault(); area.classList.add("drag"); });
  area.addEventListener("dragleave", () => area.classList.remove("drag"));
  area.addEventListener("drop", e => {
    e.preventDefault();
    area.classList.remove("drag");
    handleFiles(e.dataTransfer.files);
  });
  input.addEventListener("change", () => handleFiles(input.files));
}

async function handleFiles(files) {
  const log = document.getElementById("import-log");
  log.classList.add("show");
  log.innerHTML = "";

  for (const file of files) {
    log.innerHTML += `→ ${file.name} …\n`;
    try {
      const result = await api.uploadFile(file);
      if (result.typ === "umsaetze") {
        log.innerHTML += `  ✓ ${result.importiert} Transaktionen importiert, ${result.duplikate_ignoriert} Duplikate ignoriert, ${result.neue_wertpapiere} neue Wertpapiere\n`;
      } else if (result.typ === "anschaffungskosten") {
        log.innerHTML += `  ✓ ${result.importiert} Kauflots importiert (exakte Einstandspreise), ${result.duplikate_ignoriert} Duplikate ignoriert\n`;
      } else {
        log.innerHTML += `  ✓ Depotübersicht ${result.datum}: ${result.importiert} Positionen importiert\n`;
      }
      notify(`${file.name} importiert`);
    } catch (e) {
      log.innerHTML += `  ✗ Fehler: ${e.message}\n`;
      notify(`Fehler bei ${file.name}`, "error");
    }
  }
}

async function updateKurse() {
  const btn = document.getElementById("btn-kurse");
  btn.disabled = true;
  btn.textContent = "Aktualisiere…";
  try {
    const result = await api.post("/api/portfolio/prices/update", {});
    const details = Object.entries(result.details).map(([wkn, s]) => `${wkn}: ${s}`).join("\n");
    const log = document.getElementById("import-log");
    log.classList.add("show");
    log.innerHTML = "Kurse aktualisiert:\n" + details;
    notify("Kurse aktualisiert");
  } catch (e) {
    notify("Fehler bei Kursabfrage", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Kurse aktualisieren";
  }
}

// ─── Chart Defaults ───────────────────────────────────────────────────────────
function chartDefaults(unit) {
  return {
    responsive: true,
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { labels: { color: "#8b90a8", font: { size: 12 } } },
      tooltip: {
        callbacks: {
          label: ctx => {
            const v = ctx.raw;
            return " " + ctx.dataset.label + ": " +
              new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(v);
          }
        }
      }
    },
    scales: {
      x: { ticks: { color: "#8b90a8", maxTicksLimit: 10 }, grid: { color: "#2e3248" } },
      y: {
        ticks: {
          color: "#8b90a8",
          callback: v => new Intl.NumberFormat("de-DE", { notation: "compact", currency: "EUR", style: "currency" }).format(v)
        },
        grid: { color: "#2e3248" }
      }
    }
  };
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("nav a[data-page]").forEach(a => {
    a.addEventListener("click", e => { e.preventDefault(); navigate(a.dataset.page); });
  });

  document.getElementById("tx-prev").addEventListener("click", () => { txPage--; loadTransaktionen(false); });
  document.getElementById("tx-next").addEventListener("click", () => { txPage++; loadTransaktionen(false); });

  document.querySelectorAll(".tx-filter").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tx-filter").forEach(b => b.classList.remove("active"));
      txTypeFilter = btn.dataset.type || null;
      btn.classList.add("active");
      loadTransaktionen();
    });
  });

  document.querySelectorAll(".pos-filter").forEach(btn => {
    btn.addEventListener("click", () => {
      positionFilter = btn.dataset.filter;
      renderPositionen();
    });
  });

  document.querySelectorAll(".range-filter").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".range-filter").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      _portfolioRange = btn.dataset.range;
      if (_portfolioHistoryData) {
        // Nutze aggregierte Daten aus daily_gains
        renderPortfolioChart(_filterByRange(_portfolioHistoryData, _portfolioRange));
      }
    });
  });

  document.querySelectorAll(".pos-range-filter").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pos-range-filter").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      _positionRange = btn.dataset.range;
      // Neue Logik: daily_gains verwenden
      if (_positionDailyGains) {
        _renderPositionChartFromDailyGains(_positionDailyGains);
      } else if (_positionHistoryData) {
        _renderPositionChart();
      }
    });
  });

  initUpload();

  const page = window.location.hash.replace("#", "") || "dashboard";
  navigate(page);
});
