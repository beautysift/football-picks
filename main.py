import requests
import json
import os
from datetime import datetime, timezone

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY")
MINIMAX_GROUP_ID = os.environ.get("MINIMAX_GROUP_ID")

def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }
    r = requests.get(url, params=params)
    return r.json()

def main():
    print("test")

if __name__ == "__main__":
    main()
