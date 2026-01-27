# get access token via twitch api


import os
import json
from pathlib import Path
import requests
from dotenv import load_dotenv, find_dotenv
#uv add requests


OUT_DIR = Path("orphan/new_sources/out/twitch")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# .env imports
env_path = find_dotenv()
load_dotenv(env_path)
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TOKEN = os.getenv("TWITCH_ACCESS_TOKEN") 
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