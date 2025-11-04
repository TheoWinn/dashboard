from google.auth.transport.requests import Request
from google_auth_oauthlib import flow
from googleapiclient import discovery
import pickle
import os
import json
from datetime import datetime, timedelta, timezone


# authenticate
def create_youtube_service(path_to_token, 
                           path_to_credentials, 
                           scopes):
    
    # Disable OAuthlib's HTTPS verification when running locally.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

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
    
    # transforming date strings to datetime objects for validation
    if isinstance(publishedAfter, str):
        after_dt = datetime.fromisoformat(publishedAfter.replace("Z", "+00:00"))
    else:
        after_dt = None
    if isinstance(publishedBefore, str):
        before_dt = datetime.fromisoformat(publishedBefore.replace("Z", "+00:00"))
    else:
        before_dt = None
    
    # checking for okay timeframe of search
    if (after_dt is not None) and (before_dt is not None):
        if before_dt - after_dt > timedelta(days=366):
            raise ValueError("The date range between publishedAfter and publishedBefore must not exceed 1 year.")
    elif (after_dt is None) and (before_dt is not None):
        raise ValueError("publishedAfter must be provided if publishedBefore is provided.")
    elif (after_dt is not None) and (before_dt is None):
        now = datetime.now(timezone.utc)
        if now - after_dt > timedelta(days=366):
            raise ValueError("The date range between publishedAfter and the current date must not exceed 1 year.")
    else:
        raise ValueError("You must provide a timeframe for your search by setting either publishedAfter and publishedBefore or only publishedAfter")

    next_page_token = None
    search_results = []

    while True:
        # search for videos
        request = youtube.search().list(part="snippet",
                                        channelId=channelId,
                                        maxResults=maxResults,
                                        order="date",
                                        publishedAfter=publishedAfter,
                                        publishedBefore=publishedBefore,
                                        type="video",
                                        q=q,
                                        pageToken=next_page_token)
        response = request.execute()

        # extract right videos and save their ids and titles into list
        for item in response.get("items"):
            title = item.get("snippet").get("title")
            description = item.get("snippet").get("description")
            if (q in title) or (q in description):
                videoId = item.get("id").get("videoId")
                search_results.append([videoId, title])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return search_results

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
            pageToken=next_page_token
        )
        response = request.execute()
        for item in response.get("items"):
            video_ids_in_playlist.append(item["snippet"]["resourceId"]["videoId"])
            playlistitem_ids.append(item["id"])
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return video_ids_in_playlist, playlistitem_ids

# check if the videos were already downloaded (then they should be in meta_data) or are already in the playlist
def check_videos(search_results,
                 metadata_path,
                 video_ids_in_playlist,
                 video_playlistids = []):
    
    # video_ids_in_playlist, _ = get_videos_in_playlist(youtube,playlistId)

    if os.path.exists(metadata_path):
        meta = pd.read_csv(metadata_path, header=None)
        downloaded_urls = meta[0].tolist()
        downloaded_ids = []
        for url in downloaded_urls:
            video_id = url.split("v=")[-1]
            downloaded_ids.append(video_id)
    else:
        downloaded_ids = []

    if search_results is None:
        delete_videos_from_playlist = []
        for videoId, itemId in zip(video_ids_in_playlist, video_playlistids):
            if videoId in downloaded_ids:
                delete_videos_from_playlist.append(itemId)
        return delete_videos_from_playlist
    else:
        videos_into_playlist = []
        for videoId, title in search_results:
            if (videoId not in downloaded_ids) and (videoId not in video_ids_in_playlist):
                videos_into_playlist.append([videoId, title])
        return videos_into_playlist


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
                         playlistId,
                         delete_videos_from_playlist):
        
    for playlistitemId in delete_videos_from_playlist:
        request = youtube.playlistItems().delete(
                id=playlistitemId
        )
        request.execute()


#############################
# Test run

# for downloading playlist
from src.yt_utils import download_from_playlist
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
import os
import pandas as pd

youtube = create_youtube_service(path_to_token= "../token.pkl", 
                                 path_to_credentials = "../client_secret.json", 
                                 scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"])

# channelId = get_channel_id(youtube = youtube, 
#                            channel_name = "tagesschau")

print("searching videos")
search_results = search_videos(youtube = youtube,
                               channelId = "UC5NOEUbkLheQcaaRldYW5GA",
                               publishedAfter = "2025-01-01T00:00:00Z",
                               #  publishedAfter = None,
                               #  publishedBefore = "2025-05-01T00:00:00Z",
                               publishedBefore = None,
                               q = "Caren Miosga",
                               maxResults = 50)
print(f"output: {search_results}")

print("getting videos in playlist before adding")
video_ids_in_playlist, _ = get_videos_in_playlist(youtube = youtube,
                                                  playlistId = "PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd")
print(f"output: {video_ids_in_playlist}")

print("checking videos to add")
videos_into_playlist = check_videos(search_results = search_results,
                                    metadata_path = "data/raw/talkshow_audio/metadata.csv",
                                    video_ids_in_playlist = video_ids_in_playlist,
                                    video_playlistids = [])
print(f"output: {videos_into_playlist}")

print("adding videos to playlist")
add_videos_to_playlist(youtube = youtube,
                       videos_into_playlist = videos_into_playlist,
                       playlistId = "PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd")
print(f"done")

print("downloading from playlist")
download_from_playlist(playlist_url = "https://www.youtube.com/playlist?list=PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd",
                       output_dir="data/raw/talkshow_audio")
print("done downloading")

print("getting videos in playlist after adding")
video_ids_in_playlist, video_playlistids = get_videos_in_playlist(youtube = youtube,
                                                  playlistId = "PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd")
print(f"videoids: {video_ids_in_playlist}")
print(f"playlistitemids: {video_playlistids}")

print("checking videos to delete")
delete_videos_from_playlist = check_videos(search_results = None,
                                    metadata_path = "data/raw/talkshow_audio/metadata.csv",
                                    video_ids_in_playlist = video_ids_in_playlist,
                                    video_playlistids = video_playlistids)
print(f"output: {videos_into_playlist}")

print("deleting videos from playlist")
delete_from_playlist(youtube = youtube,
                         playlistId = "PL9AGsmzq4o4KhAJxfV_mqMGj4kGvjighd",
                         delete_videos_from_playlist = delete_videos_from_playlist)
print("done")

