import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import pickle
from datetime import datetime, timedelta
import time
import os

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_matchup_ids(date_str):
    url = f"https://www.covers.com/sports/ncaab/matchups?selectedDate={date_str}"
    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)

        matchup_ids = set()
        for link in links:
            match = re.search(r"/sport/basketball/ncaab/matchup/(\d+)", link["href"])
            if match:
                matchup_ids.add(int(match.group(1)))

        return sorted(matchup_ids)
    except Exception as e:
        print(f"Error fetching matchup IDs for {date_str}: {e}")
        return []

def get_injury_report(matchup_id):
    url = f"https://www.covers.com/sport/basketball/ncaab/matchup/{matchup_id}#injuries"
    try:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        injuries_block = soup.find("div", id="injuries")
        if not injuries_block:
            return []

        def extract_team_injuries(section_class):
            section = injuries_block.find("section", class_=section_class)
            if not section:
                return []

            team_name_tag = section.find("h2")
            team_name = team_name_tag.get_text(strip=True).replace("Injuries", "").strip() if team_name_tag else "Unknown Team"
            if team_name.endswith("'s"):
                team_name = team_name[:-2]

            table = section.find("table")
            if not table:
                return []

            rows = table.find_all("tr")[1:]  # skip header
            injuries = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) == 1 and "No injuries" in cols[0].get_text():
                    return []
                elif len(cols) == 5:
                    injuries.append({
                        "matchup_id": matchup_id,
                        "team": team_name,
                        "player": cols[0].get_text(strip=True),
                        "position": cols[1].get_text(strip=True),
                        "status": cols[2].get_text(strip=True),
                        "date": cols[3].get_text(strip=True),
                        "note": cols[4].get_text(strip=True)
                    })
            return injuries

        away_injuries = extract_team_injuries("away-team-section")
        home_injuries = extract_team_injuries("home-team-section")

        return away_injuries + home_injuries

    except Exception as e:
        print(f"Error scraping matchup {matchup_id}: {e}")
        return []

# -------------------------------
# Load existing dataset if present
# -------------------------------
filename = "ncaab_injury_dataframes_2025_2026.rds"
if os.path.exists(filename):
    with open(filename, "rb") as f:
        injury_df_dict = pickle.load(f)
else:
    injury_df_dict = {}

# -------------------------------
# Scrape only missing dates
# -------------------------------
start_date = datetime(2025, 11, 10)
end_date = datetime.today()
current = start_date

while current <= end_date:
    date_str = current.strftime("%Y-%m-%d")

    if date_str in injury_df_dict and not injury_df_dict[date_str].empty:
        print(f"Skipping {date_str}, already scraped.")
    else:
        print(f"Scraping injuries for {date_str}...")
        matchup_ids = get_matchup_ids(date_str)

        daily_records = []
        for matchup_id in matchup_ids:
            print(f"Matchup {matchup_id}")
            records = get_injury_report(matchup_id)
            daily_records.extend(records)
            time.sleep(1.5)  # polite delay

        injury_df_dict[date_str] = pd.DataFrame(daily_records)

    current += timedelta(days=1)

# -------------------------------
# Save updated dataset
# -------------------------------
with open(filename, "wb") as f:
    pickle.dump(injury_df_dict, f)

print("\n Updated injury DataFrame dictionary saved to", filename)