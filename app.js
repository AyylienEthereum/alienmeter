/* ============================================================
   AYYLIEN — shared frontend logic. No build step, no framework.
   Reads data.json / history.json / sightings.json written by backend.py.
   ============================================================ */
"use strict";

/* ---- config ---- */
// Bands low->high, index matches backend band.index (0..5).
const BANDS = [
  { name:"NOTHINGBURGER",   range:"00\u201314", color:"#3a8d72" },
  { name:"SWAMP GAS",       range:"15\u201329", color:"#5DD49C" },
  { name:"THAT'S WEIRD",    range:"30\u201349", color:"#A89844" },
  { name:"ROSWELL ENERGY",  range:"50\u201369", color:"#FFB347" },
  { name:"THEY'RE WATCHING",range:"70\u201389", color:"#9c3535" },
  { name:"CONTACT IMMINENT",range:"90\u2013100",color:"#7a6d9c" },
];
// Glow color per band index, for the active tile / score.
const BAND_GLOW = ["#00FF94","#5DD49C","#FFE066","#FFB347","#FF5252","#B49BFF"];

const FACTOR_META = {
  news_velocity:        { label:"News velocity",        source:"GDELT 2.0",        color:"#FFB347", srcColor:"#FF5252", max:14 },
  social_chatter:       { label:"Social chatter",       source:"Reddit + Bluesky", color:"#FF6FCF", srcColor:"#FF6FCF", max:12 },
  search_interest:      { label:"Search interest",      source:"Wikipedia",        color:"#FFE066", srcColor:"#FFE066", max:10 },
  geomagnetic:          { label:"Geomagnetic",          source:"NOAA",             color:"#7AFFD0", srcColor:"#7AFFD0", max:12 },
  asteroid_approach:    { label:"Asteroid approach",    source:"NASA",             color:"#5AC8FF", srcColor:"#5AC8FF", max:10 },
  solar_flares:         { label:"Solar flares",         source:"GOES",             color:"#FFB347", srcColor:"#FFB347", max:10 },
  seismic:              { label:"Seismic activity",     source:"USGS",             color:"#FFB347", srcColor:"#FFB347", max:5 },
  space_weather_alerts: { label:"Space weather alerts", source:"NOAA SWPC",        color:"#7AFFD0", srcColor:"#7AFFD0", max:6 },
  alien_variance:       { label:"Alien variance",       source:"Stochastic",       color:"#B49BFF", srcColor:"#B49BFF", max:5 },
};

const TICKER_EMOJI = { news:"\uD83D\uDCF0", reddit:"\uD83D\uDC7D", swpc:"\uD83D\uDEF0\uFE0F",
  seismic:"\uD83C\uDF0B", neo:"\u2604\uFE0F", bluesky:"\uD83E\uDD8B", default:"\uD83D\uDEF8" };

/* ---- helpers ---- */
async function fetchJSON(path) {
  const r = await fetch(path + "?t=" + Date.now(), { cache:"no-store" });
  if (!r.ok) throw new Error(path + " -> " + r.status);
  return r.json();
}
const $  = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
const clamp = (v,a,b) => Math.max(a, Math.min(b, v));
const fmt = (n) => (n>0?"+":"") + (Math.round(n*10)/10);
function relTime(iso) {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime())/1000;
  if (s<90) return Math.round(s)+"s";
  if (s<5400) return Math.round(s/60)+"m";
  if (s<129600) return Math.round(s/3600)+"h";
  return Math.round(s/86400)+"d";
}

/* ---- nav live pill (all pages) ---- */
function bindNav(data) {
  const pill = $("#nav-pill");
  if (pill && data) {
    const g = BAND_GLOW[data.band.index];
    pill.innerHTML = `<span class="live-dot pulse" style="background:${g};box-shadow:0 0 6px ${g},0 0 14px ${g}66"></span>`
      + `<span class="mn" style="font-size:10px;color:${g};letter-spacing:.16em;text-shadow:0 0 6px ${g}99">`
      + `${data.band.name.replace("PROBABLY ","")} \u00b7 ${Math.round(data.score)}</span>`;
  }
  const upd = $("#nav-updated");
  if (upd && data) upd.textContent = "UPDATED " + relTime(data.generated_at) + " AGO";
}

