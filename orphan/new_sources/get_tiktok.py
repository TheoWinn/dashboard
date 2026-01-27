# what is available: 
# Packages:
# uv add TikTokApi
# uv add playwright
# playwright install

# ms_token: is a TikTok session token stored in your browser; TikTokApi uses it to mimic a real logged-in browser session
# how to get it: 
# Log in to TikTok in your normal browser.
# ​Open DevTools → Application/Storage tab → Cookies for https://www.tiktok.com.
# ​Find the cookie named msToken (or similar), copy its value.
# ​Put it into an environment variable, for example in your shell:
# export ms_token='PASTE_VALUE_HERE'
# Then your Python code os.environ.get("ms_token") will see it

from TikTokApi import TikTokApi
import asyncio
import os
import json
from pathlib import Path

# 1. Setup paths and token
ms_token = os.environ.get("ms_token") 
if not ms_token:
    print("WARNING: ms_token is not set in environment variables! Script may fail.")

OUTDIR = Path("orphan/new_sources/out/tiktok")
OUTDIR.mkdir(parents=True, exist_ok=True)
HASHTAG = "politics"

# 2. Trending Videos Function
async def trending_videos():
    print("DEBUG: Starting Trending scrape...")
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
            headless=False,
        )

        i = 0
        async for video in api.trending.videos(count=3):
            i += 1
            try:
                if not video.as_dict:
                    await video.info()
                
                data = video.as_dict
                # Use safe ID access
                vid_id = data.get('id', video.id)
                
                path = OUTDIR / f"video_{i}_{vid_id}.json"
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"wrote {path}")
            except Exception as e:
                print(f"Error saving trending video {i}: {e}")
    print(f"DEBUG: Trending scrape finished. Found {i} videos.")

# 3. Get hashtag
async def scrape_hashtag():
    async with TikTokApi() as api:
        # 1. Use Chromium with stealthier settings
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=5, # Wait longer to let page load fully
            browser=os.getenv("TIKTOK_BROWSER", "chromium"), 
            headless=False,
        )

        print(f"DEBUG: Fetching trending videos (Safe Mode)...")
        
        # 2. Iterate slowly (no massive counts)
        # Use api.trending.videos() without a count argument first to let it use default
        i = 0
        saved = 0
        
        try:
            async for video in api.trending.videos(count=10): # Keep count LOW (10)
                i += 1
                try:
                    # 3. Add a small sleep between processing to mimic human speed
                    await asyncio.sleep(1) 
                    
                    if not video.as_dict:
                        await video.info()
                    
                    data = video.as_dict
                    
                    # 4. Check for hashtags
                    video_tags = []
                    if 'challenges' in data:
                        video_tags = [tag.get('title', '').lower() for tag in data['challenges']]
                    elif 'textExtra' in data: # sometimes hashtags are here
                         video_tags = [t.get('hashtagName', '').lower() for t in data['textExtra']]

                    print(f"DEBUG: Checked video {i} (Tags: {video_tags})")

                    if HASHTAG.lower() in video_tags:
                        saved += 1
                        vid_id = data.get('id', video.id)
                        path = OUTDIR / f"filtered_{HASHTAG}_{saved}_{vid_id}.json"
                        
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print(f"SUCCESS: wrote {path}")
                        
                        if saved >= 5: # Stop after 5 matches
                            break
                            
                except Exception as inner:
                    print(f"Skipped video {i}: {inner}")
                    
        except Exception as e:
            print(f"Loop Error: {e}")

        print(f"DEBUG: Finished. Checked {i} videos, saved {saved}.")



if __name__ == "__main__":
    # Uncomment the one you want to run:
    
    asyncio.run(trending_videos())
    #asyncio.run(scrape_hashtag())
