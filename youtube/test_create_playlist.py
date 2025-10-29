# search for talkshow videos --> then use download_from_playlist function
# youtube api
## GET https://www.googleapis.com/youtube/v3/search
# parameters:
# part=snippet (comma-separated list of one or more search resource properties)
# channelId - (constrained to max of 500 videos)
# order=date ?
# publishedBefore / publishedAfter
# q =  "boating|sailing"
# type=video

from google.auth.transport.requests import Request
from google_auth_oauthlib import flow
from googleapiclient import discovery
import pickle
import os
import json

# Disable OAuthlib's HTTPS verification when running locally.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# settings
api_service_name = "youtube"
api_version = "v3"
path_to_token = "../token.pkl"
path_to_credentials = "../client_secret.json" # create this file with credentials that are saved on cluster
scopes = ["https://www.googleapis.com/auth/youtube"]

# authenticate
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
youtube = discovery.build(api_service_name, api_version, credentials=creds)

# tagesschau search
channelId = "UC5NOEUbkLheQcaaRldYW5GA"
publishedAfter="2025-10-01T00:00:00Z"
q = "Caren Miosga"

# search for videos
request = youtube.search().list(part="snippet",
                                channelId=channelId,
                                maxResults=5,
                                order="date",
                                publishedAfter=publishedAfter,
                                type="video",
                                q=q)
response = request.execute()

# nicely print results
print(json.dumps(response, indent=2))

# extract right videos and save their ids and titles into list
videos_into_playlist = []
for item in response.get("items"):
    title = item.get("snippet").get("title")
    if q in title:
        videoId = item.get("id").get("videoId")
        videos_into_playlist.append([videoId, title])

print(videos_into_playlist)

# # get channel id for tagesschau (run once)
# request = youtube.search().list(
#     q="tagesschau",     # name of the channel
#     type="channel",
#     part="snippet",
#     maxResults=1
# )
# response = request.execute()
# channel_id = response["items"][0]["id"]["channelId"]
# print("Channel ID:", channel_id)