#!/usr/bin/env python3
"""
$AYYLIEN Global Extraterrestrial Threat Level — data fetcher.

Pulls from NOAA SWPC, NASA, USGS, GDELT, Reddit, Wikipedia.
Computes a weighted 0-100 score, maps to a threat band, writes data.json.
Stdlib only — no pip install required.

Run:  python3 backend.py
Env:  NASA_API_KEY   (optional; falls back to DEMO_KEY)
      DRY_RUN=1      (use mock data, skip network — for local testing)
"""
import os
import json
import random
import datetime as dt
import statistics
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# ---------- config ----------
NASA_KEY = os.environ.get("NASA_API_KEY", "DEMO_KEY")
DRY_RUN  = os.environ.get("DRY_RUN") == "1"
UA       = "ayylien-threatmeter/1.0 (https://github.com/ayylien)"
OUT      = Path("data.json")
HIST     = Path("history.json")
SIGHT    = Path("sightings.json")

# UFOSINT free REST API. Endpoint/params may need tuning on first run — see get_sightings().
UFOSINT_BASE = os.environ.get("UFOSINT_BASE") or "https://ufosint-explorer.azurewebsites.net/api"
SIGHT_LIMIT  = int(os.environ.get("SIGHT_LIMIT", "1500"))  # cap points shipped to the browser

# v4 bands. (min_score, name, color, emoji, [rotating flavor lines])
# Thresholds: 0-14 / 15-29 / 30-49 / 50-69 / 70-89 / 90-100
# Listed high->low so score_to_band can return the first match where score >= min.
BANDS = [
    (90, "CONTACT IMMINENT",   "#B49BFF", "\U0001F7E3",
        ["ayy lmao", "they're here", "do not look up"]),
    (70, "THEY'RE WATCHING",   "#FF5252", "\U0001F534",
        ["hide the cattle", "close the blinds", "this is not a drill"]),
    (50, "ROSWELL ENERGY",     "#FFB347", "\U0001F7E0",
        ["they might be cooking", "something in the air tonight", "trust nothing"]),
    (30, "THAT'S WEIRD",       "#FFE066", "\U0001F7E1",
        ["huh", "that's... unusual", "keep an eye on the sky"]),
    (15, "PROBABLY SWAMP GAS", "#5DD49C", "\U0001F7E2",
        ["weather balloon energy", "probably venus", "nothing to see here"]),
    (0,  "NOTHINGBURGER",      "#00FF94", "\U0001F7E2",
        ["all quiet", "the aliens are sleeping", "boringly terrestrial"]),
]
BAND_INDEX = {name: i for i, (_, name, *_rest) in enumerate(reversed(BANDS))}  # 0..5 low->high

# ---------- helpers ----------
def fetch_json(url, timeout=20):
    if DRY_RUN:
        return None
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  WARN fetch failed {url[:80]}…  {e}")
        return None

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def zscore(latest, series):
    if len(series) < 2:
        return 0.0
    mean = statistics.mean(series)
    sd   = statistics.pstdev(series) or 0.01
    return (latest - mean) / sd

# ---------- fetchers ----------
def get_kp():
    """NOAA SWPC planetary K-index (0–9). First row is headers."""
    data = fetch_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
    if not data or len(data) < 2:
        return None
    try:
        latest = data[-1]
        return {"value": float(latest[1]), "time": latest[0]}
    except Exception as e:
        print(f"  kp parse: {e}")
        return None

def get_xray():
    """GOES X-ray flux → flare class (A/B/C/M/X)."""
    data = fetch_json("https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json")
    if not data:
        return None
    longs = [d for d in data if d.get("energy") == "0.1-0.8nm" and d.get("flux") is not None]
    if not longs:
        return None
    latest = longs[-1]
    flux = float(latest["flux"])
    if   flux >= 1e-4: cls, idx = "X", 5
    elif flux >= 1e-5: cls, idx = "M", 4
    elif flux >= 1e-6: cls, idx = "C", 3
    elif flux >= 1e-7: cls, idx = "B", 2
    else:              cls, idx = "A", 1
    return {"class": cls, "idx": idx, "flux": flux, "time": latest.get("time_tag")}

