#uv add snscrape
import csv
import snscrape.modules.instagram as sninsta

HASHTAGS = ["politics", "germany", "merz", "politik", "bundestag"]
MAX_POSTS_PER_TAG = 200  # adjust

out_path = "instagram_hashtag_posts.csv"

fields = [
    "source_hashtag",
    "url",
    "date_utc",
    "username",
    "content",
    "likes",
    "comments",
    "is_video",
    "display_url",
    "thumbnail_url",
]

with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()

    for tag in HASHTAGS:
        scraper = sninsta.InstagramHashtagScraper(tag)  # no leading '#'
        for i, post in enumerate(scraper.get_items()):
            if i >= MAX_POSTS_PER_TAG:
                break

            w.writerow({
                "source_hashtag": tag,
                "url": post.url,
                "date_utc": post.date.isoformat() if post.date else None,
                "username": post.username,
                "content": post.content,
                "likes": post.likes,
                "comments": post.comments,
                "is_video": post.isVideo,
                "display_url": post.displayUrl,
                "thumbnail_url": post.thumbnailUrl,
            })
