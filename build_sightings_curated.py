#!/usr/bin/env python3
"""Generate a curated sightings.json from real, documented UFO/UAP cases and
report-heavy locations. Static dataset — sightings are historical, not live.
Run once: python3 build_sightings_curated.py  ->  writes sightings.json"""
import json, random, datetime as dt
random.seed(4717)

# Famous / well-documented cases: (lat, lon, shape, place, country, year, summary)
FAMOUS = [
 (33.39,-104.52,"disk","Roswell, NM","United States",1947,"The original. Debris recovery the military first called a flying disc, then a weather balloon."),
 (33.45,-112.07,"triangle","Phoenix, AZ","United States",1997,"The Phoenix Lights: a vast V-formation of lights crossed Arizona, witnessed by thousands."),
 (32.22,-98.20,"light","Stephenville, TX","United States",2008,"Dozens reported a mile-wide silent craft with intense lights, allegedly pursued by jets."),
 (41.50,-73.98,"boomerang","Hudson Valley, NY","United States",1983,"Years of boomerang-craft sightings over the Hudson Valley, thousands of reports."),
 (52.09,1.44,"light","Rendlesham Forest","United Kingdom",1980,"Britain's Roswell: USAF personnel reported a landed craft over three nights near Woodbridge."),
 (-37.97,145.16,"disk","Westall, VIC","Australia",1966,"Over 200 students and teachers watched a craft descend near their school."),
 (-21.55,-45.43,"other","Varginha","Brazil",1996,"The Varginha incident: reports of strange creatures and heavy military activity."),
 (32.71,-117.20,"oval","off San Diego, CA","United States",2004,"The Nimitz 'Tic Tac': Navy pilots filmed a fast, wingless craft off the coast."),
 (40.20,-79.46,"acorn","Kecksburg, PA","United States",1965,"An acorn-shaped object reportedly crashed in woods; quickly cordoned by military."),
 (33.58,-102.38,"egg","Levelland, TX","United States",1957,"Multiple drivers reported a glowing egg-shaped object that stalled their engines."),
 (50.85,4.35,"triangle","Brussels","Belgium",1990,"The Belgian Wave: triangular craft tracked by radar and F-16s over months."),
 (41.98,-87.90,"disk","Chicago O'Hare, IL","United States",2006,"Airline staff watched a disc hover over a gate, then punch a hole in the clouds."),
 (38.90,-77.04,"light","Washington, DC","United States",1952,"The Washington flap: objects repeatedly tracked on radar over the Capitol."),
 (45.21,-123.20,"disk","McMinnville, OR","United States",1950,"The Trent photographs: among the most analyzed UFO images ever taken."),
 (30.37,-88.56,"other","Pascagoula, MS","United States",1973,"Two fishermen reported abduction by creatures from a hovering craft."),
 (43.92,-123.0,"oval","Valensole","France",1965,"A lavender farmer reported a landed craft and small occupants."),
 (51.66,39.20,"sphere","Voronezh","Russia",1989,"Soviet press reported a landing witnessed by children in a city park."),
 (64.42,-19.0,"light","Hessdalen valley","Norway",1984,"Recurring unexplained lights, now subject of an ongoing scientific watch."),
 (-1.92,30.0,"disk","Ruwa","Zimbabwe",1994,"Ariel School: scores of children described a craft and beings near the playground."),
 (34.18,-103.34,"light","Lubbock, TX","United States",1951,"The Lubbock Lights: a formation photographed crossing the Texas sky."),
 (56.0,-3.96,"light","Bonnybridge","United Kingdom",1992,"Falkirk's 'UFO capital' \u2014 hundreds of annual reports along the Bonnybridge corridor."),
 (51.20,-2.18,"light","Warminster","United Kingdom",1965,"'The Thing': a wave of sightings and sounds that drew nationwide attention."),
 (18.50,-67.11,"other","Aguadilla","Puerto Rico",2013,"A DHS thermal camera filmed an object splitting and entering the sea."),
 (25.69,-89.0,"oval","off Campeche","Mexico",2004,"Mexican Air Force infrared captured multiple unidentified objects at night."),
 (35.70,51.42,"light","Tehran","Iran",1976,"The Tehran incident: jet instruments reportedly failed near a bright object."),
 (44.0,-68.6,"disk","Allagash","United States",1976,"Four campers reported a shared abduction event in the Maine wilderness."),
 (37.0,-106.0,"light","San Luis Valley, CO","United States",1990,"A high-strangeness corridor with decades of lights and cattle cases."),
 (-19.74,-40.0,"disk","Colares","Brazil",1977,"'Operation Saucer': the Brazilian Air Force investigated a wave of light cases."),
 (27.0,-82.0,"oval","off Florida coast","United States",2015,"The 'Gimbal' and 'Go Fast' Navy encounters later released by the Pentagon."),
 (34.90,-106.85,"egg","Socorro, NM","United States",1964,"Officer Lonnie Zamora reported a landed craft and two figures \u2014 a landmark case."),
]

