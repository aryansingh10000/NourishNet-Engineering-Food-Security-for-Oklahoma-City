import pandas as pd
import numpy as np
from libpysal.weights import KNN
from esda.moran import Moran

CSV_FILE = "okc_data.csv"

df = pd.read_csv(CSV_FILE)

# ---- CLEAN ----
df.columns = df.columns.str.strip().str.lower()

def clean(x):
    if pd.isna(x): return np.nan
    s = str(x).replace("%","").replace("$","").replace(",","")
    try: return float(s)
    except: return np.nan

df["poverty"] = df["% below poverty"].apply(clean)
df["obesity"] = df["adult obesity %"].apply(clean)
df["diabetes"] = df["adult diabetes %"].apply(clean)
df["inactive"] = df["% of adults physically inactive"].apply(clean)

# simple health index like you used
df["health"] = df[["obesity","diabetes","inactive"]].mean(axis=1)

# parse lat/lon from coordinate column
coords = df["latitude"].str.extract(r"(-?\d+\.\d+).*(-?\d+\.\d+)")
df["lat"] = coords[0].astype(float)
df["lon"] = coords[1].astype(float)

# drop missing
df = df.dropna(subset=["lat","lon","poverty"])

# ---- MORAN'S I ----
coords = list(zip(df["lon"], df["lat"]))

w = KNN.from_array(coords, k=4)
w.transform = "R"

y = df["poverty"].values

mi = Moran(y, w)

print("Moran's I:", round(mi.I,4))
print("p-value:", round(mi.p_sim,4))