def get_alerts():
    """SWPC alerts feed — count last-24h alerts."""
    data = fetch_json("https://services.swpc.noaa.gov/products/alerts.json")
    if not data:
        return None
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    recent = []
    for a in data:
        ts = a.get("issue_datetime", "")
        try:
            t = dt.datetime.strptime(ts.split(".")[0], "%Y-%m-%d %H:%M:%S")
            if (now - t).total_seconds() < 86400:
                msg = (a.get("message") or "").strip().replace("\n", " ")[:140]
                recent.append(msg)
        except Exception:
            pass
    return {"count": len(recent), "latest": recent[:5]}

def get_neo():
    """NASA Near-Earth Object — closest asteroid pass over the next few days, in Lunar Distances."""
    if NASA_KEY == "DEMO_KEY":
        print("  NOTE: NASA_API_KEY not set \u2014 using DEMO_KEY (rate-limited ~30/hr; asteroid data will often be empty)")
    start = dt.date.today()
    end = start + dt.timedelta(days=2)
    url = (
        f"https://api.nasa.gov/neo/rest/v1/feed?"
        f"start_date={start.isoformat()}&end_date={end.isoformat()}&api_key={NASA_KEY}"
    )
    data = fetch_json(url)
    if not data:
        print("  WARN: NASA NeoWs returned nothing (key missing/invalid or rate-limited)")
        return None
    neo_by_date = data.get("near_earth_objects", {})
    closest = None
    count = 0
    for _day, objs in neo_by_date.items():
        count += len(objs)
        for o in objs:
            for ca in o.get("close_approach_data", []):
                try:
                    ld = float(ca["miss_distance"]["lunar"])
                except (KeyError, ValueError, TypeError):
                    continue
                if closest is None or ld < closest["ld"]:
                    closest = {
                        "ld": ld,
                        "name": o.get("name", "?"),
                        "diameter_m": o.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 0),
                        "hazardous": o.get("is_potentially_hazardous_asteroid", False),
                        "velocity_kps": float(ca.get("relative_velocity", {}).get("kilometers_per_second", 0)),
                    }
    print(f"  NEO: {count} objects over 3 days, closest {closest['ld']:.2f} LD" if closest else "  NEO: response OK but no close approaches found")
    return {"closest": closest, "count": count}

def get_gdelt_volume():
    """GDELT volume timeline for UFO/UAP coverage — current vs 7-day baseline."""
    q = '(UFO OR UAP OR "unidentified aerial phenomena" OR "alien disclosure")'
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc?"
        f"query={urllib.parse.quote(q)}&mode=timelinevol&format=json&timespan=7d"
    )
    data = fetch_json(url)
    if not data or not data.get("timeline"):
        return None
    series = data["timeline"][0].get("data", [])
    if len(series) < 3:
        return None
    vals = [float(d["value"]) for d in series if d.get("value") is not None]
    if len(vals) < 3:
        return None
    latest    = vals[-1]
    history_v = vals[:-1]
    baseline  = statistics.mean(history_v)
    z         = zscore(latest, history_v)
    spike_pct = ((latest - baseline) / (baseline + 0.01)) * 100
    return {"latest": latest, "baseline": baseline, "z": z, "spike_pct": spike_pct}

def get_gdelt_articles():
    """GDELT article list — fuel for the ticker."""
    q = '(UFO OR UAP OR "Pentagon UAP" OR "alien disclosure" OR Roswell)'
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc?"
        f"query={urllib.parse.quote(q)}&mode=artlist&format=json"
        "&maxrecords=25&sort=datedesc&timespan=2d"
    )
    data = fetch_json(url)
    if not data:
        return []
    out = []
    for a in data.get("articles", []):
        if a.get("title"):
            out.append({
                "title":  a["title"][:200],
                "url":    a.get("url"),
                "source": a.get("domain"),
                "time":   a.get("seendate"),
            })
    return out[:20]

