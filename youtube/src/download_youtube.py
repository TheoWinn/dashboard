# download_playlist_simple.py
from yt_utils import download_from_playlist
import pytubefix.request as req
import traceback

# Optional: reduce memory usage
req.default_range_size = 64 * 1024  # 128 KB chunks

# if __name__ == "__main__":
#     playlist_url = "https://www.youtube.com/playlist?list=PLfRDp3S7rLduqUTa6oXe_Zlv7bEeD06t6"
#     bundestag = True  # or False for talkshow path

#     print("Starting download…")
#     print("Playlist:", playlist_url)
#     print("Bundestag:", bundestag)
#     print("Chunk size:", req.default_range_size, "bytes")
#     print("-" * 60)

#     try:
#         download_from_playlist(playlist_url, bundestag=bundestag, test_mode=False, talkshow_name=None)
#     except KeyboardInterrupt:
#         print("Download stopped manually")

############# So könnte es aussehen alle Playlists (Bundestag und talkshows) herunterzuladen #############

###### vorsicht: wenn hier True dann werden max 2 videos pro playlist heruntergeladen, False lädt alles herunter ######
test_mode = True

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

    def main(playlist_url, bundestag, talkshow_name, test_mode):
        print("Starting download…")
        print("Playlist:", playlist_url)
        print("Bundestag:", bundestag)
        #print("Chunk size:", req.default_range_size, "bytes")
        print("-" * 60)

        try:
            print("in try")
            download_from_playlist(playlist_url=playlist_url, bundestag=bundestag, talkshow_name=talkshow_name, test_mode=test_mode)
            return None
        except KeyboardInterrupt:
            print("Download stopped manually")
            return "KeyboardInterrupt"
        except Exception as e:
            print("NOOOOOOOO an error occurred")
            traceback.print_exc()
            return traceback.format_exc()
        

    error_summary = {}

    # Bundestag playlist
    error_info = main(playlist_url="https://www.youtube.com/playlist?list=PLfRDp3S7rLduqUTa6oXe_Zlv7bEeD06t6", talkshow_name=None, bundestag=True, test_mode=test_mode)
    if error_info:
        error_summary["bundestag"] = error_info

    # Talkshow playlists
    for playlist_name, playlist_url in dict_of_talkshow_playlists.items():
        print(f"\nDownloading from talkshow playlist: {playlist_name}")
        error_info = main(playlist_url=playlist_url, bundestag=False, talkshow_name=playlist_name, test_mode=test_mode)
    
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
            print(tb.strip().splitlines()[-1])  # print only the last traceback line (error type + msg)
            # or print(tb) for full traceback