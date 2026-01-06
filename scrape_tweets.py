import sys
from nitter_scraper import scrape_top_n_tweets

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise ValueError("Usage: python scrape_tweets.py <username> <num_tweets>")

    username = sys.argv[1]
    n = int(sys.argv[2])

    tweets = scrape_top_n_tweets(username, n)

    print(f"Found {len(tweets)} tweets") 

    for t in tweets:
        print("=" * 80)
        print(t["created_at"])
        print(t["text"])