def get_reddit():
    """Reddit chatter velocity across UFO subs (no auth, custom UA required)."""
    subs = ["UFOs", "aliens", "UAP", "HighStrangeness", "AlienBodies"]
    last_hour = 0
    items = []
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).timestamp()
    for sub in subs:
        data = fetch_json(f"https://www.reddit.com/r/{sub}/new.json?limit=100")
        if not data:
            continue
        for c in data.get("data", {}).get("children", []):
            d = c.get("data", {})
            try:
                age_h = (now - float(d["created_utc"])) / 3600
            except (KeyError, ValueError):
                continue
            if age_h < 1:
                last_hour += 1
            if age_h < 24:
                items.append({
                    "title":  (d.get("title") or "")[:200],
                    "url":    "https://reddit.com" + d.get("permalink", ""),
                    "sub":    sub,
                    "score":  int(d.get("score", 0)),
                    "time":   int(d.get("created_utc", 0)),
                })
    items.sort(key=lambda x: -x["time"])
    return {"last_hour": last_hour, "items": items[:15]}

def get_bluesky():
    """Bluesky chatter velocity for UFO/UAP terms. Public AppView API — no auth,
    works from datacenter IPs (unlike Reddit, which blocks Actions runners)."""
    terms = ["UFO", "UAP", "alien sighting"]
    now = dt.datetime.now(dt.timezone.utc)
    last_hour = 0
    items = []
    seen = set()
    for q in terms:
        url = ("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
               f"?q={urllib.parse.quote(q)}&limit=100&sort=latest")
        data = fetch_json(url)
        if not data:
            continue
        for p in data.get("posts", []):
            uri = p.get("uri", "")
            if not uri or uri in seen:
                continue
            seen.add(uri)
            rec = p.get("record", {}) or {}
            created = rec.get("createdAt") or p.get("indexedAt")
            try:
                ts = dt.datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            age_h = (now - ts).total_seconds() / 3600
            if age_h < 0 or age_h > 48:
                continue
            if age_h < 1:
                last_hour += 1
            handle = (p.get("author") or {}).get("handle", "")
            rkey = uri.split("/")[-1]
            text = (rec.get("text") or "")[:200]
            if age_h < 24 and handle and rkey and text:
                items.append({
                    "title": text,
                    "url": f"https://bsky.app/profile/{handle}/post/{rkey}",
                    "handle": handle,
                    "time": ts.timestamp(),
                })
    items.sort(key=lambda x: -x["time"])
    print(f"  bluesky: {last_hour} posts in last hour, {len(items)} recent items")
    return {"last_hour": last_hour, "items": items[:15]}

def get_wiki():
    """Wikipedia pageview spike for UFO-related articles vs 30-day baseline."""
    articles = [
        "Unidentified_flying_object",
        "Unidentified_anomalous_phenomena",
        "Roswell_incident",
        "Area_51",
        "Extraterrestrial_life",
    ]
    end   = dt.date.today() - dt.timedelta(days=1)   # pageviews have ~1-day lag
    start = end - dt.timedelta(days=30)
    yesterday_total = 0
    baseline_total  = 0
    have_data = False
    for a in articles:
        url = (
            "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            f"en.wikipedia.org/all-access/user/{a}/daily/"
            f"{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}"
        )
        data = fetch_json(url)
        if not data or not data.get("items"):
            continue
        items = data["items"]
        if not items:
            continue
        have_data = True
        yesterday_total += items[-1]["views"]
        if len(items) > 1:
            baseline_total += statistics.mean(i["views"] for i in items[:-1])
    if not have_data or baseline_total == 0:
        return None
    return {
        "yesterday": yesterday_total,
        "baseline":  baseline_total,
        "spike_pct": ((yesterday_total - baseline_total) / baseline_total) * 100,
    }

def get_quakes():
    """USGS significant earthquakes last 24h — chaos input."""
    data = fetch_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson")
    if not data:
        return {"count": 0, "max_mag": 0, "places": []}
    feats = data.get("features", [])
    mags  = [f["properties"]["mag"] for f in feats if f["properties"].get("mag")]
    return {
        "count":   len(feats),
        "max_mag": max(mags) if mags else 0,
        "places":  [f["properties"]["place"] for f in feats][:5],
    }

