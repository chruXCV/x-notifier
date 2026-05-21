import os
import time
import requests
import feedparser

RSS_URL = os.environ["RSS_URL"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
CHECK_INTERVAL = 60  # seconds

def get_latest_posts(seen_ids):
    try:
        feed = feedparser.parse(RSS_URL)
        new_posts = []
        for entry in feed.entries:
            if entry.id not in seen_ids:
                new_posts.append(entry)
                seen_ids.add(entry.id)
        return new_posts, seen_ids
    except Exception as e:
        print(f"[ERROR] Failed to fetch/parse RSS feed: {e}")
        return [], seen_ids

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
        if not response.ok:
            print(f"[ERROR] Telegram API error: {response.status_code} - {response.text}")
        else:
            print("[OK] Message sent successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")

def main():
    seen_ids = set()

    # Seed seen_ids with current posts so we only alert on NEW ones
    try:
        feed = feedparser.parse(RSS_URL)
        for entry in feed.entries:
            seen_ids.add(entry.id)
        print(f"Bot started. Watching for new posts... ({len(seen_ids)} existing posts seeded)")
    except Exception as e:
        print(f"[WARNING] Could not seed initial posts: {e}. Starting with empty seen list.")

    while True:
        try:
            new_posts, seen_ids = get_latest_posts(seen_ids)
            for post in reversed(new_posts):
                message = f"<b>New post:</b>\n\n{post.title}\n\n{post.link}"
                send_telegram(message)
                print(f"Sent: {post.title}")
        except Exception as e:
            print(f"[ERROR] Unexpected error in main loop: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
