import pandas as pd
import numpy as np
import re
from ast import literal_eval
from typing import Any, List, Dict, Optional
from pathlib import Path
from yt_utils import parse_words_cell, cluster_transcript, process_one_csv

PROJECT_DIR = Path(__file__).resolve().parent.parent

IN_DIR = PROJECT_DIR/"data"/"transcribed"/"bundestag_transcript"
OUT_DIR = PROJECT_DIR/"data"/"clustered"/"bundestag_clustered"

OUT_DIR.mkdir(parents=True, exist_ok=True)

PATTERN = "*_aligned.csv"
SKIP_ON_MISSING_COLS = False

float64_pattern = re.compile(r"np\.float64\(\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*\)")
nan_pattern = re.compile(r"np\.nan")

if __name__ == "__main__":
    files = sorted(IN_DIR.glob(PATTERN))
    
    if not files:
        print(f"No files found in {IN_DIR} matching {PATTERN}")

    print(f"Found {len(files)} in {IN_DIR} matching '{PATTERN}'.")

    for f in files:
        out_path = OUT_DIR/f"{f.stem.replace('_aligned', '')}_clustered.csv"
        try:
            process_one_csv(f, out_path)
        except Exception as e:
            if SKIP_ON_MISSING_COLS:
                print(f"Skipping {f.name}: {e}")
                continue
            raise

    print(f"All transcripts contianed in {IN_DIR} have been cleaned, clustered, and written to {OUT_DIR}")