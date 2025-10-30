from google.auth.transport.requests import Request
from google_auth_oauthlib import flow
from googleapiclient import discovery
import pickle
import os
import json

# Disable OAuthlib's HTTPS verification when running locally.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# authenticate
def create_youtube_service(path_to_token, 
                           path_to_credentials, 
                           scopes):
    creds = None
    if os.path.exists(path_to_token):
        print("loading token")
        with open(path_to_token, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("refreshing token")
            creds.refresh(Request())
        else:
            print("getting new token")
            flow = flow.InstalledAppFlow.from_client_secrets_file(
                path_to_credentials, scopes
                )
            creds = flow.run_console()
        with open(path_to_token, "wb") as token:
            pickle.dump(creds, token)

    # build youtube service
    return discovery.build("youtube", "v3", credentials=creds)

def get_channel_id(youtube,
                   channel_name):
    # get channel id for tagesschau (run once)
    request = youtube.search().list(
        q=channel_name,     
        type="channel",
        part="snippet",
        maxResults=1
    )
    response = request.execute()
    return response["items"][0]["id"]["channelId"]

def search_videos(youtube,
                  channelId,
                  publishedAfter,
                  publishedBefore,
                  q,
                  maxResults=50):

    # search for videos
    request = youtube.search().list(part="snippet",
                                    channelId=channelId,
                                    maxResults=maxResults,
                                    order="date",
                                    publishedAfter=publishedAfter,
                                    publishedBefore=publishedBefore,
                                    type="video",
                                    q=q)
    response = request.execute()

    # extract right videos and save their ids and titles into list
    search_results = []
    for item in response.get("items"):
        title = item.get("snippet").get("title")
        description = item.get("snippet").get("description")
        if (q in title) or (q in description):
            videoId = item.get("id").get("videoId")
            search_results.append([videoId, title])

    return search_results

# check if the videos were already downloaded (then they should be in meta_data) or are already in the playlist
def check_videos(youtube,
                 playlistId,
                 search_results,
                 metadata_path):
    
    video_ids_in_playlist, _ = get_videos_in_playlist(youtube,playlistId)

    if os.path.exists(metadata_path):
        meta = pd.read_csv(metadata_path, header=None)
        downloaded_urls = meta[0].tolist()
        downloaded_ids = []
        for url in downloaded_urls:
            video_id = url.split("v=")[-1]
            downloaded_ids.append(video_id)
    else:
        downloaded_ids = []

    videos_into_playlist = []
    for videoId, title in search_results:
        if (videoId not in downloaded_ids) and (videoId not in video_ids_in_playlist):
            videos_into_playlist.append([videoId, title])
    
    return videos_into_playlist


def get_videos_in_playlist(youtube,
                           playlistId):
    # get videos already in playlist
    next_page_token = None
    video_ids_in_playlist = []
    playlistitem_ids = []
    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlistId,
            maxResults=50,
            page_token=next_page_token
        )
        response = request.execute()
        for item in response.get("items"):
            video_ids_in_playlist.append(item["snippet"]["resourceId"]["videoId"])
            playlistitem_ids.append(item["id"])
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return video_ids_in_playlist, playlistitem_ids


def add_videos_to_playlist(youtube,
                           videos_into_playlist,
                           playlistId):
    # add videos to playlist
    for videoId, title in videos_into_playlist:
        print(f"Adding video {title} ({videoId}) to playlist")
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlistId,  # replace with your playlist ID
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": videoId  # replace with the video ID you want to add
                    }
                }
            }
        )
        request.execute()

def delete_from_playlist(youtube,
                         playlistId):
        
    request = youtube.playlistItems().list(
        part="id,snippet",
        playlistId=playlistId,
        maxResults=50
    )
    response = request.execute()

    for item in response["items"]:
        print(f"{item['snippet']['title']} → {item['id']}")

    delete_videos_from_playlist = ["UEw5QUdzbXpxNG80S2hBSnhmVl9tcU1HajRrR3ZqaWdoZC41MjE1MkI0OTQ2QzJGNzNG"]
    for playlistitemId in delete_videos_from_playlist:
        request = youtube.playlistItems().delete(
                id=playlistitemId
        )
        request.execute()




#############################
# Test run


# youtube = create_youtube_service(path_to_token= "../token.pkl", 
#                                  path_to_credentials = "../client_secret.json", 
#                                  scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"])

# channelId = get_channel_id(youtube = youtube, 
#                            channel_name = "tagesschau")

# videos_into_playlist = search_videos(youtube = youtube,
#                                      channelId = "UC5NOEUbkLheQcaaRldYW5GA",
#                                      publishedAfter = "2025-03-01T00:00:00Z",
#                                      publishedAfter = None,
#                                      publishedBefore = "2025-07-01T00:00:00Z",
#                                      q = "Caren Miosga",
#                                      maxResults = 50)

# # check if the videos were already downloaded (then they should be in meta_data)

# add_videos_to_playlist(youtube = youtube,
#                        videos_into_playlist = videos_into_playlist,
#                        playlistId = "PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd")


# for downloading playlist
from src.yt_utils import download_from_playlist
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
import os
import pandas as pd

# download_from_playlist(playlist_url = "https://www.youtube.com/playlist?list=PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd", 
#                        output_dir="data/raw/talkshow_audio")