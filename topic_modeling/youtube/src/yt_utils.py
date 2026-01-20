from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
import os
import pandas as pd

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
