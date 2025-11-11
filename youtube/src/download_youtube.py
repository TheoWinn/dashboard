# download_playlist_simple.py
from yt_utils import download_from_playlist
import pytubefix.request as req

# Optional: reduce memory usage
# req.default_range_size = 128 * 1024  # 128 KB chunks

# if __name__ == "__main__":
#     playlist_url = "https://www.youtube.com/playlist?list=PLfRDp3S7rLduqUTa6oXe_Zlv7bEeD06t6"
#     bundestag = True  # or False for talkshow path

#     print("Starting download…")
#     print("Playlist:", playlist_url)
#     print("Bundestag:", bundestag)
#     print("Chunk size:", req.default_range_size, "bytes")
#     print("-" * 60)

#     try:
#         download_from_playlist(playlist_url, bundestag=bundestag)
#     except KeyboardInterrupt:
#         print("Download stopped manually")

############# So könnte es aussehen alle Playlists (Bundestag und talkshows) herunterzuladen (in Test mode) #############

dict_of_talkshow_playlists = {
    "hart_aber_fair": "https://www.youtube.com/playlist?list=PLkKDSXRppVa4b810iSTCbsR3Vw80eV2zB", # oldest from 1 year ago (Tagesschau) 
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

dict_of_talkshow_playlists = {
    "test": "https://www.youtube.com/playlist?list=PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd"
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
        except KeyboardInterrupt:
            print("Download stopped manually")
        except Exception as e:
            print(f"An error occurred: {e}")

    # Bundestag playlist
    # main(playlist_url="https://www.youtube.com/playlist?list=PLfRDp3S7rLduqUTa6oXe_Zlv7bEeD06t6", bundestag=True, test_mode=True)

    # Talkshow playlists
    for playlist_name, playlist_url in dict_of_talkshow_playlists.items():
        print(f"\nDownloading from talkshow playlist: {playlist_name}")
        main(playlist_url=playlist_url, bundestag=False, talkshow_name=playlist_name, test_mode=True)
    