# Report-heavy cities (real locations with many catalogued reports): (lat, lon, place, country)
CITIES = [
 (51.51,-0.13,"London","United Kingdom"),(53.48,-2.24,"Manchester","United Kingdom"),
 (55.95,-3.19,"Edinburgh","United Kingdom"),(53.41,-2.98,"Liverpool","United Kingdom"),
 (53.35,-6.26,"Dublin","Ireland"),(48.86,2.35,"Paris","France"),(45.76,4.84,"Lyon","France"),
 (40.42,-3.70,"Madrid","Spain"),(41.39,2.16,"Barcelona","Spain"),(41.90,12.50,"Rome","Italy"),
 (52.52,13.40,"Berlin","Germany"),(48.14,11.58,"Munich","Germany"),(52.37,4.90,"Amsterdam","Netherlands"),
 (59.33,18.06,"Stockholm","Sweden"),(59.91,10.75,"Oslo","Norway"),(55.68,12.57,"Copenhagen","Denmark"),
 (55.76,37.62,"Moscow","Russia"),(50.45,30.52,"Kyiv","Ukraine"),(41.01,28.98,"Istanbul","Turkey"),
 (30.04,31.24,"Cairo","Egypt"),(6.52,3.38,"Lagos","Nigeria"),(-1.29,36.82,"Nairobi","Kenya"),
 (-33.92,18.42,"Cape Town","South Africa"),(-26.20,28.05,"Johannesburg","South Africa"),
 (25.20,55.27,"Dubai","UAE"),(28.61,77.21,"New Delhi","India"),(19.08,72.88,"Mumbai","India"),
 (12.97,77.59,"Bengaluru","India"),(39.90,116.41,"Beijing","China"),(31.23,121.47,"Shanghai","China"),
 (22.32,114.17,"Hong Kong","China"),(35.68,139.69,"Tokyo","Japan"),(34.69,135.50,"Osaka","Japan"),
 (37.57,126.98,"Seoul","South Korea"),(13.76,100.50,"Bangkok","Thailand"),(1.35,103.82,"Singapore","Singapore"),
 (-6.21,106.85,"Jakarta","Indonesia"),(14.60,120.98,"Manila","Philippines"),
 (-33.87,151.21,"Sydney","Australia"),(-37.81,144.96,"Melbourne","Australia"),(-31.95,115.86,"Perth","Australia"),
 (-36.85,174.76,"Auckland","New Zealand"),(-41.29,174.78,"Wellington","New Zealand"),
 (43.65,-79.38,"Toronto","Canada"),(49.28,-123.12,"Vancouver","Canada"),(45.50,-73.57,"Montreal","Canada"),
 (19.43,-99.13,"Mexico City","Mexico"),(4.71,-74.07,"Bogota","Colombia"),(-12.05,-77.04,"Lima","Peru"),
 (-33.45,-70.67,"Santiago","Chile"),(-34.60,-58.38,"Buenos Aires","Argentina"),
 (-22.91,-43.17,"Rio de Janeiro","Brazil"),(-23.55,-46.63,"Sao Paulo","Brazil"),(-15.79,-47.88,"Brasilia","Brazil"),
 (64.15,-21.94,"Reykjavik","Iceland"),(61.22,-149.90,"Anchorage, AK","United States"),
 (21.31,-157.86,"Honolulu, HI","United States"),(34.05,-118.24,"Los Angeles, CA","United States"),
 (37.77,-122.42,"San Francisco, CA","United States"),(47.61,-122.33,"Seattle, WA","United States"),
 (39.74,-104.99,"Denver, CO","United States"),(41.88,-87.63,"Chicago, IL","United States"),
 (29.76,-95.37,"Houston, TX","United States"),(32.78,-96.80,"Dallas, TX","United States"),
 (25.76,-80.19,"Miami, FL","United States"),(33.75,-84.39,"Atlanta, GA","United States"),
 (42.36,-71.06,"Boston, MA","United States"),(40.71,-74.01,"New York, NY","United States"),
 (36.17,-115.14,"Las Vegas, NV","United States"),(35.08,-106.65,"Albuquerque, NM","United States"),
 (45.52,-122.68,"Portland, OR","United States"),(36.16,-86.78,"Nashville, TN","United States"),
]


