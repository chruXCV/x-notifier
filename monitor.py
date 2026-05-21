import os
import time
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
GETXAPI_KEY = os.environ["GETXAPI_KEY"]
TWITTER_USERNAME = "DeItaone"
CHECK_INTERVAL = 60  # seconds

def get_latest_tweets(seen_ids):
    try:
        url = "https://api.getxapi.com/v1/tweets/user"
        headers = {"X-API-Key": GETXAPI_KEY}
        params = {"username": TWITTER_USERNAME, "limit": 20}
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if not response.ok:
            print(f"[ERROR] GetXAPI error: {response.status_code} - {response.text}")
            return [], seen_ids

        data = response.json()
        tweets = data.get("data", [])
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
        url = "https://api.getxapi.com/v1/tweets/user"
        headers = {"X-API-Key": GETXAPI_KEY}
        params = {"username": TWITTER_USERNAME, "limit": 20}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        tweets = data.get("data", [])
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
                tweet_id = tweet.get("id")
                link = f"https://x.com/{TWITTER_USERNAME}/status/{tweet_id}"
                message = f"<b>@{TWITTER_USERNAME}:</b>\n\n{text}\n\n{link}"
                send_telegram(message)
                print(f"Sent: {text[:60]}...")
        except Exception as e:
            print(f"[ERROR] Unexpected error in main loop: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