# ---------- scoring ----------
def score_factors(f):
    """Map each factor to a sub-score. Tune weights here."""
    score = 0.0
    contrib = {}

    # GDELT news velocity — biggest weight (0–36)
    g = f.get("gdelt_volume")
    if g:
        s = clamp(g["spike_pct"] / 50, 0, 3) * 12
        score += s; contrib["news_velocity"] = round(s, 1)

    # Reddit chatter (0–20). Baseline ~8/hr combined across subs.
    r = f.get("reddit") or {}
    b = f.get("bluesky") or {}
    chatter = (r.get("last_hour") or 0) + (b.get("last_hour") or 0)
    if chatter:
        s = clamp((chatter - 8) / 40, 0, 1) * 12
        score += s; contrib["social_chatter"] = round(s, 1)

    # Geomagnetic Kp (0–15)
    k = f.get("kp")
    if k:
        s = clamp(k["value"] / 9, 0, 1) * 15
        score += s; contrib["geomagnetic"] = round(s, 1)

    # Solar flare class (0–10)
    x = f.get("xray")
    if x:
        s = (x["idx"] - 1) / 4 * 10
        score += s; contrib["solar_flares"] = round(s, 1)

    # Asteroid close approach (0–10). <1 LD = under moon orbit = spicy.
    n = f.get("neo")
    if n and n.get("closest"):
        ld = n["closest"]["ld"]
        s = clamp((10 - ld) / 10, 0, 1) * 10
        score += s; contrib["asteroid_approach"] = round(s, 1)

    # Wikipedia interest spike (0–8)
    w = f.get("wiki")
    if w:
        s = clamp(w["spike_pct"] / 50, 0, 1) * 8
        score += s; contrib["search_interest"] = round(s, 1)

    # SWPC alerts count (0–6)
    a = f.get("alerts")
    if a:
        s = clamp(a["count"] / 5, 0, 1) * 6
        score += s; contrib["space_weather_alerts"] = round(s, 1)

    # Seismic chaos (0–4)
    q = f.get("quakes")
    if q and q["count"] > 0:
        s = clamp(q["max_mag"] / 8, 0, 1) * 4
        score += s; contrib["seismic"] = round(s, 1)

    # Random alien variance so the meter feels alive
    chaos = random.uniform(-3, 5)
    score += chaos; contrib["alien_variance"] = round(chaos, 1)

    return clamp(round(score, 1), 0, 100), contrib

def score_to_band(s):
    for min_score, name, color, emoji, flavors in BANDS:
        if s >= min_score:
            return {
                "name":   name,
                "flavor": random.choice(flavors),
                "index":  BAND_INDEX[name],   # 0 (NOTHINGBURGER) .. 5 (CONTACT IMMINENT)
                "color":  color,
                "emoji":  emoji,
                "min":    min_score,
            }
    b = BANDS[-1]
    return {"name": b[1], "flavor": random.choice(b[4]), "index": 0, "color": b[2], "emoji": b[3], "min": 0}

# ---------- ticker ----------
def build_ticker(f):
    t = []
    for a in f.get("gdelt_articles", [])[:10]:
        if a.get("title"):
            t.append({"type": "news", "text": a["title"], "source": a.get("source"), "url": a.get("url")})
    for p in f.get("reddit", {}).get("items", [])[:6]:
        t.append({"type": "reddit", "text": p["title"], "source": f"r/{p['sub']}", "url": p["url"]})
    for p in f.get("bluesky", {}).get("items", [])[:5]:
        t.append({"type": "bluesky", "text": p["title"], "source": "@" + p.get("handle", "bsky"), "url": p["url"]})
    for msg in (f.get("alerts") or {}).get("latest", [])[:3]:
        t.append({"type": "swpc", "text": msg, "source": "NOAA SWPC", "url": "https://www.swpc.noaa.gov/communities/space-weather-enthusiasts-dashboard"})
    q = f.get("quakes") or {}
    for place in q.get("places", [])[:2]:
        t.append({"type": "seismic", "text": f"Significant seismic event: {place}", "source": "USGS", "url": "https://earthquake.usgs.gov/earthquakes/map/"})
    n = f.get("neo") or {}
    if n.get("closest"):
        c = n["closest"]
        t.append({
            "type": "neo",
            "text": f"NEO {c['name']} passing at {c['ld']:.2f} LD (~{c['diameter_m']:.0f}m, {c['velocity_kps']:.1f} km/s)" + (" \u2014 PHA" if c["hazardous"] else ""),
            "source": "NASA NeoWs",
            "url": "https://cneos.jpl.nasa.gov/ca/",
        })
    return t

