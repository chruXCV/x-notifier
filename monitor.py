import os
import time
import requests
import feedparser
RSS_URL = os.environ["RSS_URL"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
CHECK_INTERVAL = 60 # secondsdef get_latest_posts(seen_ids):
feed = feedparser.parse(RSS_URL)
new_posts = []
for entry in feed.entries:
    if entry.id not in seen_ids:
    new_posts.append(entry)
seen_ids.add(entry.id)
return new_posts, seen_ids
def send_telegram(text):
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
def main():
seen_ids = set()
feed = feedparser.parse(RSS_URL)
for entry in feed.entries:
seen_ids.add(entry.id)
print("Bot started. Watching for new posts...")
while True:
new_posts, seen_ids = get_latest_posts(seen_ids)
for post in reversed(new_posts):
message = f" <b>New post:</b>\n\n{post.title}\n\n {post.link}"
send_telegram(message)
print(f"Sent: {post.title}")
time.sleep(CHECK_INTERVAL)
if __name__ == "__main__":
main()