/* ============================================================ INDEX */
function initIndex(data) {
  // alert banner
  const banner = $("#alert-banner");
  if (banner) {
    if (data.deltas && data.deltas.d1h >= 5) {
      banner.classList.remove("hidden");
      $("#alert-delta").textContent = fmt(data.deltas.d1h);
    } else { banner.classList.add("hidden"); }
  }

  // gauge: needle angle maps score 0..100 -> -90..+90 deg
  const score = data.score;
  const angle = score * 1.8 - 90;
  const needle = $("#gauge-needle");
  if (needle) needle.setAttribute("transform", `rotate(${angle.toFixed(1)})`);
  const scoreEl = $("#gauge-score");
  if (scoreEl) scoreEl.textContent = Math.round(score);

  // band label + flavor
  const g = BAND_GLOW[data.band.index];
  const lvl = $("#band-name");
  if (lvl) {
    lvl.textContent = data.band.name;
    lvl.style.color = g;
    lvl.style.textShadow = `0 0 12px ${g}d9, 0 0 28px ${g}66`;
  }
  const flv = $("#band-flavor");
  if (flv) flv.textContent = "\u201c" + data.band.flavor + "\u201d";

  // band tiles + arrow
  const row = $("#band-row");
  if (row) {
    row.innerHTML = BANDS.map((b,i)=>`
      <div class="band-tile ${i===data.band.index?"active":""}">
        <div class="band-tile-name" style="color:${i===data.band.index?"":b.color}">${b.name}</div>
        <div class="band-tile-range">${b.range}</div>
      </div>`).join("");
  }
  const arrow = $("#band-arrow");
  if (arrow) arrow.style.left = ((data.band.index + 0.5)/6*100).toFixed(2) + "%";

  // deltas
  if (data.deltas) {
    if ($("#d1h"))  { $("#d1h").textContent  = "\u25b2 " + fmt(data.deltas.d1h) + " / 1H"; }
    if ($("#d24h")) { $("#d24h").textContent = "\u25b2 " + fmt(data.deltas.d24h) + " / 24H"; }
    if ($("#peak90")) $("#peak90").innerHTML = `90D PEAK <span class="glow-red" style="color:var(--red)">${data.deltas.peak90}</span>`;
  }

  // contributing factors
  const fg = $("#factor-grid");
  if (fg) {
    const entries = Object.entries(data.contributing_factors || {});
    fg.innerHTML = entries.map(([k,v])=>{
      const m = FACTOR_META[k] || { label:k, source:"", color:"#7AFFD0", srcColor:"#7AFFD0", max:10 };
      const pct = clamp(Math.abs(v)/m.max, 0, 1)*100;
      return `<div class="factor-card" style="border-color:${m.color}40;box-shadow:0 0 16px ${m.color}0a">
        <div class="row" style="justify-content:space-between;margin-bottom:8px">
          <span style="font-size:12.5px;color:#cdd1d8">${m.label}</span>
          <span class="mn" style="font-size:13px;color:${m.color};text-shadow:0 0 8px ${m.color}99">${fmt(v)}</span>
        </div>
        <div class="bar"><div class="fill" style="width:${pct}%;background:${m.color};box-shadow:0 0 10px ${m.color}8c"></div></div>
        <div class="mn" style="font-size:9.5px;color:var(--text-faint);margin-top:6px;letter-spacing:.12em">
          <span style="color:${m.srcColor}">${m.source}</span></div>
      </div>`;
    }).join("");
  }

  // daily report card
  const rep = data.daily_report || {};
  const setTxt = (id,v)=>{ const e=$("#"+id); if(e) e.textContent=v; };
  setTxt("rep-band", data.band.name);
  setTxt("rep-score", Math.round(score));
  setTxt("rep-d24", "\u25b2 " + fmt(data.deltas ? data.deltas.d24h : 0));
  setTxt("rep-sight", (data.sightings_total||0).toLocaleString());
  setTxt("rep-number", "#" + (rep.number ?? "\u2014"));
  setTxt("rep-daystamp", "DAY " + (rep.day ?? "\u2014") + " OF SURVEILLANCE \u00b7 " + (rep.date || ""));
  setTxt("rep-declass", rep.declassified || "");
  setTxt("rep-utc", rep.generated_utc || "");
  setTxt("rep-assessment", "\u201c" + (rep.assessment || "") + "\u201d");
  const drv = $("#rep-drivers");
  if (drv && rep.top_drivers) {
    drv.innerHTML = rep.top_drivers.map((d,i)=>
      `<div><span class="glow-amber" style="color:var(--amber)">${String(i+1).padStart(2,"0")}</span> \u00b7 ${escapeHTML(d)}</div>`).join("");
  }
  wireShare(data);

  // 7-day chart
  drawTrend($("#trend-svg"), data.history || []);

  // ticker
  const feed = $("#ticker-feed");
  if (feed) {
    const items = (data.ticker || []).slice(0, 9);
    feed.innerHTML = items.length ? items.map(t=>{
      const e = TICKER_EMOJI[t.type] || TICKER_EMOJI.default;
      const txt = t.url ? `<a href="${t.url}" target="_blank" rel="noopener">${escapeHTML(t.text)}</a>`
                        : `<span style="flex:1">${escapeHTML(t.text)}</span>`;
      return `<div class="ticker-row"><span style="font-size:15px">${e}</span>${txt}
        <span class="mn" style="font-size:10.5px;color:var(--text-faint)">${escapeHTML(t.source||"")}</span></div>`;
    }).join("") : `<div class="loading">No intel in feed yet \u2014 awaiting first fetch.</div>`;
  }
}

