// Atmos AI dashboard - talks only to the public REST API
const API = "/api/v1";
const CAT = { VFR: "#3ddc84", MVFR: "#4aa3ff", IFR: "#ff5c5c", LIFR: "#d36cff" };
const LEVEL = { NORMAL: "#3ddc84", CAUTION: "#f5b83d", ADVERSE: "#ff5c5c" };
const charts = {};
let selected = new URLSearchParams(location.search).get("icao") || "VIDP";

Chart.defaults.color = "#8796a5";
Chart.defaults.font.family = "Inter, system-ui, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.borderColor = "#1e2935";

// Static mode (GitHub Pages demo): the same API responses are read from saved JSON files
const STATIC = window.ATMOS_STATIC === true;
const get = (p) => fetch(STATIC ? "data" + p.split("?")[0] + ".json" : API + p).then((r) => r.json());
const chip = (c) => `<span class="chip" style="background:${CAT[c]}">${c}</span>`;
const hhmm = (iso) => iso.slice(11, 16);
const fmtVis = (m) => (m >= 9999 ? "10+ km" : m >= 1000 ? (m / 1000).toFixed(1) + " km" : m + " m");

async function loadNetwork() {
  const net = await get("/network");
  document.getElementById("network").innerHTML = net.map((a) => `
    <li class="net-row ${a.icao === selected ? "active" : ""}" data-icao="${a.icao}">
      <div><b>${a.icao}</b> <small><span class="adv-dot" style="background:${LEVEL[a.advisory_level]}"></span>${a.city} · ${a.advisory_level}</small></div>
      ${chip(a.flight_category)}${chip(a.predicted_category)}
    </li>`).join("");
  document.querySelectorAll(".net-row").forEach((el) =>
    el.addEventListener("click", () => { selected = el.dataset.icao; loadNetwork(); loadAirport(); }));
}

async function loadMeta() {
  const [h, m] = await Promise.all([get("/health"), get("/models")]);
  document.getElementById("mode").textContent = STATIC ? "Live demo · sample-data snapshot" : h.data_source === "sample" ? "Sample data mode" : "Live · Open-Meteo";
  if (STATIC) { const a = document.querySelector(".pill.link"); a.href = "api.html"; }
  const t = new Date(h.now);
  document.getElementById("clock").textContent = t.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) + " IST";
  const best = m.category.comparison[m.category.best_model];
  const base = m.category.comparison["persistence (no model)"];
  document.getElementById("modelbox").innerHTML = `
    <h3>Model (test set)</h3>
    <div><span>Category accuracy</span><b>${(best.accuracy * 100).toFixed(1)}%</b></div>
    <div><span>Persistence baseline</span><b>${(base.accuracy * 100).toFixed(1)}%</b></div>
    <div><span>Visibility MAE</span><b>${(m.visibility.mae_m / 1000).toFixed(2)} km</b></div>
    <div><span>Thunderstorm ROC-AUC</span><b>${m.thunder.roc_auc.toFixed(2)}</b></div>`;
}

