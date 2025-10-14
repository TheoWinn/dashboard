import pandas as pd

API_CSV_URL = "https://api.hutt.io/bt-to/csv"
LOCAL_CSV_FILE = "bundestag_actual_speechtime.csv"

# This is for the current year 2025 only (loop over all the other years (2015?) to get all data)
def fetch_full_data():
    print("Downloading latest agenda CSV...")
    df = pd.read_csv(API_CSV_URL)
    print(f"Fetched {len(df)} total rows.")
    return df

# Filter for oktober 2025 and select specific columns (exclude Status/Abstimmung und Details zu den Einzelplänen)
def filter_october_selected_columns(df):
    # Convert 'Start' column to datetime
    df["Start"] = pd.to_datetime(df["Start"], errors="coerce")

    # Filter for Oktober 2025
    mask = (df["Start"].dt.year == 2025) & (df["Start"].dt.month == 10)
    filtered_df = df.loc[mask, ["Start", "Ende", "TOP", "Thema"]].copy()

    print(f"Filtered down to {len(filtered_df)} rows from Oktober 2025 with selected columns.")
    return filtered_df

def save_to_csv(df):
    df.to_csv(LOCAL_CSV_FILE, index=False)
    print(f"Saved filtered data to {LOCAL_CSV_FILE}")

if __name__ == "__main__":
    all_data = fetch_full_data()
    df_october = filter_october_selected_columns(all_data)
    save_to_csv(df_october)

