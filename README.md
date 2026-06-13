# Global Alien Activity Index

A free, zero-infra web app: a real-time "alien activity" index (0-100) plus a global UFO/UAP
sightings map. Static frontend on GitHub Pages, data refreshed every 15 min by a GitHub Actions
cron running backend.py. Total cost: $0.

## Files
```
index.html        Alien Activity Index (gauge, factors, daily report, trend, ticker)
sightings.html    Global Leaflet map (CARTO Dark Matter tiles) + address search
archives.html     90-day history: stats, chart, notable activity, calendar heatmap
styles.css        Shared design system
app.js            Shared fetch + bind layer (reads the JSON below)
backend.py        Data fetcher - writes the three JSON files
.github/workflows/fetch.yml   Cron (every 15 min) + manual trigger; commits JSON back
data.json         (generated) score, band, deltas, factors, ticker, 7-day history
history.json      (generated) ~90 days of readings, 15-min cadence
sightings.json    (generated) recent sightings for the map
```
The frontend is plain HTML/CSS/JS - no build step, no framework. Just commit the files.

## Deploy (one-time, ~15 min)
1. Create a GitHub repo and add every file above (keep the folder structure).
2. NASA key: grab a free key at https://api.nasa.gov -> repo Settings > Secrets and variables >
   Actions > New repository secret -> name NASA_API_KEY, paste the key. (Without it the fetcher
   falls back to NASA's shared DEMO_KEY, which is heavily rate-limited.)
3. Let Actions write back: Settings > Actions > General > Workflow permissions >
   Read and write permissions > Save. (The cron commits the JSON files to the repo.)
4. Turn on Pages: Settings > Pages > Source: Deploy from a branch > main / (root) > Save.
   Your site goes live at https://<you>.github.io/<repo>/.
5. Seed the data now (don't wait 15 min): Actions tab > fetch-threat-level > Run workflow.
   First run writes data.json / history.json / sightings.json; refresh the site and it's live.

## How it updates
The cron runs backend.py every 15 minutes. It pulls NOAA SWPC, NASA NeoWs, USGS, GDELT, Reddit,
Wikipedia (+ stochastic "alien variance"), computes the weighted score, maps it to a band
(NOTHINGBURGER -> CONTACT IMMINENT), appends to history.json, pulls recent sightings into
sightings.json, and commits. GitHub Pages serves the new JSON; the pages re-read it on load.

Local test without network: DRY_RUN=1 python3 backend.py (uses mock data).

## Notes / known trade-offs
- Map tiles (CARTO Dark Matter): free, no API key, but the free tier caps at ~75k mapviews/month
  and is non-commercial. Fine for launch. If you outgrow it or want full control, self-host a single
  Protomaps .pmtiles file - a one-line change to the tile URL in app.js (initSightings).
- Sightings (UFOSINT): backend.py calls the UFOSINT REST API best-effort and is defensive - if the
  endpoint shape differs, it logs a warning and writes an empty list so the rest of the run (pages
  1 & 3) still succeeds. Confirm UFOSINT's live API path and, if needed, set a repo variable
  UFOSINT_BASE (Settings > Secrets and variables > Actions > Variables) to override.
- Address search (Nominatim): free OSM geocoder, no key. Fires only on submit (<=1 req/sec) to stay
  within their usage policy.
