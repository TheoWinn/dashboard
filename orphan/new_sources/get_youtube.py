
# in bash: run uv add google-api-python-client isodate
# to get credentials: https://github.com/Sixtus24/YouTube-Data-API-v3-Documentation-Enhanced-Version-?tab=readme-ov-file
# pass key to session like this:
# in bash: export YOUTUBE_API_KEY="YOUR_API_KEY_HERE"

import argparse
import os
import json
import re
import isodate  # uv add isodate
from datetime import datetime
from googleapiclient.discovery import build # uv add google-api-python-client
from googleapiclient.errors import HttpError

# Default playlist from your previous script
DEFAULT_PLAYLIST_URL = "https://www.youtube.com/watch?v=4Y1lZQsyuSQ&list=PLIpXfMcU3wW9uMPHeo9m_ZTnxfsMPW5za"

def get_repo_root() -> str:
    """Returns the root of the repository."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def extract_playlist_id(url_or_id: str) -> str:
    """Extracts the playlist ID from a full URL or returns the ID if provided directly."""
    if "list=" in url_or_id:
        return url_or_id.split("list=")[1].split("&")[0]
    return url_or_id

def get_video_ids_from_playlist(youtube, playlist_id: str, max_videos: int = 5):
    """Fetches video IDs from a playlist."""
    video_ids = []
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=min(max_videos, 50)  # API page limit is 50
    )
    
    while request and len(video_ids) < max_videos:
        response = request.execute()
        for item in response.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
            if len(video_ids) >= max_videos:
                break
        request = youtube.playlistItems().list_next(request, response)
    
    return video_ids

def get_video_details(youtube, video_ids: list):
    """Fetches metadata (Title, Duration, Views, etc.) for a list of video IDs."""
    videos_data = {}
    
    # Process in chunks of 50 (API limit)
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(chunk)
        )
        response = request.execute()
        
        for item in response.get("items", []):
            vid_id = item["id"]
            snippet = item["snippet"]
            content = item["contentDetails"]
            stats = item["statistics"]
            
            # Convert ISO 8601 duration (e.g., PT1H2M) to seconds
            duration_iso = content.get("duration", "PT0S")
            duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
            
            videos_data[vid_id] = {
                "id": vid_id,
                "title": snippet.get("title"),
                "creator": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "description": snippet.get("description"),
                "duration_seconds": duration_seconds,
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "tags": snippet.get("tags", []),
                "comments": []  # To be filled later
            }
            
    return videos_data

def get_comments_for_video(youtube, video_id: str, max_comments: int = 20):
    """Fetches top-level comments for a specific video."""
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_comments, 100),  # 100 is max per page
            textFormat="plainText",
            order="relevance"
        )
        response = request.execute()
        
        for item in response.get("items", []):
            top_comment = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "author": top_comment.get("authorDisplayName"),
                "text": top_comment.get("textDisplay"),
                "likes": top_comment.get("likeCount"),
                "published_at": top_comment.get("publishedAt")
            })
            
    except HttpError as e:
        # Comments might be disabled or video private
        print(f"    [!] Could not fetch comments for {video_id}: {e.reason}")
    
    return comments

def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube metadata and comments via Official API.")
    parser.add_argument("--api-key", type=str, help="Google YouTube Data API Key (or set YOUTUBE_API_KEY env var)")
    parser.add_argument("--playlist-url", type=str, default=DEFAULT_PLAYLIST_URL, help="YouTube Playlist URL or ID")
    parser.add_argument("--output-dir", type=str, default="orphan/new_sources/out/youtube", help="Output directory path")
    parser.add_argument("--max-videos", type=int, default=3, help="Max videos to process")
    parser.add_argument("--max-comments", type=int, default=10, help="Max comments per video")
    parser.add_argument("--many-videos", action="store_true", help="Increase default limits (script logic)")
    
    # Legacy args to prevent breaking existing calls (unused logic)
    parser.add_argument("--audio-only", action="store_true")
    parser.add_argument("--reduce-memory", action="store_true")
    parser.add_argument("--use-oauth", action="store_true")

    args = parser.parse_args()

    # Resolve API Key
    api_key = args.api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError("API Key is required. Pass --api-key or set YOUTUBE_API_KEY environment variable.")

    # Setup Directory
    repo_root = get_repo_root()
    output_dir = os.path.abspath(os.path.join(repo_root, args.output_dir))
    os.makedirs(output_dir, exist_ok=True)

    # Initialize API
    youtube = build("youtube", "v3", developerKey=api_key)

    # 1. Get Video IDs
    playlist_id = extract_playlist_id(args.playlist_url)
    limit_videos = 20 if args.many_videos else args.max_videos
    print(f"Fetching {limit_videos} videos from playlist: {playlist_id}")
    
    video_ids = get_video_ids_from_playlist(youtube, playlist_id, limit_videos)
    if not video_ids:
        print("No videos found.")
        return

    # 2. Get Metadata
    print(f"Fetching metadata for {len(video_ids)} videos...")
    data_map = get_video_details(youtube, video_ids)

    # 3. Get Comments
    limit_comments = 50 if args.many_videos else args.max_comments
    print(f"Fetching up to {limit_comments} comments per video...")
    
    results = []
    for vid_id, data in data_map.items():
        print(f" -> Processing: {data['title'][:40]}...")
        data["comments"] = get_comments_for_video(youtube, vid_id, limit_comments)
        results.append(data)

    # 4. Save Output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"youtube_data_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Saved {len(results)} records to:\n{output_file}")

if __name__ == "__main__":
    main()
