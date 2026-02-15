import pandas as pd
import re
from sklearn.linear_model import LinearRegression

# Load
df = pd.read_csv("okc_data.csv")
df.columns = df.columns.str.strip().str.lower()

print("Columns found:", df.columns.tolist())

# --- Helper to find columns ---
def find_col(keyword):
    for c in df.columns:
        if keyword in c:
            return c
    return None

poverty_col = find_col("poverty")
income_col = find_col("income")
grocery_col = find_col("grocery")
obesity_col = find_col("obesity")
diabetes_col = find_col("diabetes")
inactive_col = find_col("inactive")

print("Using:")
print(poverty_col, income_col, grocery_col)

# --- Percent extractor ---
def get_pct(x):
    if pd.isna(x):
        return None
    s = str(x)

    # grab percent in parentheses first
    m = re.search(r"\(([\d.]+)%\)", s)
    if m:
        return float(m.group(1))

    # otherwise percent sign
    m = re.search(r"([\d.]+)%", s)
    if m:
        return float(m.group(1))

    # fallback number
    m = re.search(r"[\d.]+", s)
    if m:
        return float(m.group())

    return None

# --- Build variables ---
df["poverty"] = pd.to_numeric(df[poverty_col], errors="coerce")
df["income"] = pd.to_numeric(df[income_col], errors="coerce")

df["obesity"] = pd.to_numeric(df[obesity_col], errors="coerce")
df["diabetes"] = pd.to_numeric(df[diabetes_col], errors="coerce")
df["inactive"] = pd.to_numeric(df[inactive_col], errors="coerce")

df["health"] = df[["obesity","diabetes","inactive"]].mean(axis=1)

df["grocery"] = df[grocery_col].apply(get_pct)

# Outcome: low access
df["low_access"] = 100 - df["grocery"]

# Drop missing
df = df.dropna(subset=["poverty","income","health","low_access"])

print("Rows used:", len(df))

# --- Regression ---
X = df[["poverty","health","income"]]
y = df["low_access"]

model = LinearRegression().fit(X,y)

print("\nWeights:")
for name,coef in zip(X.columns, model.coef_):
    print(name, round(coef,3))

print("\nR²:", round(model.score(X,y),3))