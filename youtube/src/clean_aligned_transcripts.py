import pandas as pd
import numpy as np
import re
from ast import literal_eval
from typing import Any, List, Dict, Optional
from pathlib import Path
from yt_utils import parse_words_cell, cluster_transcript, process_one_csv
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--bundestag",
    action = "store_true",
    help = "Use Bundestag Audio Directory. If not set, talkshow directory will be used."
)

args = parser.parse_args()

BUNDESTAG = args.bundestag

PROJECT_DIR = Path(__file__).resolve().parent.parent


if BUNDESTAG:
    in_dir = PROJECT_DIR/"data"/"transcribed"/"bundestag_transcript"
    in_dir.mkdir(parents=True, exist_ok=True)

    out_dir = PROJECT_DIR/"data"/"clustered"/"bundestag_clustered"
    out_dir.mkdir(parents=True, exist_ok=True)

if not BUNDESTAG:
    in_dir = PROJECT_DIR/"data"/"transcribed"/"talkshow_audio"
    in_dir.mkdir(parents=True, exist_ok=True)

    out_dir = PROJECT_DIR/"data"/"clustered"/"talkshow_clustered"
    out_dir.mkdir(parents=True, exist_ok=True)

print("Input Directory: ", in_dir)
print("Output Directory: ", out_dir)

PATTERN = "*_aligned.csv"
SKIP_ON_MISSING_COLS = False

float64_pattern = re.compile(r"np\.float64\(\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*\)")
nan_pattern = re.compile(r"np\.nan")

if __name__ == "__main__":
    files = sorted(in_dir.glob(PATTERN))
    
    if not files:
        print(f"No files found in {in_dir} matching {PATTERN}")

    print(f"Found {len(files)} in {in_dir} matching '{PATTERN}'.")

    for f in files:
        out_path = out_dir/f"{f.stem.replace('_aligned', '')}_clustered.csv"

        if out_path.exists():
            print(f"Skipping {f.name} for it has already been cleaned!")
            continue

        try:
            process_one_csv(f, out_path)
        except Exception as e:
            if SKIP_ON_MISSING_COLS:
                print(f"Skipping {f.name}: {e}")
                continue
            raise

    print(f"All transcripts contianed in {in_dir} have been cleaned, clustered, and written to {out_dir}")