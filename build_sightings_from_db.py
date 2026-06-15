#!/usr/bin/env python3
"""Optional: build sightings.json from the FULL UFOSINT public SQLite (~614k records).

UFOSINT asks people to use the SQLite download rather than scrape the rate-limited API.
1. Download 'ufo_public.db' from https://ufosint.com  (Methodology / Download panel)
2. Run:  python3 build_sightings_from_db.py /path/to/ufo_public.db  [max_points]
3. Commit the regenerated sightings.json

The script introspects the 'sighting' table and auto-detects lat/lon/shape/city/date
columns, so it tolerates minor schema changes. Default sample: 25,000 geocoded points
spread across the globe (more than that bloats the static file the browser must load).
"""
import sys, json, sqlite3, random, datetime as dt

def pick(cols, *cands):
    low = {c.lower(): c for c in cols}
    for cand in cands:
        if cand in low: return low[cand]
    for cand in cands:                       # substring fallback
        for c in cols:
            if cand in c.lower(): return c
    return None

def main():
    if len(sys.argv) < 2:
        print("usage: python3 build_sightings_from_db.py /path/to/ufo_public.db [max_points]")
        sys.exit(1)
    db = sys.argv[1]
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 25000

    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    cols = [r[1] for r in con.execute("PRAGMA table_info(sighting)").fetchall()]
    if not cols:
        print("No 'sighting' table found. Check the DB file."); sys.exit(1)

    c_lat   = pick(cols, "lat", "latitude")
    c_lon   = pick(cols, "lon", "lng", "longitude")
    c_shape = pick(cols, "shape", "object_shape")
    c_city  = pick(cols, "city", "location", "place")
    c_state = pick(cols, "state", "region", "country")
    c_date  = pick(cols, "date", "datetime", "sighted", "occurred", "event_date")
    c_summ  = pick(cols, "summary", "description", "text", "narrative")
    if not (c_lat and c_lon):
        print(f"Could not find lat/lon columns. Available: {cols}"); sys.exit(1)
    print(f"Using columns: lat={c_lat} lon={c_lon} shape={c_shape} city={c_city} date={c_date}")

    q = f"SELECT * FROM sighting WHERE {c_lat} IS NOT NULL AND {c_lon} IS NOT NULL ORDER BY RANDOM() LIMIT ?"
    NORM = {"sphere":"orb","light":"orb","circle":"orb","orb":"orb","triangle":"triangle",
            "formation":"triangle","disk":"disk","oval":"disk","diamond":"disk","fireball":"fireball",
            "cigar":"other","other":"other","unknown":"other"}
    out = []
    for r in con.execute(q, (cap,)):
        try:
            lat, lon = float(r[c_lat]), float(r[c_lon])
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180): continue
        raw = (str(r[c_shape]).lower().strip() if c_shape and r[c_shape] else "other")
        out.append({
            "lat": round(lat,4), "lon": round(lon,4),
            "shape": NORM.get(raw, "other"),
            "date": (str(r[c_date])[:10] if c_date and r[c_date] else ""),
            "city": (str(r[c_city]) if c_city and r[c_city] else ""),
            "country": (str(r[c_state]) if c_state and r[c_state] else ""),
            "summary": (str(r[c_summ])[:280] if c_summ and r[c_summ] else ""),
            "source": "UFOSINT",
        })
    payload = {"generated_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()+"Z",
               "note": f"Sampled {len(out)} of full UFOSINT dataset.", "count": len(out), "sightings": out}
    open("sightings.json","w",encoding="utf-8").write(json.dumps(payload))
    print(f"wrote sightings.json: {len(out)} sightings")

if __name__ == "__main__":
    main()