# ---------- history ----------
def update_history(score, band):
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    hist = []
    if HIST.exists():
        try:
            hist = json.loads(HIST.read_text())
        except Exception:
            hist = []
    hist.append({"ts": now, "score": score, "band": band["name"], "i": band["index"]})
    # Keep ~90 days at 15-min cadence (for the Archives page); ~8640 points.
    hist = hist[-8640:]
    HIST.write_text(json.dumps(hist))
    return hist

def compute_deltas(hist, score):
    # hist is 15-min cadence: 1h ago ~= 4 points back, 24h ago ~= 96 points back.
    def back(n):
        return hist[-1 - n]["score"] if len(hist) > n else None
    h1  = back(4)
    h24 = back(96)
    peak90 = max((p["score"] for p in hist), default=score)
    return {
        "d1h":  round(score - h1, 1)  if h1  is not None else 0.0,
        "d24h": round(score - h24, 1) if h24 is not None else 0.0,
        "peak90": peak90,
    }

# ---------- mock for dry-run ----------
def mock_factors():
    return {
        "kp":             {"value": 4.3, "time": "2026-05-27 00:00:00"},
        "xray":           {"class": "C", "idx": 3, "flux": 2.3e-6, "time": "2026-05-27T00:00:00Z"},
        "alerts":         {"count": 2, "latest": ["G2 storm watch issued", "M-class flare observed"]},
        "neo":            {"closest": {"ld": 4.1, "name": "(2026 XX)", "diameter_m": 87, "hazardous": False, "velocity_kps": 12.4}, "count": 5},
        "gdelt_volume":   {"latest": 0.18, "baseline": 0.12, "z": 1.6, "spike_pct": 50.0},
        "gdelt_articles": [{"title": "Pentagon releases new UAP report to Congress", "url": "https://www.reuters.com/", "source": "reuters.com", "time": "20260527T000000Z"}],
        "reddit":         {"last_hour": 17, "items": [{"title": "Bright orb over Phoenix tonight", "url": "https://reddit.com/r/UFOs/x", "sub": "UFOs", "score": 412, "time": 1700000000}]},
        "bluesky":        {"last_hour": 23, "items": [{"title": "anyone else just see that thing over the bay?? #UAP", "url": "https://bsky.app/profile/skywatcher.bsky.social/post/abc", "handle": "skywatcher.bsky.social", "time": 1700000000}]},
        "wiki":           {"yesterday": 12000, "baseline": 8200, "spike_pct": 46.3},
        "quakes":         {"count": 1, "max_mag": 6.4, "places": ["off the coast of Chile"]},
    }

# ---------- sightings (for the map) ----------
SHAPE_MAP = {
    "triangle": "triangle", "disk": "disk", "circle": "orb", "sphere": "orb",
    "orb": "orb", "light": "orb", "fireball": "fireball", "cigar": "other",
    "oval": "disk", "formation": "triangle", "diamond": "disk",
}
def norm_shape(s):
    if not s:
        return "other"
    return SHAPE_MAP.get(str(s).strip().lower(), "other")

def _normalize_sighting(rec):
    """Map a raw UFOSINT record to our compact map schema. Defensive about field names."""
    def pick(*keys):
        for k in keys:
            if k in rec and rec[k] not in (None, ""):
                return rec[k]
        return None
    lat = pick("lat", "latitude", "Latitude")
    lon = pick("lon", "lng", "longitude", "Longitude")
    try:
        lat = float(lat); lon = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return {
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "shape": norm_shape(pick("shape", "Shape", "object_shape")),
        "date": pick("date", "datetime", "sighted_at", "Date") or "",
        "city": pick("city", "City", "location", "place") or "",
        "country": pick("country", "Country", "state", "region") or "",
        "summary": (pick("summary", "description", "text", "Summary") or "")[:280],
        "source": pick("source", "Source", "dataset") or "UFOSINT",
    }

