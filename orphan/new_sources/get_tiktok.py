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

ms_token = os.environ.get("ms_token")  # make sure this is set. see above
OUTDIR = Path("orphan/new_sources/out/tiktok")
OUTDIR.mkdir(parents=True, exist_ok=True)
HASHTAG = "politics"

# get trending vids
async def trending_videos():
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "chromium"),
        )

        i = 0
        async for video in api.trending.videos(count=3):
            i += 1
            data = video.as_dict
            path = OUTDIR / f"video_{i}_{data['id']}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("wrote", path)

# get vids with hashtag = politics
async def scrape_hashtag():
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[ms_token],
            num_sessions=1,
            sleep_after=3,
            browser=os.getenv("TIKTOK_BROWSER", "webkit"),
            headless=False,
        )

        hashtag = api.hashtag(name=HASHTAG)

        i = 0
        async for video in hashtag.videos(count=5):
            i += 1
            data = video.as_dict
            path = OUTDIR / f"hashtag_{HASHTAG}_{i}_{data['id']}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print("wrote", path)


if __name__ == "__main__":
    #asyncio.run(trending_videos())
    asyncio.run(scrape_hashtag())
