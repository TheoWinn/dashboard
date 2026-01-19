import argparse
import os
import re
import time

from pytubefix import Playlist, YouTube
import pytubefix.request as req

PLAYLIST_URL = "https://www.youtube.com/watch?v=4Y1lZQsyuSQ&list=PLIpXfMcU3wW9uMPHeo9m_ZTnxfsMPW5za"


def safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name)
    return name[:180] if len(name) > 180 else name


def get_repo_root() -> str:
    # file is: <repo>/orphan/new_sources/get_youtube.py
    # repo root is: three levels up
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=str,
        default="orphan/new_sources/out/youtube",  # <<< changed
        help="Path relative to repo root (default: orphan/new_sources/out/youtube)",
    )
    parser.add_argument("--max-videos", type=int, default=3)
    parser.add_argument("--audio-only", action="store_true")
    parser.add_argument("--many-videos", action="store_true")
    parser.add_argument("--reduce-memory", action="store_true")
    parser.add_argument("--use-oauth", action="store_true")
    args = parser.parse_args()

    if args.reduce_memory:
        req.default_range_size = 1024 * 1024  # 1 mb

    repo_root = get_repo_root()
    output_dir = os.path.abspath(os.path.join(repo_root, args.output_dir))

    # <<< changed: do NOT create directories, fail if missing
    if not os.path.isdir(output_dir):
        raise FileNotFoundError(
            f"Output directory does not exist: {output_dir}\n"
            f"Create it first (mkdir -p orphan/new_sources/out/youtube) "
            f"or pass an existing path via --output-dir."
        )  # os.path.isdir is the correct check for directories 

    print("Saving to:", output_dir)

    pl = Playlist(PLAYLIST_URL)
    urls = list(pl.video_urls)[: args.max_videos]
    print(f"Playlist loaded. Downloading {len(urls)} video(s).")

    for i, url in enumerate(urls, start=1):
        yt = YouTube(url, use_oauth=True, allow_oauth_cache=True) if args.use_oauth else YouTube(url)
        title = safe_filename(getattr(yt, "title", f"video_{i}"))
        print(f"\n[{i}/{len(urls)}] {title}")

        stream = yt.streams.get_audio_only() if args.audio_only else yt.streams.get_highest_resolution()
        stream.download(output_path=output_dir, filename=f"{title}.mp4")

        time.sleep(20 if args.many_videos else 3)

    print("\nDone.")


if __name__ == "__main__":
    main()


# in bash run uv run orphan/new_sources/get_youtube.py --max-videos 3 --audio-only --many-videos --use-oauth
# follow oAuth process from console
