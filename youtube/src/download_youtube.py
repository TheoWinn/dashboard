# download_playlist_simple.py
from yt_utils import download_from_playlist
import pytubefix.request as req

# Optional: reduce memory usage
req.default_range_size = 128 * 1024  # 128 KB chunks

if __name__ == "__main__":
    playlist_url = "https://www.youtube.com/playlist?list=PLfRDp3S7rLduqUTa6oXe_Zlv7bEeD06t6"
    bundestag = True  # or False for talkshow path

    print("Starting download…")
    print("Playlist:", playlist_url)
    print("Bundestag:", bundestag)
    print("Chunk size:", req.default_range_size, "bytes")
    print("-" * 60)

    try:
        download_from_playlist(playlist_url, bundestag=bundestag)
    except KeyboardInterrupt:
        print("\n⏹️  Download stopped by user.")