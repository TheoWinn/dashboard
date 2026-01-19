import os
import pandas as pd
import whisperx
from whisperx.diarize import DiarizationPipeline
import gc
import torch
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import time
from yt_utils import process_one_file
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--bundestag",
    action = "store_true",
    help = "Use Bundestag Audio Directory. If not set, talkshow directory will be used."
)

args = parser.parse_args()

# .env imports
env_path = find_dotenv()
load_dotenv(env_path)

HF_TOKEN = os.getenv("HF_TOKEN")

# Path setup
AUDIO_EXTS = {".m4a"}
BUNDESTAG = args.bundestag

project_dir = Path(__file__).resolve().parent.parent

model_dir = project_dir / "models"
model_dir.mkdir(parents=True, exist_ok=True)

if BUNDESTAG:
    in_dir = project_dir/"data"/"raw"/"bundestag_audio"
    in_dir.mkdir(parents=True, exist_ok=True)

    out_dir = project_dir/"data"/"transcribed"/"bundestag_transcript"
    out_dir.mkdir(parents=True, exist_ok=True)

if not BUNDESTAG:
    in_dir = project_dir/"data"/"raw"/"talkshow_audio"
    in_dir.mkdir(parents=True, exist_ok=True)

    out_dir = project_dir/"data"/"transcribed"/"talkshow_transcript"
    out_dir.mkdir(parents=True, exist_ok=True)

print("Path to model: ", model_dir)
print("Input path: ", in_dir)
print("Output path: ", out_dir)

# WhisperX "hyperparameters"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16"
BATCH_SIZE = 32
FORCED_LANGUAGE = "de"

if DEVICE == "cpu":
    COMPUTE_TYPE = "int8"


if __name__ == "__main__":
    start_all = time.time()
    files = [p for p in in_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS]

    if not files:
        print("No audio/video files found in: ", in_dir)
        print("\n Exiting script without any results.")
        exit()

    failed = []

    for i, f in enumerate(files, start = 1):

        out_file = out_dir / f"{f.stem}_aligned.csv"

        if out_file.exists():
            # print(f"Skipping {f.name}, already transcribed.")
            continue
        
        print(f"\n ### File {i}/{len(files)} ###")
        ok, err = process_one_file(audio_path = f, 
                                   out_dir = out_dir, 
                                   model_dir = model_dir,
                                   device = DEVICE,
                                   compute_type = COMPUTE_TYPE,
                                   batch_size = BATCH_SIZE,
                                   forced_language = FORCED_LANGUAGE,
                                   HF_TOKEN = HF_TOKEN
                                   )
        if not ok:
            failed.append((f, err))
        print("Cache cleared, moving to next file... \n")

    print(f"All done in {time.time() - start_all:.1f}s total.")
    print(f"Summary: total={len(files)}, failed={len(failed)}")
    if failed:
        print("\nFailures:")
        for f, err in failed:
            print(f"- {f.name}: {err}")