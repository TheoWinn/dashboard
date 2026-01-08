# download_playlist_simple.py
from yt_utils import download_from_playlist
import pytubefix.request as req
import traceback
from datetime import date
import argparse

##### HOW TO USE:
# The script must be run from the command line. (You have to be in the youtube/src/ directory)
# Available arguments:
# --cutoff: Cutoff date in YYYY-MM-DD format (default: 2025-01-01)
# --test-mode: Enable test mode (max 2 videos)
# --reduce-memory: Reduce memory usage by lowering chunk size (only use this for cluster)
# --many-videos: Enable many videos mode (leads to longer pauses between downloads to avoid bot detection) --> do this when downloading many videos in one go, i.e. not for weekly downloads
# --source: Source to download from: 'bundestag', 'talkshows', or 'both' (default: both)
# Example usage:
# uv run download_youtube.py --cutoff 2023-01-01 --test-mode --reduce-memory
# --> this will download videos uploaded after or on 1st Jan 2023, in test_mode: max 2 videos per playlist, with reduced memory usage
# uv run download_youtube.py --cutoff 2024-06-01 --many-videos --source talkshows
# --> this will download talkshow (!) videos uploaded after or on 1st June 2024, full download, normal memory usage, with many-videos mode enabled 


dict_of_talkshow_playlists = {
    "hart_aber_fair": "https://www.youtube.com/playlist?list=PLkKDSXRppVa4b810iSTCbsR3Vw80eV2zB", # oldest from 1 year ago (Tagesschau)
    # "test_bullshit": "lalalala",
    "caren_miosga": "https://www.youtube.com/playlist?list=PLkKDSXRppVa4grZmSCGexQbwMfd9TylEi", # oldest from 1 year ago (Tagesschau)
    "maischberger": "https://www.youtube.com/playlist?list=PLkKDSXRppVa7Ao8LyGQ0JpwHXwjSjMo7-", # oldest from 4 years ago (Tagesschau) 
    "markus_lanz": "https://www.youtube.com/playlist?list=PLdPrKDvwrog6SPKzMAVh1d6cPVtGtDIeT", # oldest from 5 years ago (ZDFheute Nachrichten) 
    "maybrit_illner": "https://www.youtube.com/playlist?list=PLdPrKDvwrog5MvFTzlxs5L5QUazkvCeYa", # oldest from 5 years ago (ZDFheute Nachtichten) 
    "phoenix_2025": "https://www.youtube.com/playlist?list=PLoeytWjTuSup-ULnzO9iPf_Fqvc8DhNTq" ,
    "phoenix_2024": "https://www.youtube.com/playlist?list=PLoeytWjTuSurPoOBmZqJjnlM0BkPtmynl",
    "phoenix_2023": "https://www.youtube.com/playlist?list=PLoeytWjTuSuph1fmTPec5GrvDS0Ro4Lke",
    "phoenix_2022": "https://www.youtube.com/playlist?list=PLoeytWjTuSuoJGJ4KZanLHkYJ1X-s-Z9s",
    "phoenix_2021": "https://www.youtube.com/playlist?list=PLoeytWjTuSuqrX8hE6nFL79YK2ejWibix",
    "phoenix_2020": "https://www.youtube.com/playlist?list=PLoeytWjTuSuryaxF3JuROt8Aoq7ZAS0zZ",
    "phoenix_2019": "https://www.youtube.com/playlist?list=PLoeytWjTuSup3G39MiY8d-O4KYJt9RuqC",
    "phoenix_2018": "https://www.youtube.com/playlist?list=PLoeytWjTuSurAWTjJcJnqkgbzElGn8CYV",
    "phoenix_2017": "https://www.youtube.com/playlist?list=PLoeytWjTuSupmIfrZIGG9qihmKYVNck4p"
}

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", type=str, default="2025-01-01",
                        help="Cutoff date in YYYY-MM-DD format")
    parser.add_argument("--test-mode", action="store_true",
                        help="Enable test mode (max 2 videos)")
    parser.add_argument("--reduce-memory", action="store_true",
                        help="Reduce memory usage by lowering chunk size")
    parser.add_argument("--many-videos", action="store_true",
                        help="Enable many videos mode (leads to longer pauses between downloads to avoid bot detection)")
    parser.add_argument("--source", type=str, default="both",
                        help="Source to download from: 'bundestag', 'talkshows', or 'both' (default: 'both')")
    args = parser.parse_args()

    cutoff = date.fromisoformat(args.cutoff)
    if args.reduce_memory:
        req.default_range_size = 1024 * 1024 
        print(f"Reduced memory usage: chunk size set to {req.default_range_size} bytes")
    test_mode = args.test_mode
    many_mode = args.many_videos
    
    def main(playlist_url, bundestag, talkshow_name, test_mode, cutoff, many_mode):
        print("Starting download…")
        print("Playlist:", playlist_url)
        print("Bundestag:", bundestag)
        #print("Chunk size:", req.default_range_size, "bytes")
        print("-" * 60)

        try:
            print("in try")
            error = download_from_playlist(playlist_url=playlist_url, bundestag=bundestag, talkshow_name=talkshow_name, test_mode=test_mode, cutoff=cutoff, many_mode=many_mode)
            return error
        except KeyboardInterrupt:
            print("Download stopped manually")
            return "KeyboardInterrupt"
        except Exception as e:
            print("NOOOOOOOO an error occurred")
            traceback.print_exc()
            return traceback.format_exc()
        

    error_summary = {}
    source = args.source

    # Bundestag playlist
    if source in ["bundestag", "both"]:
        error_info = main(playlist_url="https://www.youtube.com/playlist?list=PLfRDp3S7rLduqUTa6oXe_Zlv7bEeD06t6", talkshow_name=None, bundestag=True, test_mode=test_mode, cutoff=cutoff, many_mode=many_mode)
        if error_info:
            error_summary["bundestag"] = error_info

    # Talkshow playlists
    if source in ["talkshows", "both"]:
        for playlist_name, playlist_url in dict_of_talkshow_playlists.items():
            print(f"\nDownloading from talkshow playlist: {playlist_name}")
            error_info = main(playlist_url=playlist_url, bundestag=False, talkshow_name=playlist_name, test_mode=test_mode, cutoff=cutoff, many_mode=many_mode)
        
            if error_info:
                error_summary[playlist_name] = error_info

    # Error summary      
    print("\n")
    print("-" * 60)
    print("\n")
    print("FINAL SUMMARY: \n")
    if not error_summary:
        print("All playlists processed successfully!")
    else:
        print("Errors occurred in the following playlists:")
        for name, tb in error_summary.items():
            print(f"\n--- {name} ---")
            exc_name = type(tb).__name__  
            if exc_name == "BotDetection":
                print("BotDetection error occurred.")
            else:
                print(tb.strip().splitlines()[-1])  # print only the last traceback line (error type + msg)
            # or print(tb) for full traceback