from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
import os
import pandas as pd
import numpy as np
from ast import literal_eval
from typing import Any, List, Dict, Optional
from pandas.errors import EmptyDataError
import gc
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import time
import random
import re
from datetime import datetime, date
from slugify import slugify

### YouTube Downloading Utilities ###

def _sanitize_filename(name: str):
    name = re.sub(r"[^\w\s\.-]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "video"

# --- date parsing ---
# Accept weekday (optional comma), "17." then either numeric month "10." or German month name "Oktober", then year.
_WEEKDAY = r"(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonnabend|Sonntag)"
_MONTH_NAME = (
    r"(?:Januar|Jan\.?|Februar|Feb\.?|März|Maerz|Mär\.?|Mrz\.?|April|Apr\.?|"
    r"Mai|Juni|Juli|August|Aug\.?|September|Sep\.?|Sept\.?|Oktober|Okt\.?|"
    r"November|Nov\.?|Dezember|Dez\.?)"
)

# e.g., "Freitag, 17. Oktober 2025"  (weekday + month name)
_DATE_WD_NAME = re.compile(
    rf"\b(?:{_WEEKDAY}),?\s*(\d{{1,2}})\.\s*({_MONTH_NAME})\s+(\d{{4}})\b",
    re.IGNORECASE
)

# e.g., "Freitag, 27.09.2025"  (weekday + numeric)
_DATE_WD_NUM = re.compile(
    rf"\b(?:{_WEEKDAY}),?\s*(\d{{1,2}})\.\s*(\d{{1,2}})\.(\d{{4}})\b",
    re.IGNORECASE
)

# (Optional) also allow same two formats *without* a weekday
_DATE_NAME = re.compile(
    rf"\b(\d{{1,2}})\.\s*({_MONTH_NAME})\s+(\d{{4}})\b",
    re.IGNORECASE
)
_DATE_NUM = re.compile(
    r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b",
    re.IGNORECASE
)

_MONTH_MAP = {
    # full names
    "januar":1, "februar":2, "märz":3, "maerz":3, "april":4, "mai":5, "juni":6, "juli":7,
    "august":8, "september":9, "oktober":10, "november":11, "dezember":12,
    # common abbrevs (strip trailing dot)
    "jan":1, "feb":2, "mär":3, "mrz":3, "apr":4, "aug":8, "sep":9, "sept":9, "okt":10, "nov":11, "dez":12,
}

def _parse_month_token(tok: str) -> int | None:
    t = tok.strip().lower().rstrip(".")
    # normalize umlauts to "ae"/"oe"/"ue" keys if needed
    t_norm = (t
              .replace("ä", "ae")
              .replace("ö", "oe")
              .replace("ü", "ue"))
    return _MONTH_MAP.get(t) or _MONTH_MAP.get(t_norm)

def _date_from_description(desc: str) -> str | None:
    """
    Extracts a German date from YouTube description.
    Supports:
      - "Freitag, 17. Oktober 2025"
      - "Freitag, 27.09.2025"
      - "17. Oktober 2025"
      - "27.09.2025"
    Returns "DD-MM-YYYY" or None.
    """
    if not desc:
        return None

    # 1) Prefer weekday + month name
    m = _DATE_WD_NAME.search(desc)
    if m:
        d, mon_tok, y = m.groups()
        mon = _parse_month_token(mon_tok)
        if mon:
            try:
                return datetime(int(y), int(mon), int(d)).strftime("%d-%m-%Y")
            except ValueError:
                return None

    # 2) Weekday + numeric
    m = _DATE_WD_NUM.search(desc)
    if m:
        d, mon, y = map(int, m.groups())
        try:
            return datetime(y, mon, d).strftime("%d-%m-%Y")
        except ValueError:
            return None

    # 3) Without weekday: name month
    m = _DATE_NAME.search(desc)
    if m:
        d, mon_tok, y = m.groups()
        mon = _parse_month_token(mon_tok)
        if mon:
            try:
                return datetime(int(y), int(mon), int(d)).strftime("%d-%m-%Y")
            except ValueError:
                return None

    # 4) Without weekday: numeric
    m = _DATE_NUM.search(desc)
    if m:
        d, mon, y = map(int, m.groups())
        try:
            return datetime(y, mon, d).strftime("%d-%m-%Y")
        except ValueError:
            return None

    return None

def download_from_playlist(playlist_url, bundestag: bool = True, talkshow_name: str = None, test_mode: bool = False, cutoff = date(2025, 1, 1)):
    """
    Download audio files from a YouTube playlist and save metadata into csv file. It will all be saved in the specified output directory.
    If the output directory is empty, all files from the playlist will be downloaded.
    Also gets the Date from the YouTube Description and adds it as file pre-fix. 
    New files will be {date}_{YouTubeTitle}.m4a
    """

    project_dir = Path(__file__).resolve().parent.parent

    if bundestag:
        output_dir = project_dir/"data"/"raw"/"bundestag_audio"
    else:
        output_dir = project_dir/"data"/"raw"/"talkshow_audio"

    output_dir.mkdir(parents=True, exist_ok=True)

    meta_file = output_dir/"metadata.csv"

    # get playlist
    print("Creating Playlist object...")
    p = Playlist(playlist_url) 
    print("Found", len(p.video_urls), "videos")

    if meta_file.exists():
        try:
            meta = pd.read_csv(meta_file, header = None)
            urls = meta[0].tolist()
            meta = meta.values.tolist()
        except EmptyDataError:
            meta, urls = [], []
    else:
        meta, urls = [], []


    # download missing audio files and update downloaded ids
    count = 0
    skipped_cutoff_consecutive = 0
    max_consecutive_cutoff_skips = 20

    for url in p.video_urls:
        if url not in urls: 
            try:
                # download audio
                # yt = YouTube(url, client = "ANDROID_EMBED", on_progress_callback=on_progress)
                yt = YouTube(url, on_progress_callback=on_progress)

                # check whether the video is not a short (short is less than 4 minutes)
                if yt.length < 240:
                    print(f'Skipping short video: {yt.title} ({yt.length} seconds)')
                    continue

                publish_date = yt.publish_date.date()   # strip timezone + time

                # check that the publish date is after or on cutoff
                if publish_date < cutoff:
                    skipped_cutoff_consecutive += 1
                    if skipped_cutoff_consecutive >= max_consecutive_cutoff_skips:
                        print(f"Reached {skipped_cutoff_consecutive} consecutive videos before cutoff date. Stopping download.")
                        break
                    continue
                else:
                    skipped_cutoff_consecutive = 0  # reset counter

                print(f'Downloading: {yt.title}')

                date_prefix = _date_from_description(yt.description or "")
                if not date_prefix:
                    if getattr(yt, "publish_date", None):
                        date_prefix = yt.publish_date.strftime("%d-%m-%Y")
                    else:
                        date_prefix = datetime.today().strftime("%d-%m-%Y")

                # safe_title = _sanitize_filename(yt.title)
                safe_title = slugify(yt.title)
                filename_stem = f"{date_prefix}_{safe_title}.m4a"

                ys = yt.streams.get_audio_only()
                # ys = yt.streams.filter(only_audio=True, file_extension="m4a").order_by('abr').desc().first()
                ys.download(output_path=str(output_dir), filename = filename_stem)
                # append to dataframe
                # title = yt.title
                channel = yt.author
                date = date_prefix

                if bundestag:
                    meta.append([url, safe_title, channel, date])
                    pd.DataFrame(meta, columns=["url", "title", "channel", "date"]).to_csv(
                        meta_file, index=False, header=False)
                else:
                    meta.append([url, safe_title, channel, date, talkshow_name])
                    pd.DataFrame(meta, columns=["url", "title", "channel", "date", "talkshow_name"]).to_csv(
                        meta_file, index=False, header=False)

                count += 1

                # for testing: limit to 2 downloads
                if test_mode and count >= 2:
                    print("Test mode active - stopping after 2 downloads.")
                    break

                sleep_seconds = random.uniform(2.0, 6.0)
                print(f"Sleeping {sleep_seconds:.1f}s before next download...")
                time.sleep(sleep_seconds)
                if count % 20 == 0:
                    cooldown = random.uniform(3600.0, 7200.0)
                    current_time = datetime.now().strftime("%H:%M:%S")
                    print(f"[{current_time}]: Reached {count} videos — cooling down for {cooldown/3600:.1f} hours...")
                    time.sleep(cooldown)

            except Exception as e:
                print(f"Error downloading {url}: {e}")
                if "bot" in e:
                    print("Detected bot prevention - stopping further downloads.")
                    return e
                continue

    # save updated dataframe
    # meta = pd.DataFrame(meta, columns=["url", "title", "channel", "date"])
    # meta.to_csv(meta_file, index=False, header=False)


# Example usage
# download_from_playlist("https://www.youtube.com/playlist?list=PL4izbwXmh0jonTVHpB1VtSYgR48lq6eN4")

### WhisperX Transcription & Alignment Utilities ###

def process_one_file(audio_path: Path, out_dir: Path, model_dir: Path, device: str = "cuda", compute_type: str = "float16", batch_size: int = 32, forced_language: str = "de", HF_TOKEN: str = None):
    """
    Processes exactly one file in the specified input directory, which currently is set to be created in the parent folder of
    yt_utils.py own parent folder to follow the project structure.

    Args:
        - audio_path: Path object, needs to be specified in the loop
        - Rest is set to sensible defaults
    """
    try:
        import whisperx
        from whisperx.diarize import DiarizationPipeline
        import torch
    except Exception as e:
        raise RuntimeError(
            "Failed to import whisperx/torch. Install compatible versions in this env "
            "(e.g., pip install whisperx torch torchvision torchaudio)."
        ) from e

    print(f"\n--- Processing: {audio_path.name} ---")

    t0 = time.time()

    model = model_a = metadata = diarize_model = audio = result = diarize_segments = None
    try:
        # ASR
        model = whisperx.load_model(
            "large-v2",
            device=device,
            compute_type=compute_type,
            download_root=model_dir,
            language=forced_language
        )
        audio = whisperx.load_audio(str(audio_path))
        result = model.transcribe(audio, batch_size=batch_size)

        # Align
        lang_code = result.get("language") or forced_language or "en"
        model_a, metadata = whisperx.load_align_model(language_code=lang_code, device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        # Diarize
        if not HF_TOKEN:
            raise RuntimeError("HF_TOKEN not set (required for pyannote diarization).")
        diarize_model = DiarizationPipeline(use_auth_token=HF_TOKEN, device=device)
        # e.g. diarize_model(audio, min_speakers=1, max_speakers=8)
        diarize_segments = diarize_model(audio)
        result = whisperx.assign_word_speakers(diarize_segments, result)

        # Save
        out_csv = out_dir / f"{audio_path.stem}_aligned.csv"
        pd.DataFrame(result["segments"]).to_csv(out_csv, index=False)
        print(f"Done {audio_path.name} in {time.time()-t0:.1f}s → {out_csv.name}")

    except torch.cuda.OutOfMemoryError:
        print("CUDA OOM. Try lower batch_size (e.g., 16/8) or set device='cpu'.")
    except Exception as e:
        print(f"Error on {audio_path.name}: {e}")
    finally:
        # Cleanup always
        del model, model_a, metadata, diarize_model, audio, result, diarize_segments
        gc.collect()
        if device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()


### Cleaning & Clustering Utilities ###

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