async function loadAirport() {
  const [aps, cur, adv, fc, br] = await Promise.all([
    get("/airports"), get(`/airports/${selected}/current`), get(`/airports/${selected}/advisory`),
    get(`/airports/${selected}/forecast?hours=24`), get(`/airports/${selected}/briefing`)]);
  const ap = aps.find((a) => a.icao === selected);
  document.getElementById("ap-title").textContent = `${ap.icao} · ${ap.city}`;
  document.getElementById("ap-sub").textContent = `${ap.name} · elev ${ap.elevation_m} m · RWY ${ap.runways.join(" / ")}`;

  const box = document.getElementById("advisory");
  box.style.borderColor = LEVEL[adv.level]; box.style.background = LEVEL[adv.level] + "14";
  document.getElementById("adv-level").textContent = adv.level;
  document.getElementById("adv-level").style.color = LEVEL[adv.level];
  document.getElementById("adv-score").innerHTML = `risk ${adv.score}/100<br>next ${adv.valid_for_hours} h: ${adv.predicted_category}`;
  document.getElementById("reasons").innerHTML = adv.reasons.map((r) => `<li>${r}</li>`).join("");

  const cards = [
    ["Flight category", cur.flight_category, "observed now", CAT[cur.flight_category]],
    ["Visibility", fmtVis(cur.visibility_m), cur.weather_code === 45 ? "fog" : "prevailing"],
    ["Ceiling", cur.ceiling_ft ? cur.ceiling_ft + " ft" : "None", cur.ceiling_ft ? "BKN/OVC" : "no low cloud"],
    ["Wind", `${String(cur.wind_direction_deg).padStart(3, "0")}° / ${cur.wind_speed_kt} kt`, `gust ${cur.wind_gust_kt} kt`],
    ["Temp / Dew pt", `${cur.temperature_c.toFixed(0)}° / ${cur.dewpoint_c.toFixed(0)}°C`, `RH ${cur.humidity_pct}%`],
    ["QNH · Density alt", `${cur.qnh_hpa} hPa`, `DA ${cur.density_altitude_ft.toLocaleString()} ft`],
  ];
  document.getElementById("cards").innerHTML = cards.map(([l, v, s, c]) =>
    `<div class="card"><label>${l}</label><div class="v" style="${c ? "color:" + c : ""}">${v}</div><div class="s">${s}</div></div>`).join("");

  document.querySelector("#runways tbody").innerHTML = adv.runway.all.map((r) =>
    `<tr><td><b>${r.runway}</b></td><td style="color:${r.headwind_kt >= 0 ? "#3ddc84" : "#ff5c5c"}">${r.headwind_kt >= 0 ? "H " : "T "}${Math.abs(r.headwind_kt).toFixed(0)} kt</td><td>${r.crosswind_kt.toFixed(0)} kt</td></tr>`).join("");
  document.getElementById("briefing").textContent = br.text;

  const labels = fc.map((f) => hhmm(f.valid_time));
  const obsLabels = fc.map((f) => hhmm(f.issued_from));
  draw("visChart", {
    type: "line",
    data: { labels, datasets: [
      { label: "Model +3 h", data: fc.map((f) => f.predicted_visibility_m / 1000), borderColor: "#4cc9f0", backgroundColor: "#4cc9f022", fill: true, tension: .3, pointRadius: 0 },
      { label: "Actual at valid time", data: fc.map((f, i) => (fc[i + 3] ? fc[i + 3].visibility_m / 1000 : null)), borderColor: "#e6edf3", borderDash: [4, 4], tension: .3, pointRadius: 0 },
    ] },
    options: { scales: { y: { type: "logarithmic", min: 0.05, max: 25, title: { display: true, text: "km (log)" } } } },
  });
  draw("catChart", {
    type: "bar",
    data: { labels, datasets: ["VFR", "MVFR", "IFR", "LIFR"].map((c) => ({ label: c, data: fc.map((f) => f.probabilities[c] * 100), backgroundColor: CAT[c], borderWidth: 0 })) },
    options: { scales: { x: { stacked: true }, y: { stacked: true, max: 100, title: { display: true, text: "%" } } } },
  });
  draw("windChart", {
    data: { labels: obsLabels, datasets: [
      { type: "line", label: "Wind kt", data: fc.map((f) => f.wind_speed_kt), borderColor: "#4cc9f0", pointRadius: 0, tension: .3, yAxisID: "y" },
      { type: "line", label: "Gust kt", data: fc.map((f) => f.wind_gust_kt), borderColor: "#f5b83d", borderDash: [3, 3], pointRadius: 0, tension: .3, yAxisID: "y" },
      { type: "bar", label: "Thunderstorm %", data: fc.map((f) => f.thunderstorm_probability * 100), backgroundColor: "#ff5c5c88", yAxisID: "y1" },
    ] },
    options: { scales: { y: { title: { display: true, text: "kt" } }, y1: { position: "right", max: 100, grid: { display: false }, title: { display: true, text: "%" } } } },
  });
}

function draw(id, cfg) {
  if (charts[id]) charts[id].destroy();
  cfg.options = Object.assign({ responsive: true, maintainAspectRatio: false, animation: false,
    plugins: { legend: { labels: { boxWidth: 10, boxHeight: 10 } } } }, cfg.options);
  charts[id] = new Chart(document.getElementById(id), cfg);
}

loadMeta(); loadNetwork(); loadAirport();
setInterval(() => { loadNetwork(); loadAirport(); }, 5 * 60 * 1000);
