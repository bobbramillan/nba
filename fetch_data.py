import requests
import json
import os
import time
from datetime import datetime

API_KEY = os.environ.get("BALLDONTLIE_API_KEY", "")
BASE    = "https://api.balldontlie.io/v1"
SEASON  = 2025

if not API_KEY:
    print("Error: set BALLDONTLIE_API_KEY as an environment variable.")
    exit(1)

headers = {"Authorization": API_KEY}

def get(path, params=None):
    for attempt in range(5):
        r = requests.get(f"{BASE}{path}", headers=headers,
                         params=params or {}, timeout=15)
        if r.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"  rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Rate limited after 5 attempts")

def paginate(path, params=None):
    params = params or {}
    params["per_page"] = 100
    results = []
    cursor  = None
    page    = 1
    while True:
        if cursor:
            params["cursor"] = cursor
        print(f"  page {page}...")
        data    = get(path, params)
        results.extend(data["data"])
        cursor  = data.get("meta", {}).get("next_cursor")
        page   += 1
        if not cursor:
            break
        time.sleep(13)
    return results

os.makedirs("data", exist_ok=True)

print("Fetching teams...")
teams = get("/teams")["data"]
with open("data/teams.json", "w") as f:
    json.dump(teams, f)
print(f"  saved {len(teams)} teams")

time.sleep(13)

print("Fetching games...")
games = paginate("/games", {"seasons[]": SEASON})
with open("data/games.json", "w") as f:
    json.dump(games, f)
print(f"  saved {len(games)} games")

with open("data/last_updated.json", "w") as f:
    json.dump({"timestamp": datetime.utcnow().isoformat()}, f)

print("Done. Commit the data/ folder to your repo.")