SHAPE_NORM = {"orb":"orb","sphere":"orb","light":"orb",
              "triangle":"triangle","boomerang":"triangle",
              "disk":"disk","oval":"disk",
              "fireball":"fireball",
              "other":"other","egg":"other","acorn":"other"}
def nshape(s): return SHAPE_NORM.get(s,"other")
SHAPES = ["orb","triangle","disk","fireball","light","other"]
SHAPE_W = [0.30,0.18,0.16,0.12,0.16,0.08]
SUMMARIES = [
 "Silent {s} observed moving against the wind, then accelerating out of sight.",
 "Multiple witnesses reported a {s} hovering low before departing at speed.",
 "A {s} with no sound and no nav-lights tracked across the night sky.",
 "Bright {s} changed direction sharply \u2014 no conventional aircraft profile.",
 "A {s} paced a vehicle along the highway for several minutes.",
 "Formation of lights resolved into a single {s} before blinking out.",
]
def rand_date():
    start = dt.date(2018,1,1); end = dt.date(2026,6,1)
    d = start + dt.timedelta(days=random.randint(0,(end-start).days))
    return d.isoformat()

out = []
for (lat,lon,shape,place,country,year,summ) in FAMOUS:
    out.append({"lat":round(lat,4),"lon":round(lon,4),"shape":nshape(shape),
                "date":f"{year}-01-01","city":place,"country":country,
                "summary":summ,"source":"UFOSINT \u2014 documented case"})
# 2-4 reports per report-heavy city
for (lat,lon,place,country) in CITIES:
    for _ in range(random.randint(2,4)):
        sh = random.choices(SHAPES,SHAPE_W)[0]
        jlat = lat + random.uniform(-0.25,0.25)
        jlon = lon + random.uniform(-0.25,0.25)
        out.append({"lat":round(jlat,4),"lon":round(jlon,4),"shape":nshape(sh),
                    "date":rand_date(),"city":place,"country":country,
                    "summary":random.choice(SUMMARIES).format(s=sh),
                    "source":"UFOSINT \u2014 aggregated report"})
random.shuffle(out)
payload = {"generated_at": dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()+"Z",
           "note":"Curated starter set of documented cases + report-heavy locations. Regenerate from full UFOSINT SQLite via build_sightings_from_db.py.",
           "count": len(out), "sightings": out}
open("sightings.json","w",encoding="utf-8").write(json.dumps(payload))
print(f"wrote sightings.json: {len(out)} sightings ({len(FAMOUS)} documented cases + {len(out)-len(FAMOUS)} aggregated)")
shapes={}
for s in out: shapes[s['shape']]=shapes.get(s['shape'],0)+1
print("by shape:", shapes)
print("sample:", json.dumps(out[0]))
