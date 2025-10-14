import pandas as pd

# Path to your CSV file (change if needed)
file_path = "census.csv"

# Read the dataset safely
df = pd.read_csv(file_path, encoding='utf-8', low_memory=False, on_bad_lines='skip')

# Show available columns to confirm structure
print("Columns in dataset:\n")
print(df.columns.tolist())

# List of tract IDs you want
tracts_of_interest = [
    40109108005,
    40109107900,
    40109101500,
    40109107806,
    40109107703,
    40109107218,
    40109105300,
    40109107002,
    40109104600,
    40109101800,
    40109100900,
    40109101000,
    40109101200,
    40109101300,
    40109101400,
    40109100400,
    40109100800
]

# Normalize column names (makes it easier to work with)
df.columns = df.columns.str.strip().str.lower()

# Filter down to only the tracts you want
df_filtered = df[df["tractfips"].isin(tracts_of_interest)]

# Select useful columns — keeping key health measures
columns_to_keep = [
    "stateabbr",
    "countyname",
    "tractfips",
    "obesity_crudeprev",
    "diabetes_crudeprev",
    "lpa_crudeprev"
]

# Some columns may not exist depending on version, so only keep what’s available
available_columns = [c for c in columns_to_keep if c in df_filtered.columns]
df_filtered = df_filtered[available_columns]

# Rename columns to friendlier names
df_filtered = df_filtered.rename(columns={
    "obesity_crudeprev": "Adult_Obesity_%",
    "diabetes_crudeprev": "Adult_Diabetes_%",
    "lpa_crudeprev": "% Physically_Inactive"
})

# Show results
print("\nFiltered data for selected tracts:\n")
print(df_filtered.head())

# Save to a new CSV
output_path = "tract_health_data.csv"
df_filtered.to_csv(output_path, index=False)
print(f"\nFiltered data saved to: {output_path}")