def get_sightings():
    """Pull recent sightings from UFOSINT. On any failure, return [] so the rest of the run survives."""
    if DRY_RUN:
        return mock_sightings()
    # NOTE: exact path/params are best-effort; adjust to UFOSINT's live API shape if this 404s.
    for path in (f"/sightings?limit={SIGHT_LIMIT}&sort=-date",
                 f"/sightings/recent?limit={SIGHT_LIMIT}",
                 f"/sightings?limit={SIGHT_LIMIT}"):
        data = fetch_json(UFOSINT_BASE + path)
        if data is None:
            continue
        rows = data if isinstance(data, list) else data.get("data") or data.get("results") or data.get("sightings") or []
        out = []
        for rec in rows:
            n = _normalize_sighting(rec)
            if n:
                out.append(n)
        if out:
            print(f"  sightings: {len(out)} via {path}")
            return out[:SIGHT_LIMIT]
    print("  WARN: no sightings returned from UFOSINT — map will be empty until API shape is confirmed")
    return []

def mock_sightings():
    pts = [
        (33.45, -112.07, "triangle", "Phoenix, AZ US", "United States", 312),
        (51.18, -1.83,  "orb",      "Stonehenge, UK",  "United Kingdom", 12),
        (-23.55, -46.63,"fireball", "Sao Paulo, BR",   "Brazil", 47),
        (35.68, 139.69, "disk",     "Tokyo, JP",       "Japan", 8),
        (40.71, -74.01, "orb",      "New York, US",    "United States", 5),
        (48.85, 2.35,   "disk",     "Paris, FR",       "France", 6),
        (-33.87,151.21, "triangle", "Sydney, AU",      "Australia", 9),
        (55.75, 37.62,  "orb",      "Moscow, RU",      "Russia", 4),
        (19.43, -99.13, "fireball", "Mexico City, MX", "Mexico", 22),
        (1.35,  103.82, "disk",     "Singapore, SG",   "Singapore", 3),
    ]
    return [{"lat": la, "lon": lo, "shape": sh, "date": "2026-05-27", "city": c,
             "country": ctry, "summary": f"{w} witnesses reported anomalous activity.",
             "source": "UFOSINT/NUFORC"} for (la, lo, sh, c, ctry, w) in pts]

# ---------- daily report (for the briefing card) ----------
ASSESSMENTS = {
    5: "Anomalous signal is off the charts across every monitored source. If you were waiting for a sign, this is it. Recommend you look up.",
    4: "Multiple independent sources are spiking in unison. Something is driving sustained, coordinated anomalous activity. Heightened surveillance advised.",
    3: "Evidence remains inconclusive but public interest is accelerating. The disclosure cycle continues to drive sustained anomalous signal. Recommend continued surveillance.",
    2: "A handful of signals are running above baseline. Nothing definitive, but the needle is twitching. Worth keeping an eye on the sky tonight.",
    1: "Background activity only. The occasional weather balloon, the odd swamp gas event. Nothing the cattle need worry about.",
    0: "All quiet on the extraterrestrial front. Sensors nominal, skies boring, aliens presumably asleep.",
}

def build_daily_report(score, band, deltas, factors, history, sightings_total):
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    # surveillance day = number of distinct calendar days we have data for (grows over time)
    days = {p["ts"][:10] for p in history if p.get("ts")}
    day_n = max(1, len(days))

    drivers = []
    art = (factors.get("gdelt_articles") or [])
    if art and art[0].get("title"):
        drivers.append(art[0]["title"])
    gv = factors.get("gdelt_volume") or {}
    if gv.get("spike_pct", 0) > 10:
        drivers.append(f"News velocity +{gv['spike_pct']:.0f}% vs 7-day baseline (GDELT)")
    rd = factors.get("reddit") or {}
    bs = factors.get("bluesky") or {}
    chatter = (rd.get("last_hour") or 0) + (bs.get("last_hour") or 0)
    if chatter:
        drivers.append(f"Social chatter: {chatter} UFO/UAP posts/hr (Reddit + Bluesky)")
    al = factors.get("alerts") or {}
    if al.get("count"):
        drivers.append(f"NOAA space-weather alerts active: {al['count']}")
    wk = factors.get("wiki") or {}
    if wk.get("spike_pct", 0) > 5:
        drivers.append(f"Wikipedia UFO pageviews +{wk['spike_pct']:.0f}% above baseline")
    neo = (factors.get("neo") or {}).get("closest")
    if neo:
        drivers.append(f"NEO {neo['name']} passing Earth at {neo['ld']:.1f} lunar distances")
    if not drivers:
        drivers = ["Background monitoring \u2014 no significant drivers in the last cycle."]

    return {
        "number": day_n,
        "day": day_n,
        "date": now.strftime("%d.%m.%Y"),
        "declassified": now.strftime("%d.%m.%y"),
        "generated_utc": now.strftime("%H:%M"),
        "top_drivers": drivers[:4],
        "assessment": ASSESSMENTS.get(band["index"], ASSESSMENTS[3]),
        "sightings_total": sightings_total,
    }

