import pandas as pd

def main(metadata_file):
    # Load metadata
    df = pd.read_csv(metadata_file, dtype=str)

    # Convert is_complete column to boolean
    # (Your script writes True/False or None as strings)
    df["is_complete_bool"] = df["is_complete"].map(
        lambda x: True if x == "True" else False
    )

    total = len(df)
    incomplete = (~df["is_complete_bool"]).sum()

    percentage_incomplete = (incomplete / total) * 100 if total > 0 else 0

    print(f"Total protocols: {total}")
    print(f"Incomplete protocols: {incomplete}")
    print(f"Percentage incomplete: {percentage_incomplete:.2f}%")

if __name__ == "__main__":
    main("../data/raw/metadata.csv")