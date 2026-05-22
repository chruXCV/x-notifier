import os
import time
import json
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GETXAPI_KEY = os.environ["GETXAPI_KEY"]
TWITTER_USERNAME = "DeItaone"
DISPLAY_NAME = "*Walter Bloomberg"
SEEN_IDS_FILE = "seen_ids.json"

def get_check_interval():
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    hour = now.hour
    minute = now.minute

    # Active window: Sunday 2pm PT through Friday 2pm PT
    if weekday == 6:  # Sunday
        return 60 if (hour > 14 or (hour == 14 and minute >= 0)) else 300
    elif weekday < 4:  # Monday through Thursday
        return 60
    elif weekday == 4:  # Friday
        return 60 if hour < 14 else 300
    else:  # Saturday
        return 300

def load_seen_ids():
    try:
        with open(SEEN_IDS_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_seen_ids(seen_ids):
    try:
        with open(SEEN_IDS_FILE, "w") as f:
            json.dump(list(seen_ids), f)
    except Exception as e:
        print(f"[ERROR] Could not save seen_ids: {e}")

def fetch_tweets():
    url = "https://api.getxapi.com/twitter/user/tweets"
    headers = {"Authorization": f"Bearer {GETXAPI_KEY}"}
    params = {"userName": TWITTER_USERNAME}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    if not response.ok:
        print(f"[ERROR] GetXAPI error: {response.status_code} - {response.text}")
        return []
    data = response.json()
    return data.get("tweets", [])

def get_latest_tweets(seen_ids):
    try:
        tweets = fetch_tweets()
        new_tweets = []
        for tweet in tweets:
            tweet_id = tweet.get("id")
            if tweet_id and tweet_id not in seen_ids:
                new_tweets.append(tweet)
                seen_ids.add(tweet_id)
        return new_tweets, seen_ids
    except Exception as e:
        print(f"[ERROR] Failed to fetch tweets: {e}")
        return [], seen_ids

def format_timestamp(tweet):
    raw = tweet.get("created_at") or tweet.get("createdAt") or tweet.get("timestamp") or ""
    if not raw:
        return "Unknown time"
    try:
        if isinstance(raw, (int, float)):
            dt = datetime.fromtimestamp(raw, tz=timezone.utc)
        else:
            try:
                dt = datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                raw = raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(raw)
        dt_pt = dt.astimezone(ZoneInfo("America/Los_Angeles"))
        tz_label = "PDT" if dt_pt.dst() else "PST"
        return dt_pt.strftime(f"%a %m/%d/%Y – %H:%M:%S {tz_label}")
    except Exception:
        return str(raw)

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
    # Load seen_ids from file so restarts don't cause duplicate messages
    seen_ids = load_seen_ids()

    # Seed seen_ids with current tweets if starting fresh
    if not seen_ids:
        try:
            tweets = fetch_tweets()
            for tweet in tweets:
                seen_ids.add(tweet.get("id"))
            save_seen_ids(seen_ids)
            print(f"Bot started. Watching @{TWITTER_USERNAME} for new posts... ({len(seen_ids)} existing tweets seeded)")
        except Exception as e:
            print(f"[WARNING] Could not seed initial tweets: {e}. Starting with empty seen list.")
    else:
        print(f"Bot started. Watching @{TWITTER_USERNAME} for new posts... ({len(seen_ids)} IDs loaded from memory)")

    while True:
        try:
            new_tweets, seen_ids = get_latest_tweets(seen_ids)
            for tweet in reversed(new_tweets):
                raw_text = tweet.get("text", "")
                text = raw_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                timestamp = format_timestamp(tweet)
                message = (
                    f"<b>{DISPLAY_NAME} (@{TWITTER_USERNAME})</b>\n\n"
                    f"{text}\n\n"
                    f"<code>{timestamp}</code>"
                )
                send_telegram(message)
                print(f"Sent: {text[:60]}...")
            if new_tweets:
                save_seen_ids(seen_ids)
        except Exception as e:
            print(f"[ERROR] Unexpected error in main loop: {e}")

        interval = get_check_interval()
        now = datetime.now(ZoneInfo("America/Los_Angeles"))
        print(f"[INFO] Next check in {interval}s ({now.strftime('%A %H:%M PT')})")
        time.sleep(interval)

if __name__ == "__main__":
    main()
