#!/usr/bin/env python3
"""Build sightings.json from the full UFOSINT public SQLite (~600k records).

Usage:
  python build_sightings_from_db.py ufo_public.db --inspect      # dump schema
  python build_sightings_from_db.py ufo_public.db 25000          # extract

UFOSINT normalizes location into a separate `location` table (joined via
sighting.location_id). This script joins it for city/state/country, uses the
cleaned `standardized_shape`, and pulls `description` for the popup summary.
Prints the chosen mapping + a sample record so you can verify before uploading.
"""
import sys, json, sqlite3, datetime as dt

def col_info(con, table):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    samples = {}
    for c in cols:
        try:
            row = con.execute(f'SELECT "{c}" FROM "{table}" WHERE "{c}" IS NOT NULL AND "{c}"!=\'\' LIMIT 1').fetchone()
            samples[c] = row[0] if row else None
        except Exception:
            samples[c] = None
    return cols, samples

def inspect(con, tables):
    for t in tables:
        cols, samples = col_info(con, t)
        print(f"\nTABLE: {t}  ({len(cols)} columns)\n" + "-"*60)
        for c in cols:
            print(f"  {c:<24} = {str(samples.get(c))[:50]}")
        print("-"*60)

def clean_date(*vals):
    for v in vals:
        if not v: continue
        s = str(v)[:10]
        if len(s) >= 4 and s[:4].isdigit():
            y = int(s[:4])
            if 1900 <= y <= 2027:
                return s
    return ""

def txt(v, maxlen=60):
    if v is None: return ""
    s = str(v).strip().strip('"').strip()
    return s[:maxlen]

def main():
    if len(sys.argv) < 2:
        print("usage: python build_sightings_from_db.py ufo_public.db [max_points | --inspect]"); sys.exit(1)
    db = sys.argv[1]
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]

    if len(sys.argv) > 2 and sys.argv[2] == "--inspect":
        print("TABLES:", tables); inspect(con, tables); return

    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 25000
    scols, _ = col_info(con, "sighting")
    has_location = "location" in tables and "location_id" in scols
    shape_col = "standardized_shape" if "standardized_shape" in scols else "shape"

    # build query (join location if available)
    if has_location:
        q = (f'SELECT s.lat, s.lng, s."{shape_col}" AS shape, s.description AS descr, '
             f's.date_event, s.sighting_datetime, '
             f'l.city AS l_city, l.state AS l_state, l.country AS l_country '
             f'FROM sighting s LEFT JOIN location l ON s.location_id = l.id '
             f'WHERE s.lat IS NOT NULL AND s.lng IS NOT NULL ORDER BY RANDOM() LIMIT ?')
        print("Joining `location` table for city/state/country.")
    else:
        q = (f'SELECT lat, lng, "{shape_col}" AS shape, description AS descr, '
             f'date_event, sighting_datetime, "" AS l_city, "" AS l_state, "" AS l_country '
             f'FROM sighting WHERE lat IS NOT NULL AND lng IS NOT NULL ORDER BY RANDOM() LIMIT ?')
        print("WARNING: no location table/location_id found — city will be blank.")
    print(f"shape column: {shape_col}\n")

    NORM = {"sphere":"orb","light":"orb","circle":"orb","orb":"orb","star":"orb","triangle":"triangle",
            "formation":"triangle","chevron":"triangle","boomerang":"triangle","v-shaped":"triangle",
            "disk":"disk","oval":"disk","egg":"disk","diamond":"disk","saucer":"disk","cylinder":"other",
            "fireball":"fireball","flash":"fireball","flare":"fireball","cigar":"other","other":"other","unknown":"other"}

    out = []
    for r in con.execute(q, (cap,)):
        try: lat, lon = float(r["lat"]), float(r["lng"])
        except (TypeError, ValueError): continue
        if not (-90<=lat<=90 and -180<=lon<=180): continue
        raw = (str(r["shape"]).lower().strip() if r["shape"] else "other")
        city, state, ctry = txt(r["l_city"]), txt(r["l_state"], 24), txt(r["l_country"], 32)
        place = ", ".join([p for p in (city, state) if p]) or ctry
        out.append({
            "lat": round(lat,4), "lon": round(lon,4),
            "shape": NORM.get(raw, "other"),
            "date": clean_date(r["date_event"], r["sighting_datetime"]),
            "city": place,
            "country": ctry,
            "summary": txt(r["descr"], 280),
            "source": "UFOSINT",
        })
    payload = {"generated_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()+"Z",
               "note": f"Sampled {len(out)} of full UFOSINT dataset.", "count": len(out), "sightings": out}
    open("sightings.json","w",encoding="utf-8").write(json.dumps(payload))
    with_desc = sum(1 for s in out if s["summary"])
    with_city = sum(1 for s in out if s["city"])
    print(f"wrote sightings.json: {len(out)} sightings  ({with_city} with a place, {with_desc} with a description)")
    print("SAMPLE RECORDS:")
    for s in out[:3]:
        print("  ", json.dumps(s, ensure_ascii=False))

if __name__ == "__main__":
    main()
