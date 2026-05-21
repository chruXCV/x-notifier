import os
import time
import requests
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GETXAPI_KEY = os.environ["GETXAPI_KEY"]
TWITTER_USERNAME = "DeItaone"
CHECK_INTERVAL = 60  # seconds

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
    # Try common timestamp field names from GetXAPI
    raw = tweet.get("created_at") or tweet.get("createdAt") or tweet.get("timestamp") or ""
    if not raw:
        return "Unknown time"
    try:
        # Handle Unix timestamp (integer)
        if isinstance(raw, (int, float)):
            dt = datetime.fromtimestamp(raw, tz=timezone.utc)
        else:
            # Handle Twitter format: "Thu May 21 17:36:07 +0000 2026"
            try:
                dt = datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                # Handle ISO string like "2026-05-21T14:30:00.000Z"
                raw = raw.replace("Z", "+00:00")
                dt = datetime.fromisoformat(raw)
        from zoneinfo import ZoneInfo
        dt_pt = dt.astimezone(ZoneInfo("America/Los_Angeles"))
        tz_label = "PDT" if dt_pt.dst() else "PST"
        return dt_pt.strftime(f"%A, %b %d, %Y – %I:%M %p {tz_label}")
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
    seen_ids = set()

    # Seed seen_ids with current tweets so we only alert on NEW ones
    try:
        tweets = fetch_tweets()
        for tweet in tweets:
            seen_ids.add(tweet.get("id"))
        print(f"Bot started. Watching @{TWITTER_USERNAME} for new posts... ({len(seen_ids)} existing tweets seeded)")
    except Exception as e:
        print(f"[WARNING] Could not seed initial tweets: {e}. Starting with empty seen list.")

    while True:
        try:
            new_tweets, seen_ids = get_latest_tweets(seen_ids)
            for tweet in reversed(new_tweets):
                text = tweet.get("text", "")
                timestamp = format_timestamp(tweet)
                message = (
                    f"<b>@{TWITTER_USERNAME}</b>\n\n"
                    f"{text}\n\n"
                    f"🕐 {timestamp}"
                )
                send_telegram(message)
                print(f"Sent: {text[:60]}...")
        except Exception as e:
            print(f"[ERROR] Unexpected error in main loop: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
