# okc_food_map_final_takecontrol.py
import re
import time
import math
import requests
import pandas as pd
import folium

CSV_FILE = "Data Sheet of OKC - Sheet1.csv"
OUTPUT_HTML = "okc_food_map.html"
TIGER_SLEEP = 0.18  # polite pause between TIGERweb requests

# ---------------- helpers ----------------
def clean_number(x):
    if x is None:
        return None
    if isinstance(x, (int, float)) and not pd.isna(x):
        return float(x)
    s = str(x).strip()
    if s == "" or s.lower() in ("na", "n/a", "nan", "--"):
        return None
    # remove parentheses, currency, percent, commas
    s = s.replace("(", "").replace(")", "").replace("$", "").replace("%", "").replace(",", "")
    # allow minus and dot only
    s2 = re.sub(r"[^0-9.\-]+", "", s)
    try:
        return float(s2) if s2 != "" else None
    except Exception:
        return None

def parse_latlon_from_any(value):
    if value is None:
        return None, None
    s = str(value)
    m = re.search(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None

def get_centroid_from_tigerweb(geoid):
    services = [
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/16/query",
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts/MapServer/11/query",
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/MapServer/23/query"
    ]
    params = {"where": f"GEOID='{geoid}'", "outFields": "GEOID", "returnGeometry": "true", "f": "json"}
    for svc in services:
        try:
            r = requests.get(svc, params=params, timeout=15)
            if r.status_code != 200:
                continue
            j = r.json()
            features = j.get("features") or []
            if not features:
                continue
            geom = features[0].get("geometry")
            if not geom:
                continue
            if "rings" in geom:
                pts = []
                for ring in geom["rings"]:
                    for xy in ring:
                        # xy => [x=lon, y=lat]
                        pts.append((xy[1], xy[0]))
                if pts:
                    avg_lat = sum(p[0] for p in pts) / len(pts)
                    avg_lon = sum(p[1] for p in pts) / len(pts)
                    return avg_lat, avg_lon
            if "x" in geom and "y" in geom:
                return float(geom["y"]), float(geom["x"])
        except Exception:
            pass
        finally:
            time.sleep(TIGER_SLEEP)
    return None, None

# ---------------- load CSV ----------------
print(f"Loading '{CSV_FILE}' ...")
df = pd.read_csv(CSV_FILE, dtype=str)
cols = list(df.columns)
print("Columns found:", cols)
print()

# ---------------- detect columns (explicit preferred) ----------------
tract_col = "Tract_FIPS" if "Tract_FIPS" in cols else None
totalpop_col = next((c for c in cols if "total population" in c.lower()), None)

# prefer explicit lat/lon names
possible_lat_names = ["latitude", "lat", "centroid_lat", "intptlat", "y"]
possible_lon_names = ["longitude", "lon", "centroid_lon", "intptlon", "x", "lng"]

lat_col = None
lon_col = None
for c in cols:
    cl = c.strip().lower()
    if cl in possible_lat_names and lat_col is None:
        lat_col = c
    if cl in possible_lon_names and lon_col is None:
        lon_col = c

def find_col(cols, tokens):
    cols_l = {c.lower(): c for c in cols}
    for t in tokens:
        t = t.lower()
        for lc, orig in cols_l.items():
            if t in lc:
                return orig
    return None

if tract_col is None:
    tract_col = find_col(cols, ["tract_fips", "tractfips", "censustract", "geoid", "tract"])

if lat_col is None:
    lat_col = find_col(cols, ["latitude", "lat", "centroid_lat", "intptlat", "y"])
if lon_col is None:
    lon_col = find_col(cols, ["longitude", "lon", "centroid_lon", "intptlon", "x", "lng"])

poverty_col = find_col(cols, ["% below poverty", "poverty", "povertyrate", "poverty_rate"])
income_col = find_col(cols, ["median_income", "medianfamilyincome", "median_family_income", "medianincome"])
lap1_col = find_col(cols, ["one mile", "grocery_1mi", "within one mile", "population within one mile", "lapop1", "lapop1share"])
lap10_col = find_col(cols, ["10 miles", "grocery_10mi", "within 10 miles", "population within 10 miles", "lapop10", "lapop10share"])
snap_col = find_col(cols, ["snap", "lasnap", "snap_share", "snap%"])
obesity_col = find_col(cols, ["adult obesity", "obesity"])
diabetes_col = find_col(cols, ["adult diabetes", "diabetes"])
inactive_col = find_col(cols, ["physically inactive", "inactive", "phys_inactive"])
notes_col = find_col(cols, ["notes"])

print("Detected columns (best guesses):")
print(" Tract:", tract_col)
print(" Lat:", lat_col, " Lon:", lon_col)
print(" TotalPop:", totalpop_col)
print(" Poverty:", poverty_col, " Income:", income_col)
print(" 1mi:", lap1_col, " 10mi:", lap10_col, " SNAP:", snap_col)
print(" Health:", obesity_col, diabetes_col, inactive_col)
print()

# ---------------- clean and build records ----------------
records = []
raw_rows = 0
for _, row in df.iterrows():
    raw_rows += 1
    tract = row.get(tract_col) if tract_col else None
    if tract is None:
        # try any column that looks like a tract header
        for c in cols:
            if "tract" in c.lower() or "geoid" in c.lower():
                tract = row.get(c)
                break
    if tract is None:
        # skip rows without any tract id
        continue
    tract = str(tract).strip()
    # keep the original row for diagnosis if needed
    records.append({
        "Tract_FIPS_raw": tract,
        "row": row
    })

print(f"Total rows read: {raw_rows}, candidate tract rows found: {len(records)}")

# make a df of candidates and filter to valid 11-digit numeric tracts
cand = pd.DataFrame(records)
# normalize leading/trailing whitespace and remove non-digits
cand["Tract_FIPS_clean"] = cand["Tract_FIPS_raw"].str.replace(r"\D", "", regex=True)
# keep only 11-digit tract strings
valid_mask = cand["Tract_FIPS_clean"].str.match(r"^\d{11}$", na=False)
valid = cand[valid_mask].copy()
dropped = cand[~valid_mask].copy()

print(f"Valid tracts kept: {len(valid)}; dropped non-tract rows: {len(dropped)}")

# now parse numeric columns per valid row
rows = []
for _, r in valid.iterrows():
    row = r["row"]
    tract = r["Tract_FIPS_clean"]
    # lat/lon
    lat = clean_number(row.get(lat_col)) if lat_col and row.get(lat_col) is not None else None
    lon = clean_number(row.get(lon_col)) if lon_col and row.get(lon_col) is not None else None
    if (lat is None or lon is None):
        # try parsing combined columns
        for c in cols:
            plat, plon = parse_latlon_from_any(row.get(c))
            if plat is not None and plon is not None:
                lat = lat or plat
                lon = lon or plon
                break

    total_pop = clean_number(row.get(totalpop_col)) if totalpop_col else None

    poverty = clean_number(row.get(poverty_col)) if poverty_col else None
    income = clean_number(row.get(income_col)) if income_col else None

    lap1_raw = clean_number(row.get(lap1_col)) if lap1_col else None
    lap10_raw = clean_number(row.get(lap10_col)) if lap10_col else None

    # If the lap1/10 values look absurdly large (>100), treat them as counts and convert to percent using total_pop
    lap1_pct = None
    lap10_pct = None
    if lap1_raw is not None:
        if lap1_raw > 100 and total_pop and total_pop > 0:
            lap1_pct = max(0.0, min(100.0, (lap1_raw / total_pop) * 100.0))
        elif lap1_raw <= 100:
            lap1_pct = lap1_raw
        else:
            lap1_pct = None
    if lap10_raw is not None:
        if lap10_raw > 100 and total_pop and total_pop > 0:
            lap10_pct = max(0.0, min(100.0, (lap10_raw / total_pop) * 100.0))
        elif lap10_raw <= 100:
            lap10_pct = lap10_raw
        else:
            lap10_pct = None

    snap = clean_number(row.get(snap_col)) if snap_col else None
    obesity = clean_number(row.get(obesity_col)) if obesity_col else None
    diabetes = clean_number(row.get(diabetes_col)) if diabetes_col else None
    inactive = clean_number(row.get(inactive_col)) if inactive_col else None

    rows.append({
        "Tract_FIPS": tract,
        "lat": lat,
        "lon": lon,
        "total_pop": total_pop,
        "poverty": poverty,
        "income": income,
        "lap1_pct": lap1_pct,
        "lap10_pct": lap10_pct,
        "snap": snap,
        "obesity": obesity,
        "diabetes": diabetes,
        "inactive": inactive
    })

work = pd.DataFrame.from_records(rows)
if work.empty:
    raise SystemExit("No valid tract rows found after filtering. Check CSV.")

print(f"Working tracts: {len(work)} (after cleaning)")

# ---------------- composite calculation (CDC-like priority) ----------------
def comp_distance_val(row):
    if pd.notna(row["lap1_pct"]) and row["lap1_pct"] is not None:
        return max(0.0, min(1.0, (100.0 - row["lap1_pct"]) / 100.0))
    if pd.notna(row["lap10_pct"]) and row["lap10_pct"] is not None:
        return max(0.0, min(1.0, (100.0 - row["lap10_pct"]) / 100.0))
    return None

def comp_poverty_val(row):
    if pd.notna(row["poverty"]) and row["poverty"] is not None:
        return max(0.0, min(1.0, row["poverty"] / 100.0))
    return None

def comp_snap_val(row):
    if pd.notna(row["snap"]) and row["snap"] is not None:
        return max(0.0, min(1.0, row["snap"] / 100.0))
    return None

def comp_health_val(row):
    parts = []
    for k in ("obesity", "diabetes", "inactive"):
        if pd.notna(row[k]) and row[k] is not None:
            parts.append(row[k] / 100.0)
    if not parts:
        return None
    return sum(parts) / len(parts)

W_POV = 0.35
W_SNAP = 0.25
W_HEALTH = 0.20
W_DIST = 0.15
W_INC = 0.05

composite_scores = []
for _, r in work.iterrows():
    p = comp_poverty_val(r)
    s = comp_snap_val(r)
    h = comp_health_val(r)
    d = comp_distance_val(r)
    inc = None
    if pd.notna(r["income"]) and r["income"] is not None:
        inc = max(0.0, min(1.0, 1.0 - (r["income"] / 200000.0)))
    comps = []
    wts = []
    if p is not None:
        comps.append(p); wts.append(W_POV)
    if s is not None:
        comps.append(s); wts.append(W_SNAP)
    if h is not None:
        comps.append(h); wts.append(W_HEALTH)
    if d is not None:
        comps.append(d); wts.append(W_DIST)
    if inc is not None:
        comps.append(inc); wts.append(W_INC)
    if not comps:
        composite = None
    else:
        wsum = sum(wts)
        composite = sum(c * w for c, w in zip(comps, wts)) / wsum
    composite_scores.append(composite)

work["composite_score"] = composite_scores
work["rank"] = work["composite_score"].rank(method="min", ascending=False)
work_sorted = work.sort_values(by="composite_score", ascending=False, na_position="last").reset_index(drop=True)

# ---------------- print top-10 ----------------
print("\nTop 10 tracts by CDC-like composite (higher = worse):")
for i, r in work_sorted.head(10).iterrows():
    cs = r["composite_score"]
    print(f"{int(r['rank']) if not pd.isna(r['rank']) else 'N/A'}. Tract {r['Tract_FIPS']}: score={None if pd.isna(cs) else round(cs,3)}  poverty={r['poverty']} snap={r['snap']} lap1%={r['lap1_pct']}")

# ---------------- fetch missing centroids ----------------
missing = work_sorted[work_sorted["lat"].isna() | work_sorted["lon"].isna()]
if not missing.empty:
    print(f"\n{len(missing)} tracts missing centroids — attempting TIGERweb lookups...")
    for idx, row in missing.iterrows():
        geoid = row["Tract_FIPS"]
        lat, lon = get_centroid_from_tigerweb(geoid)
        if lat is not None and lon is not None:
            work_sorted.at[idx, "lat"] = lat
            work_sorted.at[idx, "lon"] = lon
            print(f"  got centroid for {geoid}: {lat}, {lon}")
        else:
            print(f"  could not fetch centroid for {geoid}")
    print("Centroid fetch attempts done.\n")

# ---------------- build folium map ----------------
m = folium.Map(location=[35.48, -97.50], zoom_start=11)

def risk_badge(score):
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return ("gray", "⚪️ Unknown", "Unknown")
    if score >= 0.66:
        return ("darkred", "🔥 HIGH", "Severe")
    if score >= 0.33:
        return ("orange", "⚠️ MEDIUM", "Moderate")
    return ("green", "✅ LOW", "Low")

for _, r in work_sorted.iterrows():
    lat = r["lat"]; lon = r["lon"]
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        continue
    tract = r["Tract_FIPS"]
    score = r["composite_score"]
    rank = int(r["rank"]) if not pd.isna(r["rank"]) else "N/A"
    color, badge_text, _level = risk_badge(score)

    poverty_disp = f"{r['poverty']:.1f}%" if (r['poverty'] is not None and not pd.isna(r['poverty'])) else "N/A"
    snap_disp = f"{r['snap']:.1f}%" if (r['snap'] is not None and not pd.isna(r['snap'])) else "N/A"
    lap1_disp = f"{r['lap1_pct']:.1f}%" if (r['lap1_pct'] is not None and not pd.isna(r['lap1_pct'])) else "N/A"
    lap10_disp = f"{r['lap10_pct']:.1f}%" if (r['lap10_pct'] is not None and not pd.isna(r['lap10_pct'])) else "N/A"
    income_disp = f"${int(r['income']):,}" if (r['income'] is not None and not pd.isna(r['income'])) else "N/A"
    ob_disp = f"{r['obesity']:.1f}%" if (r['obesity'] is not None and not pd.isna(r['obesity'])) else "N/A"
    diab_disp = f"{r['diabetes']:.1f}%" if (r['diabetes'] is not None and not pd.isna(r['diabetes'])) else "N/A"
    inact_disp = f"{r['inactive']:.1f}%" if (r['inactive'] is not None and not pd.isna(r['inactive'])) else "N/A"
    score_disp = f"{round(score,3)}" if score is not None and not (isinstance(score, float) and math.isnan(score)) else "N/A"

    popup_html = (
        f"<div style='max-width:320px;font-family:Arial,Helvetica,sans-serif;'>"
        f"<b>{badge_text} FOOD INSECURITY</b> &nbsp; <i>Rank #{rank}</i><br>"
        f"<b>Tract:</b> {tract}<br>"
        f"<b>Composite score:</b> {score_disp}<br><br>"
        f"<b>Poverty rate:</b> {poverty_disp}<br>"
        f"<b>SNAP (share):</b> {snap_disp}<br>"
        f"<b>% within 1 mile:</b> {lap1_disp} &nbsp; | &nbsp; <b>% within 10 miles:</b> {lap10_disp}<br>"
        f"<b>Median income:</b> {income_disp}<br><br>"
        f"<b>Health:</b> Obesity {ob_disp} &nbsp; Diabetes {diab_disp} &nbsp; Inactive {inact_disp}"
        f"</div>"
    )

    icon_name = "fire" if (isinstance(rank, int) and rank <= 3) else ("exclamation-triangle" if (isinstance(rank, int) and rank <= 7) else "info-circle")
    icon_color = "darkred" if color == "darkred" else ("orange" if color == "orange" else "green")

    folium.Marker(
        location=[float(lat), float(lon)],
        popup=folium.Popup(popup_html, max_width=360),
        tooltip=f"Rank {rank} — Tract {tract}",
        icon=folium.Icon(icon=icon_name, prefix="fa", color=icon_color)
    ).add_to(m)

# legend and save
legend_html = """
<div style="position: fixed; bottom: 12px; left: 10px; width: 300px; height: 140px; 
     border:2px solid grey; z-index:9999; font-size:13px; background:white; padding:8px;">
<b>Legend — Food insecurity composite (CDC-style)</b><br>
🔥 HIGH: severe need (top tier)<br>
⚠️ MEDIUM: moderate need<br>
✅ LOW: lower priority<br>
Icons: fire = top 3 tracts, exclamation = top 4–7<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

valid_pts = [[float(r["lat"]), float(r["lon"])] for _, r in work_sorted.iterrows() if not pd.isna(r["lat"]) and not pd.isna(r["lon"])]
if valid_pts:
    m.fit_bounds(valid_pts, padding=(20, 20))

m.save(OUTPUT_HTML)
print(f"\nMap saved to {OUTPUT_HTML} — open it in your browser to explore.")