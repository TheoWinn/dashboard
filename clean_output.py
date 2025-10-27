import pandas as pd
import numpy as np
import re
from ast import literal_eval
from typing import Any, List, Dict, Optional
from pathlib import Path

# Setup
IN_DIR = Path("data/out")
OUT_DIR = Path("data/cleaned")
PATTERN = "*_aligned.csv"
SKIP_ON_MISSING_COLS = False

OUT_DIR.mkdir(parents=True, exist_ok = True)

float64_pattern = re.compile(r"np\.float64\(\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*\)")
nan_pattern = re.compile(r"np\.nan")


def parse_words_cell(cell: Any) -> List[Any]:
    """
    Converts "words" column from mixed format with "np.float64" or "np.nan"
    """
    if pd.isna(cell):
        return []
    if isinstance(cell, list):
        return cell

    s = str(cell)
    s = float64_pattern.sub(r"\1", s)
    s = nan_pattern.sub("None", s)

    try:
        obj = literal_eval(s)
    except Exception:
        return [s]

    return obj if isinstance(obj, list) else [obj]

def cluster_transcript(df: pd.DataFrame) -> pd.DataFrame:
    required = {"speaker", "text", "start", "end", "words"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.reset_index(drop = True).copy()
    df["__words_list__"] = df["words"].apply(parse_words_cell)

    clusters = []
    current = None

    def flush_current():
        if current is not None:
            clusters.append(current.copy())

    for _, row in df.iterrows():
        speaker = row["speaker"]
        start = float(row["start"])
        end = float(row["end"])
        text = str(row["text"]) if pd.notna(row["text"]) else ""
        words_list = row["__words_list__"]

        if current is None or speaker != current["speaker"]:
            flush_current()
            current = {
                "cluster_idx": len(clusters),
                "speaker": speaker,
                "start": start,
                "end": end,
                "text_parts": [text] if text else [],
                "words_concat": list(words_list)
            }
        else:
            current["end"] = max(current["end"], end)
            if text:
                current["text_parts"].append(text)
            if words_list:
                current["words_concat"].extend(words_list)

    flush_current()

    out = pd.DataFrame({
        "cluster_idx": [c["cluster_idx"] for c in clusters],
        "speaker": [c["speaker"] for c in clusters],
        "start": [c["start"] for c in clusters],
        "end": [c["end"] for c in clusters],
        "text": [" ".join(c["text_parts"]).strip() for c in clusters],
        "words": [repr(c["words_concat"]) for c in clusters]
    })


    out["speaker_block"] = (
        out["speaker"] != out["speaker"].shift(1)
    ).groupby(out["speaker"]).cumsum()

    return out

def process_one_csv(in_csv: Path, out_csv: Path):
    print(f"Processing: {in_csv.name}")
    df = pd.read_csv(in_csv)
    out = cluster_transcript(df)
    out.to_csv(out_csv, index = False)
    print(f"Wrote {out_csv.name} ({len(out)} clusters)")

def main():
    files = sorted(IN_DIR.glob(PATTERN))
    if not files:
        print(f"No files found in {IN_DIR} matching '{PATTERN}'.")
        return
    
    print(f"Found {len(files)} in {IN_DIR}. Writing to {OUT_DIR} \n")
    for f in files:
        out_path = OUT_DIR/f"{f.stem.replace('_aligned', '')}_clustered.csv"
        try:
            process_one_csv(f, out_path)
        except Exception as e:
            if SKIP_ON_MISSING_COLS:
                print(f"Skipping {f.name}: {e}")
                continue
            raise

    print(f"All transcripts contained in {IN_DIR} have been cleaned and clustered")


if __name__ == "__main__":
    main()


# # - Setup - Provide Input and Output Files here
# INPUT_CSV  = "data/transcript_aligned.csv"
# OUTPUT_CSV = "data/transcript_aligned_clustered.csv"

# # Clean out np.float and np.nan
# float64_pattern = re.compile(r"np\.float64\(\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*\)")
# nan_pattern = re.compile(r"np\.nan")

# def parse_words_cell(cell: Any) -> List[Any]:
#     """
#     Converts the 'words' column from its mixed format (stringified list with np.float64)
#     into a clean Python list of dicts or strings.
#     """
#     if pd.isna(cell):
#         return []
#     if isinstance(cell, list):
#         return cell

#     s = str(cell)
#     # Strip out any np.float() text in csv
#     s = float64_pattern.sub(r"\1", s)
#     # Strip out any np.nan() text in csv for None
#     s = nan_pattern.sub("None", s)

#     try:
#         obj = literal_eval(s)
#     except Exception:
#         # Fallback: store the raw string inside a single-element list
#         return [s]

#     return obj if isinstance(obj, list) else [obj]


# # Load csv that needs to be cleaned
# df = pd.read_csv(INPUT_CSV).reset_index(drop=True)

# # Check that every column is present and abort if input format is not matching
# required = {"speaker", "text", "start", "end", "words"}
# missing = required - set(df.columns)
# if missing:
#     raise ValueError(f"Missing required columns in the input CSV: {missing}")

# # Clean Cells from np.nan or np.float using parse_words_cell()
# df["__words_list__"] = df["words"].apply(parse_words_cell)


# clusters = [] # Create cluster list
# current = None

# def flush_current() -> None:
#     if current is not None:
#         clusters.append(current.copy())

# for idx, row in df.iterrows(): # Loop through indexes and rows in dataframe
#     speaker = row["speaker"] # Extract current speaker ID
#     start = float(row["start"]) # Extract current start stamp
#     end   = float(row["end"]) # Extract current end stamp
#     text  = str(row["text"]) if pd.notna(row["text"]) else "" # Extract text, if None return empty string
#     words_list = row["__words_list__"] # Extract words_list (cleaned word-level timestamps)

#     if current is None or speaker != current["speaker"]: # Start new cluster if current is None or if the speaker has changed
#         flush_current()
#         current = { # Create a new cluster if current cluster is either None or the speaker has changed
#             "cluster_idx": len(clusters),
#             "speaker": speaker,
#             "start": start,
#             "end": end,
#             "text_parts": [text] if text else [],
#             "words_concat": list(words_list),
#         }
#     else: # If we are still within the same speaker
#         # Extend current cluster
#         current["end"] = max(current["end"], end) # Assign max end to new row end (min is kept as is)
#         if text:
#             current["text_parts"].append(text) # Merge the text fields belonging to the same speaker
#         if words_list:
#             current["words_concat"].extend(words_list)

# flush_current() # End the very last cluster

# # Take cluster list and extract each item into the dataframe
# out = pd.DataFrame({
#     "cluster_idx": [c["cluster_idx"] for c in clusters],
#     "speaker":     [c["speaker"] for c in clusters],
#     "start":       [c["start"] for c in clusters],
#     "end":         [c["end"] for c in clusters],
#     "text":        [" ".join(c["text_parts"]).strip() for c in clusters],
#     "words":       [repr(c["words_concat"]) for c in clusters],  # keep as literal string
# })

# # Optional: number of each consecutive block per speaker
# out["speaker_block"] = (
#     out["speaker"] != out["speaker"].shift(1)
# ).groupby(out["speaker"]).cumsum()

# # Save output as csv file and print success message
# out.to_csv(OUTPUT_CSV, index=False)
# print(f"Done. Wrote {len(out)} clusters to {OUTPUT_CSV}")
