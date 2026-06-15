#!/usr/bin/env python3
"""Build sightings.json from the full UFOSINT public SQLite (~600k records).

Usage:
  Inspect the schema first (recommended):
      python build_sightings_from_db.py ufo_public.db --inspect
  Then extract:
      python build_sightings_from_db.py ufo_public.db 25000

The extractor inspects real column VALUES (not just names) so it won't grab a
numeric city_id when it wants a city name. It prints the columns it chose plus a
sample record — eyeball that before uploading. If a field still looks wrong,
re-run with --inspect and share the output.
"""
import sys, json, sqlite3, random, datetime as dt

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

def is_texty(v):
    """True if the value looks like text (has a letter), not a pure number/id."""
    if v is None: return False
    s = str(v).strip()
    if not s: return False
    return any(ch.isalpha() for ch in s)

def pick(cols, samples, names, want_text=False, want_num=False):
    low = {c.lower(): c for c in cols}
    # exact name matches first, then substring
    ordered = []
    for n in names:
        if n in low: ordered.append(low[n])
    for n in names:
        for c in cols:
            if n in c.lower() and c not in ordered:
                ordered.append(c)
    for c in ordered:
        v = samples.get(c)
        if want_text and not is_texty(v):   # skip id-like numeric columns
            continue
        if want_num:
            try: float(v)
            except (TypeError, ValueError): continue
        return c
    return ordered[0] if ordered and not (want_text or want_num) else None

def inspect(con, table):
    cols, samples = col_info(con, table)
    print(f"\nTABLE: {table}  ({len(cols)} columns)\n" + "-"*60)
    for c in cols:
        print(f"  {c:<24} = {str(samples.get(c))[:50]}")
    print("-"*60)

def main():
    if len(sys.argv) < 2:
        print("usage: python build_sightings_from_db.py ufo_public.db [max_points | --inspect]"); sys.exit(1)
    db = sys.argv[1]
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row

    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("TABLES:", tables)
    table = "sighting" if "sighting" in tables else tables[0]

    if len(sys.argv) > 2 and sys.argv[2] == "--inspect":
        for t in tables:
            inspect(con, t)
        return

    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 25000
    cols, samples = col_info(con, table)

    c_lat   = pick(cols, samples, ["lat","latitude"], want_num=True)
    c_lon   = pick(cols, samples, ["lon","lng","long","longitude"], want_num=True)
    c_shape = pick(cols, samples, ["shape","object_shape","form"], want_text=True)
    c_city  = pick(cols, samples, ["city_name","cityname","city","town","locality","place","location"], want_text=True)
    c_state = pick(cols, samples, ["state","province","region"], want_text=True)
    c_ctry  = pick(cols, samples, ["country_name","country","nation"], want_text=True)
    c_date  = pick(cols, samples, ["date_time","datetime","date","occurred","sighted","event_date","reported"])
    c_summ  = pick(cols, samples, ["summary","description","text","narrative","comments","report","details","account","story","body","desc"], want_text=True)

    print(f"\nColumn mapping chosen:")
    for k,v in [("lat",c_lat),("lon",c_lon),("shape",c_shape),("city",c_city),
                ("state",c_state),("country",c_ctry),("date",c_date),("summary",c_summ)]:
        print(f"  {k:<8}-> {v}")
    if not (c_lat and c_lon):
        print("\nERROR: no lat/lon columns. Run with --inspect and share the output."); sys.exit(1)

    NORM = {"sphere":"orb","light":"orb","circle":"orb","orb":"orb","star":"orb","triangle":"triangle",
            "formation":"triangle","chevron":"triangle","disk":"disk","oval":"disk","egg":"disk","diamond":"disk",
            "fireball":"fireball","flash":"fireball","cigar":"other","other":"other","unknown":"other"}

    sel = [c for c in {c_lat,c_lon,c_shape,c_city,c_state,c_ctry,c_date,c_summ} if c]
    q = f'SELECT {",".join(chr(34)+c+chr(34) for c in sel)} FROM "{table}" WHERE "{c_lat}" IS NOT NULL AND "{c_lon}" IS NOT NULL ORDER BY RANDOM() LIMIT ?'
    out = []
    for r in con.execute(q, (cap,)):
        try: lat, lon = float(r[c_lat]), float(r[c_lon])
        except (TypeError, ValueError): continue
        if not (-90<=lat<=90 and -180<=lon<=180): continue
        raw = (str(r[c_shape]).lower().strip() if c_shape and r[c_shape] else "other")
        city = str(r[c_city]) if c_city and r[c_city] else ""
        state = str(r[c_state]) if c_state and r[c_state] else ""
        ctry = str(r[c_ctry]) if c_ctry and r[c_ctry] else ""
        place = ", ".join([p for p in (city, state) if p and is_texty(p)]) or ctry
        out.append({
            "lat": round(lat,4), "lon": round(lon,4),
            "shape": NORM.get(raw,"other"),
            "date": (str(r[c_date])[:10] if c_date and r[c_date] else ""),
            "city": place,
            "country": ctry if is_texty(ctry) else "",
            "summary": (str(r[c_summ])[:280] if c_summ and r[c_summ] else ""),
            "source": "UFOSINT",
        })
    payload = {"generated_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()+"Z",
               "note": f"Sampled {len(out)} of full UFOSINT dataset.", "count": len(out), "sightings": out}
    open("sightings.json","w",encoding="utf-8").write(json.dumps(payload))
    print(f"\nwrote sightings.json: {len(out)} sightings")
    print("SAMPLE RECORD:", json.dumps(out[0], ensure_ascii=False) if out else "none")

if __name__ == "__main__":
    main()
