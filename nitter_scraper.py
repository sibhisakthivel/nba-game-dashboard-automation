import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import random
import time

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.fdn.fr",
    "https://nitter.poast.org",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NBA-Dashboard/1.0)"
}

TWEET_SELECTORS = [
    ".timeline-item",
    ".timeline-entry",
    "article.timeline-item",
]

def scrape_top_n_tweets(username: str, n: int, sleep_sec: float = 1.0):
    instances = NITTER_INSTANCES.copy()
    random.shuffle(instances)

    for base in instances:
        try:
            url = f"{base}/{username}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            print(f"Trying {url}")
            print(soup.title.text if soup.title else "NO TITLE")


            items = []
            for sel in TWEET_SELECTORS:
                items = soup.select(sel)
                if items:
                    break  # stop once we find tweets

            if not items:
                raise ValueError("No tweet elements found on page")

            tweets = []
            for item in items:
                if len(tweets) >= n:
                    break

                content = item.select_one(".tweet-content")
                date_el = item.select_one("a.tweet-date")

                created_at = None
                if date_el and date_el.has_attr("title"):
                    try:
                        created_at = datetime.fromtimestamp(
                            int(date_el["title"]), tz=timezone.utc
                        )
                    except Exception:
                        pass

                text = content.get_text(strip=True) if content else ""
                if not text:
                    continue  # skip empty / promoted entries

                tweets.append({
                    "username": username,
                    "text": text,
                    "created_at": created_at,
                    "source": base,
                })

            time.sleep(sleep_sec)
            return tweets

        except Exception:
            continue

    raise RuntimeError("All Nitter instances failed or returned no tweets.")