def load_sightings_count():
    """Sightings are a static committed dataset (not refetched each cron). Just read the count."""
    if SIGHT.exists():
        try:
            return json.loads(SIGHT.read_text()).get("count", 0)
        except Exception:
            return 0
    return 0

# ---------- main ----------
def main():
    print(f"[{dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()}Z] AYYLIEN threat meter — fetching…")
    if DRY_RUN:
        print("  DRY_RUN=1 — using mock data")
        factors = mock_factors()
    else:
        factors = {
            "kp":             get_kp(),
            "xray":           get_xray(),
            "alerts":         get_alerts(),
            "neo":            get_neo(),
            "gdelt_volume":   get_gdelt_volume(),
            "gdelt_articles": get_gdelt_articles(),
            "reddit":         get_reddit(),
            "bluesky":        get_bluesky(),
            "wiki":           get_wiki(),
            "quakes":         get_quakes(),
        }

    score, contrib = score_factors(factors)
    band    = score_to_band(score)
    ticker  = build_ticker(factors)
    history = update_history(score, band)
    deltas  = compute_deltas(history, score)
    sightings_total = load_sightings_count()
    report  = build_daily_report(score, band, deltas, factors, history, sightings_total)

    output = {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "score":        score,
        "band":         band,            # {name, flavor, index, color, emoji, min}
        "deltas":       deltas,          # {d1h, d24h, peak90}
        "contributing_factors": contrib,
        "sightings_total": sightings_total,
        "daily_report": report,
        "raw": {
            "kp":                       (factors["kp"] or {}).get("value"),
            "xray_class":               (factors["xray"] or {}).get("class"),
            "closest_asteroid_ld":      ((factors["neo"] or {}).get("closest") or {}).get("ld"),
            "asteroid_name":            ((factors["neo"] or {}).get("closest") or {}).get("name"),
            "gdelt_spike_pct":          (factors["gdelt_volume"] or {}).get("spike_pct"),
            "reddit_last_hour":         (factors["reddit"] or {}).get("last_hour"),
            "wiki_spike_pct":           (factors["wiki"] or {}).get("spike_pct"),
            "earthquakes_24h":          (factors["quakes"] or {}).get("count", 0),
            "max_quake_mag_24h":        (factors["quakes"] or {}).get("max_mag", 0),
            "swpc_alerts_24h":          (factors["alerts"] or {}).get("count", 0),
        },
        "ticker": ticker,
        "history": history[-672:],   # last ~7 days for the trend chart on page 1
        "sources": [
            "NASA NeoWs", "NOAA SWPC", "USGS", "GDELT 2.0", "UFOSINT",
            "Wikipedia", "Reddit", "Bluesky",
        ],
    }

    OUT.write_text(json.dumps(output, indent=2))
    print(f"  score={score}  band={band['name']}  ({band['flavor']})")
    print(f"  deltas: 1h={deltas['d1h']:+}  24h={deltas['d24h']:+}  peak90={deltas['peak90']}")
    print(f"  report #{report['number']}  drivers={len(report['top_drivers'])}  sightings_db={sightings_total}")
    print(f"  wrote {OUT} ({OUT.stat().st_size}b)")
    print(f"  history points: {len(history)}")

if __name__ == "__main__":
    main()
