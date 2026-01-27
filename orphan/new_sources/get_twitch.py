# get access token 

# # in terminal: 
# curl -X POST 'https://id.twitch.tv/oauth2/token' \
# -H 'Content-Type: application/x-www-form-urlencoded' \
# -d 'client_id=h6lh0oiuluh4be4b0tj4ewx3qwlomj&client_secret=lh75vkxbdqgnfo20befnvva3fzu04h&grant_type=client_credentials'


# # # in terminal to run the script
# # :
# TWITCH_CLIENT_ID="h6lh0oiuluh4be4b0tj4ewx3qwlomj" \
# TWITCH_ACCESS_TOKEN="77gy1pvcib8mnsazbkh9zz5ls7cy31" \
# /home/aranka/semester3/lab/dashboard/.venv/bin/python orphan/new_sources/get_twitch.py

import os
import json
from pathlib import Path
import requests
#uv add requests


OUT_DIR = Path("orphan/new_sources/out/twitch")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- PASTE CREDENTIALS HERE ---
# 1. Get Client ID from dev.twitch.tv/console
CLIENT_ID = "h6lh0oiuluh4be4b0tj4ewx3qwlomj" 

# 2. Get Access Token by running the curl command supplied by website
# (curl -X POST "https://id.twitch.tv/oauth2/token" ...)
TOKEN = "77gy1pvcib8mnsazbkh9zz5ls7cy31" 
# -----------------------------------

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Client-Id": CLIENT_ID,
}

def get_user_id(login: str) -> str:
    r = requests.get(
        "https://api.twitch.tv/helix/users",
        headers=HEADERS,
        params={"login": login},
        timeout=30,
    )
    # Print error details if it fails (helps debugging auth issues)
    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text}")
        
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        raise RuntimeError(f"No user found for login={login}")
    return data[0]["id"]

def get_videos(user_id: str, first: int = 100) -> list[dict]:
    r = requests.get(
        "https://api.twitch.tv/helix/videos",
        headers=HEADERS,
        params={"user_id": user_id, "first": first},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text}")
        
    r.raise_for_status()
    return r.json().get("data", [])

if __name__ == "__main__":
    login = "HasanAbi"  # Example channel

    try:
        print(f"Fetching ID for {login}...")
        user_id = get_user_id(login)
        
        print(f"Fetching videos for user_id={user_id}...")
        videos = get_videos(user_id, first=100)

        top3 = sorted(videos, key=lambda v: v.get("view_count", 0), reverse=True)[:3]

        out_path = OUT_DIR / f"top3_videos_{login}.json"
        out_path.write_text(json.dumps(top3, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"SUCCESS: Wrote {len(top3)} videos to {out_path}")
        
    except Exception as e:
        print(f"FAILED: {e}")