function escapeHTML(s){ return String(s).replace(/[&<>"']/g, c=>({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[c])); }

/* share + save-image actions on the daily report card */
function wireShare(data) {
  const url   = window.location.origin + window.location.pathname;
  const emoji = (data.band && data.band.emoji) || "\uD83D\uDC7D";
  const text  = `Global Alien Activity Index: ${Math.round(data.score)} \u2014 ${data.band.name} ${emoji} "${data.band.flavor}"`;
  const note  = $("#share-note");
  const flash = (m)=>{ if(note){ note.textContent=m; setTimeout(()=>note.textContent="",2500);} };

  const x = $("#btn-x");
  if (x) x.onclick = () => window.open(
    "https://twitter.com/intent/tweet?text=" + encodeURIComponent(text) + "&url=" + encodeURIComponent(url),
    "_blank","noopener,width=600,height=500");

  const tg = $("#btn-tg");
  if (tg) tg.onclick = () => window.open(
    "https://t.me/share/url?url=" + encodeURIComponent(url) + "&text=" + encodeURIComponent(text),
    "_blank","noopener,width=600,height=500");

  // Discord has no share-intent URL, so copy a ready-to-paste message to clipboard.
  const dc = $("#btn-dc");
  if (dc) dc.onclick = async () => {
    try { await navigator.clipboard.writeText(text + " " + url); flash("COPIED \u2014 PASTE IN DISCORD"); }
    catch(e){ flash("COPY FAILED"); }
  };

  const save = $("#btn-save");
  if (save) save.onclick = async () => {
    const card = $("#report-card");
    if (!card || typeof html2canvas === "undefined") { flash("IMAGE LIB NOT LOADED"); return; }
    flash("RENDERING\u2026");
    try {
      const canvas = await html2canvas(card, { backgroundColor:"#0a0d12", scale:2, useCORS:true, logging:false });
      const a = document.createElement("a");
      a.href = canvas.toDataURL("image/png");
      a.download = "ayylien-report-" + (data.daily_report && data.daily_report.number || "x") + ".png";
      a.click();
      flash("SAVED \u2014 ATTACH IT TO YOUR POST");
    } catch(e){ console.error(e); flash("RENDER FAILED"); }
  };
}

/* downsampled trend polyline into an existing <svg> with viewBox 0 0 1180 200 */
function drawTrend(svg, hist) {
  if (!svg) return;
  const W=1180, H=200, n=hist.length;
  if (!n) { return; }
  const pts = hist.slice(-180);
  const xs = (i)=> 20 + (i/(pts.length-1||1))*(W-40);
  const ys = (s)=> H-50 - (clamp(s,0,100)/100)*(H-70);
  const line = pts.map((p,i)=>`${xs(i).toFixed(1)},${ys(p.score).toFixed(1)}`).join(" ");
  const area = `20,${H} ` + line + ` ${xs(pts.length-1)},${H}`;
  svg.querySelector("#trend-area").setAttribute("points", area);
  svg.querySelector("#trend-line").setAttribute("points", line);
  svg.querySelector("#trend-glow").setAttribute("points", line);
  const last = pts[pts.length-1];
  const dot = svg.querySelector("#trend-now");
  if (dot) { dot.setAttribute("cx", xs(pts.length-1)); dot.setAttribute("cy", ys(last.score)); }
}

/* ============================================================ ARCHIVES */
function initArchives(hist) {
  if (!hist || !hist.length) return;
  // group by calendar day -> max score
  const byDay = {};
  for (const p of hist) {
    const d = (p.ts||"").slice(0,10);
    if (!d) continue;
    if (!(d in byDay) || p.score > byDay[d]) byDay[d] = p.score;
  }
  const days = Object.keys(byDay).sort();
  const scores = days.map(d=>byDay[d]);
  const allScores = hist.map(p=>p.score);

  const high = Math.max(...allScores);
  const avg  = Math.round(allScores.reduce((a,b)=>a+b,0)/allScores.length);
  const contactDays = scores.filter(s=>s>=90).length;
  const daysTracked = days.length;

  // streaks of days >= 50 (ROSWELL+)
  let cur=0, longest=0, run=0;
  for (const s of scores){ if(s>=50){run++; longest=Math.max(longest,run);} else run=0; }
  for (let i=scores.length-1;i>=0;i--){ if(scores[i]>=50) cur++; else break; }

  const set=(id,v)=>{ const e=$("#"+id); if(e) e.textContent=v; };
  set("st-high", high); set("st-cur", cur); set("st-longest", longest);
  set("st-avg", avg); set("st-contact", contactDays); set("st-days", daysTracked);

  drawHistory($("#hist-svg"), days, scores);
  drawHeatmap($("#heat-svg"), days, scores);
  buildNotable($("#notable-list"), byDay);
}

function bandOf(s){ if(s>=90)return 5; if(s>=70)return 4; if(s>=50)return 3; if(s>=30)return 2; if(s>=15)return 1; return 0; }

function drawHistory(svg, days, scores){
  if(!svg||!days.length) return;
  const W=1180,H=320, n=days.length;
  const xs=(i)=> 8 + (i/(n-1||1))*(W-16);
  const ys=(s)=> H-62 - (clamp(s,0,100)/100)*(H-90);
  const line = scores.map((s,i)=>`${xs(i).toFixed(1)},${ys(s).toFixed(1)}`).join(" ");
  svg.querySelector("#hist-area").setAttribute("points", `8,${H} ${line} ${xs(n-1)},${H}`);
  svg.querySelector("#hist-line").setAttribute("points", line);
  svg.querySelector("#hist-glow").setAttribute("points", line);
  // mark peak
  let pi=0; scores.forEach((s,i)=>{ if(s>scores[pi]) pi=i; });
  const pk=svg.querySelector("#hist-peak");
  if(pk){ pk.setAttribute("cx",xs(pi)); pk.setAttribute("cy",ys(scores[pi])); }
}

function drawHeatmap(svg, days, scores){
  if(!svg) return;
  const COLORS=["#2DBF7B","#5DD49C","#FFE066","#FFB347","#FF5252","#B49BFF"];
  const last = days.slice(-90), lastS = scores.slice(-90);
  const cellW=78, cellH=14, gap=6, x0=44;
  let html="";
  // 7 rows x weeks; fill from oldest
  for(let i=0;i<last.length;i++){
    const col=Math.floor(i/7), rowi=i%7;
    const x=x0+col*(cellW+8), y=6+rowi*(cellH+4);
    const bi=bandOf(lastS[i]);
    const glow = bi>=5 ? `filter:url(#heatGlow)` : "";
    html += `<rect x="${x}" y="${y}" width="${cellW}" height="${cellH}" rx="2" fill="${COLORS[bi]}" opacity="${0.45+bi*0.1}" style="${glow}"></rect>`;
  }
  const g = svg.querySelector("#heat-cells");
  if (g) g.innerHTML = html;
}

function buildNotable(el, byDay){
  if(!el) return;
  const top = Object.entries(byDay).sort((a,b)=>b[1]-a[1]).slice(0,4);
  const COLORS=["#00FF94","#5DD49C","#FFE066","#FFB347","#FF5252","#B49BFF"];
  el.innerHTML = top.map(([d,s])=>{
    const bi=bandOf(s), c=COLORS[bi], name=BANDS[bi].name;
    return `<div style="background:var(--surface);border:1px solid ${c}45;border-radius:2px;padding:17px 19px;box-shadow:0 0 24px ${c}14">
      <div class="row" style="justify-content:space-between;margin-bottom:6px">
        <div class="row" style="gap:12px">
          <span class="mn" style="font-size:24px;color:${c};font-weight:500;text-shadow:0 0 12px ${c}b3">${s}</span>
          <span class="tag" style="background:${c}2e;color:${c}">${name}</span>
        </div>
        <span class="mn" style="font-size:10px;color:var(--text-faint);letter-spacing:.16em">${d}</span>
      </div>
      <div style="font-size:12.5px;color:var(--text-dim);line-height:1.55">Peak reading of ${s} recorded. ${
        bi>=4?"Major anomalous signal across multiple sources.":bi>=3?"Elevated cross-source activity.":"Notable bump above baseline."}</div>
    </div>`;
  }).join("");
}

/* ============================================================ SIGHTINGS (Leaflet) */
let MAP=null, MARKERS=null, SEARCH=null, allSightings=[], activeShape="all";

function initSightings(payload) {
  allSightings = (payload && payload.sightings) || [];
  if ($("#sight-count")) $("#sight-count").textContent = (payload && payload.count || 0).toLocaleString();

  MAP = L.map("map", { worldCopyJump:true, zoomControl:true, minZoom:2, maxZoom:18, attributionControl:true })
        .setView([25, 10], 2.4);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains:"abcd", maxZoom:20,
    attribution:'&copy; OpenStreetMap &copy; CARTO'
  }).addTo(MAP);

  // Cluster group keeps the map fast even with tens of thousands of points.
  // Falls back to a plain layer group if the plugin didn't load.
  if (typeof L.markerClusterGroup === "function") {
    MARKERS = L.markerClusterGroup({
      chunkedLoading: true,
      chunkInterval: 120,
      maxClusterRadius: 55,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      iconCreateFunction: (cluster) => {
        const n = cluster.getChildCount();
        let color = "#7AFFD0", size = 34;
        if (n >= 250)      { color = "#FF5252"; size = 50; }
        else if (n >= 50)  { color = "#FFB347"; size = 42; }
        const label = n >= 1000 ? (n/1000).toFixed(1) + "k" : n;
        return L.divIcon({
          className: "ayy-cluster",
          iconSize: [size, size],
          html: `<div style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;
                   border-radius:50%;background:${color}1f;border:1.5px solid ${color};color:${color};
                   font-family:'JetBrains Mono',monospace;font-size:${n>=1000?11:12}px;font-weight:500;
                   box-shadow:0 0 14px ${color}99, inset 0 0 10px ${color}33;text-shadow:0 0 6px ${color}">${label}</div>`
        });
      }
    }).addTo(MAP);
  } else {
    MARKERS = L.layerGroup().addTo(MAP);
  }
  SEARCH = L.layerGroup().addTo(MAP);   // geocode pin/radius live here, never cleared by filters
  renderMarkers();

  // shape filter chips
  $$("#shape-chips .chip").forEach(chip=>{
    chip.addEventListener("click", ()=>{
      $$("#shape-chips .chip").forEach(c=>c.classList.remove("active"));
      chip.classList.add("active");
      activeShape = chip.dataset.shape;
      renderMarkers();
    });
  });

  // search (Nominatim, fired on submit only -> stays within 1 req/sec policy)
  const doSearch = async () => {
    const q = $("#geo-input").value.trim();
    if (!q) return;
    const btn = $("#geo-btn"); const old = btn.textContent; btn.textContent = "\u2026";
    try {
      const url = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(q);
      const r = await fetch(url, { headers:{ "Accept-Language":"en" } });
      const j = await r.json();
      if (j && j[0]) {
        const lat=+j[0].lat, lon=+j[0].lon;
        SEARCH.clearLayers();
        MAP.setView([lat,lon], 8);
        L.circleMarker([lat,lon], { radius:7, color:"#7AFFD0", weight:2, fillColor:"#7AFFD0", fillOpacity:0.25, className:"sighting-marker" }).addTo(SEARCH);
        L.circle([lat,lon], { radius:160000, color:"#7AFFD0", weight:1, dashArray:"4,4", fill:false, opacity:0.5 }).addTo(SEARCH);
      } else {
        btn.textContent = "NOT FOUND"; setTimeout(()=>btn.textContent=old, 1500); return;
      }
    } catch(e){ console.error(e); }
    btn.textContent = old;
  };
  if ($("#geo-btn")) $("#geo-btn").addEventListener("click", doSearch);
  if ($("#geo-input")) $("#geo-input").addEventListener("keydown", e=>{ if(e.key==="Enter") doSearch(); });
}

function ageColor(dateStr){
  const t = new Date(dateStr).getTime();
  if (isNaN(t)) return "#7AFFD0";
  const days = (Date.now()-t)/86400000;
  if (days < 1) return "#FF5252";
  if (days < 7) return "#FFB347";
  if (days < 30) return "#7AFFD0";
  return "#5AC8FF";
}

function renderMarkers(){
  if (!MARKERS) return;
  MARKERS.clearLayers();
  const list = allSightings.filter(s => activeShape==="all" || s.shape===activeShape);
  const layers = [];
  for (const s of list) {
    const c = ageColor(s.date);
    const m = L.circleMarker([s.lat, s.lon], {
      radius:5, color:c, weight:1.2, fillColor:c, fillOpacity:0.55, className:"sighting-marker"
    });
    m.bindPopup(
      `<div class="mn" style="font-size:9.5px;color:${c};letter-spacing:.14em;text-transform:uppercase;margin-bottom:4px">${escapeHTML(s.shape)} \u00b7 ${escapeHTML(s.date)}</div>`
      + `<div class="gr" style="font-size:14px;font-weight:600;margin-bottom:4px">${escapeHTML(s.city||"Unknown")}${s.country?", "+escapeHTML(s.country):""}</div>`
      + (s.summary?`<div style="font-size:12px;color:#cdd1d8;font-style:italic;line-height:1.5">${escapeHTML(s.summary)}</div>`:"")
      + `<div class="mn" style="font-size:9.5px;color:#7AFFD0;letter-spacing:.16em;margin-top:8px">${escapeHTML(s.source||"UFOSINT")}</div>`
    );
    layers.push(m);
  }
  if (MARKERS.addLayers) MARKERS.addLayers(layers);   // bulk add (fast, chunked)
  else layers.forEach(m => m.addTo(MARKERS));
  const updMarkers = document.querySelector("#sight-shown");
  if (updMarkers) updMarkers.textContent = list.length.toLocaleString();
}

/* ============================================================ BOOT */
document.addEventListener("DOMContentLoaded", async () => {
  const page = document.body.dataset.page;
  try {
    if (page === "index") {
      const data = await fetchJSON("data.json");
      bindNav(data); initIndex(data);
    } else if (page === "archives") {
      try { const data = await fetchJSON("data.json"); bindNav(data); } catch(e){}
      const hist = await fetchJSON("history.json");
      initArchives(hist);
    } else if (page === "sightings") {
      try { const data = await fetchJSON("data.json"); bindNav(data); } catch(e){}
      let payload = { count:0, sightings:[] };
      try { payload = await fetchJSON("sightings.json"); } catch(e){ console.warn("no sightings.json yet"); }
      initSightings(payload);
    }
  } catch (err) {
    console.error("AYYLIEN load error:", err);
    const note = document.querySelector("#load-note");
    if (note) note.textContent = "Awaiting first data fetch \u2014 the cron writes data.json within ~15 min of deploy.";
  }
});
