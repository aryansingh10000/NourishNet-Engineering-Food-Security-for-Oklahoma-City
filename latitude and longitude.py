import requests
import csv

geoids = [
 "40109108005","40109107900","40109101500","40109107806","40109107703",
 "40109107218","40109105300","40109107002","40109104600","40109101800",
 "40109100900","40109101000","40109101200","40109101300","40109101400",
 "40109100400","40109100800"
]

# Base URL for Census TIGERweb (tracts layer)
base = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/10/query"

def polygon_centroid(coords):
    if isinstance(coords[0][0], float):
        ring = coords
    else:
        ring = coords[0]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return sum(ys) / len(ys), sum(xs) / len(xs)

results = []

# Query each GEOID separately to avoid syntax issues
for geoid in geoids:
    params = {
        "where": f"GEOID='{geoid}'",
        "outFields": "GEOID",
        "returnGeometry": "true",
        "f": "json",
        "outSR": "4326"  # get lon/lat
    }

    resp = requests.get(base, params=params)
    resp.raise_for_status()
    data = resp.json()

    features = data.get("features", [])
    if not features:
        print(f"No data for {geoid}")
        continue

    feat = features[0]
    geom = feat.get("geometry")
    if not geom:
        print(f"No geometry for {geoid}")
        continue

    if "rings" in geom:
        lat, lon = polygon_centroid(geom["rings"])
        results.append((geoid, lat, lon))
    elif "x" in geom and "y" in geom:
        results.append((geoid, geom["y"], geom["x"]))
    else:
        print(f"Unexpected geometry for {geoid}: {geom}")

# Write CSV and print
out_csv = "tract_centroids.csv"
with open(out_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["GEOID", "latitude", "longitude"])
    writer.writerows(results)

print(f"Wrote {len(results)} rows to {out_csv}")
for r in results:
    print(r)
