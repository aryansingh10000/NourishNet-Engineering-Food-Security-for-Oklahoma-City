import pandas as pd

TARGET_TRACTS = [
    "40109108005", "40109107900", "40109101500", "40109107806",
    "40109107703", "40109107218", "40109105300", "40109107002",
    "40109104600", "40109101800", "40109100900", "40109101000",
    "40109101200", "40109101300", "40109101400", "40109100400",
    "40109100800"
]

df = pd.read_csv("food_access.csv", dtype=str)

# 100% confirmed correct USDA columns:
numeric_cols = [
    "PovertyRate", "MedianFamilyIncome",
    "LAPOP1_10",  # ✅ population within 1 mile
    "lapop1share",
    "LAPOP1_20",  # ✅ population within 10 miles
    "lapop20share"
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    else:
        print(f"ERROR: Missing column '{col}' — check spelling in your CSV.")
        exit()

for tract in TARGET_TRACTS:
    row = df[df["CensusTract"] == tract]
    if row.empty:
        print(f"Tract {tract} — NOT FOUND.\n")
        continue

    row = row.iloc[0]

    poverty = f"{row['PovertyRate']:.1f}%" if pd.notna(row['PovertyRate']) else "N/A"
    income = f"${row['MedianFamilyIncome']:,.0f}" if pd.notna(row['MedianFamilyIncome']) else "N/A"

    pop_1 = f"{int(row['LAPOP1_10']):,}" if pd.notna(row['LAPOP1_10']) else "N/A"
    pct_1 = f"{row['lapop1share']:.1f}%" if pd.notna(row['lapop1share']) else "N/A"

    pop_10 = f"{int(row['LAPOP1_20']):,}" if pd.notna(row['LAPOP1_20']) else "N/A"
    pct_10 = f"{row['lapop20share']:.1f}%" if pd.notna(row['lapop20share']) else "N/A"

    print(f"Tract {tract}")
    print(f"Poverty Rate: {poverty}")
    print(f"Median Family Income: {income}")
    print(f"Population within 1 mile: {pop_1} ({pct_1})")
    print(f"Population within 10 miles: {pop_10} ({pct_10})")
    print()  # blank line