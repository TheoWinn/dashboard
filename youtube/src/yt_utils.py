from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
import os
import pandas as pd
import whisperx
from whisperx.diarize import DiarizationPipeline
import gc
import torch
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import time

def download_from_playlist(playlist_url, output_dir="data/raw_audio_talkshows"):
    """
    Download audio files from a YouTube playlist and save metadata into csv file. It will all be saved in the specified output directory.
    If the output directory is empty, all files from the playlist will be downloaded.
    """

    # get playlist
    p = Playlist(playlist_url)

    # read downloaded ids
    if len(os.listdir(output_dir)) == 0:
        meta = []
        urls = []
    else:
        meta = pd.read_csv(output_dir + "/metadata.csv", header=None)
        urls = meta[0].tolist() 
        meta = meta.values.tolist()   


    # download missing audio files and update downloaded ids
    if len(urls) < len(p.video_urls):
        for url in p.video_urls:
            if url not in urls: 
                # download audio
                yt = YouTube(url, on_progress_callback=on_progress)
                print(f'Downloading: {yt.title}')
                ys = yt.streams.get_audio_only()
                ys.download(output_path=output_dir)
                # append to dataframe
                title = yt.title
                channel = yt.author
                date = yt.publish_date
                meta.append([url, title, channel, date])

    # save updated dataframe
    meta = pd.DataFrame(meta, columns=["url", "title", "channel", "date"])
    meta.to_csv(output_dir + "/metadata.csv", index=False, header=False)


# Example usage
# download_from_playlist("https://www.youtube.com/playlist?list=PL4izbwXmh0jonTVHpB1VtSYgR48lq6eN4")


def process_one_file(audio_path: Path, out_dir: Path, model_dir: Path, device: str = "cuda", compute_type: str = "float16", batch_size: int = 32, forced_language: str = "de", HF_TOKEN: str = None):
    """
    Processes exactly one file in the specified input directory, which currently is set to be created in the parent folder of
    yt_utils.py own parent folder to follow the project structure.

    Args:
        - audio_path: Path object, needs to be specified in the loop
        - Rest is set to sensible defaults
    """
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