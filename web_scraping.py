# web_scraping.py -- Script to scrape NCAA basketball statistics and scores
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
import pickle
import os

# Set date range
date_start = datetime.strptime("2025-11-09", "%Y-%m-%d")
date_end = datetime.now().date().strftime("%Y-%m-%d")
dates = pd.date_range(date_start, date_end).strftime("%Y-%m-%d").tolist()

# Load existing stats data if available
def load_rds(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

try:
    df_stats_away = load_rds("Stats_Away.rds")
    df_stats_home = load_rds("Stats_Home.rds")
except:
    df_stats_away, df_stats_home = {}, {}

# After loading df_stats_home and df_stats_away
try:
    df_stats_away = load_rds("Stats_Away.rds")
    df_stats_home = load_rds("Stats_Home.rds")
except:
    df_stats_away, df_stats_home = {}, {}

# Identify keys with None values
home_none_keys = [k for k, v in df_stats_home.items() if v is None]
away_none_keys = [k for k, v in df_stats_away.items() if v is None]

print("\n--- Diagnostics ---")
print(f"Stats_Home.rds has {len(home_none_keys)} None entries")
if home_none_keys:
    print("Home None dates:", sorted(home_none_keys))

print(f"Stats_Away.rds has {len(away_none_keys)} None entries")
if away_none_keys:
    print("Away None dates:", sorted(away_none_keys))
print("-------------------\n")

# Create list of all dates
dates_stat = pd.date_range(date_start, date_end).strftime("%Y-%m-%d").tolist()

# Identify missing dates in stats data
missing_date = list(set([
    d for d in dates_stat if d not in df_stats_away.keys()
] + [
    d for d in dates_stat if d not in df_stats_home.keys()
]))

missing_date = sorted(set(missing_date + home_none_keys + away_none_keys))
print(f"Total missing dates to scrape: {len(missing_date)}")
print("Missing dates:", missing_date)


# Function to scrape table from teamrankings.com
def scrape_table(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Detect the table by ID
    table = soup.find('table', class_= 'tr-table datatable scrollable')

    # Confirm detection
    if table:
        print("Table found")
    else:
        print("Table not found")

    # Extract headers
    headers = [th.get_text(strip=True) for th in table.find_all('th')]

    # Extract rows
    rows = []
    for tr in table.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        row = [cell.get_text(strip=True) for cell in cells]
        if row:
            rows.append(row)

    # Create DataFrame
    df = pd.DataFrame(rows, columns=headers if headers else None)
    return df

# Teamrankings Stats pages to scrape
pages = [
    #Offense
    "offensive-efficiency", "three-point-pct", "two-point-pct", "free-throw-pct", "percent-of-points-from-3-pointers",
    "points-per-game", "three-pointers-made-per-game", "free-throws-made-per-game", "floor-percentage", 
    "turnovers-per-possession", "turnovers-per-game", "assists-per-game", "possessions-per-game",
    #Rebounding
    "offensive-rebounding-pct", "defensive-rebounding-pct","total-rebounds-per-game", "total-rebounding-percentage", 
    "extra-chances-per-game",
    #Defense
    "defensive-efficiency", "blocks-per-game", "steals-per-game", "block-pct", "steals-perpossession", 
    "personal-fouls-per-possession",
    #Other
    "win-pct-all-games",
    "effective-possession-ratio", "opponent-effective-possession-ratio",
    #Ratings
    "schedule-strength-by-other", "predictive-by-other", "consistency-by-other"
]

# Scrape data for missing dates
for date in missing_date:
    print(f"Scraping date: {date}")
    df_day_home = None
    df_day_away = None
    df_SOS = None
    df_rating = None

    for j, page in enumerate(pages):
        if j >= len(pages) - 3:  # Last 3 pages are ratings
            base_url = "https://www.teamrankings.com/ncaa-basketball/ranking/"
        else:
            base_url = "https://www.teamrankings.com/ncaa-basketball/stat/"
        
        url = f"{base_url}{page}?date={date}"

        try:
            df_scrape = scrape_table(url)
            df_scrape['Team'] = df_scrape['Team'].str.replace(r"\(.*\)", "", regex=True).str.strip()

            if j >= len(pages) - 3:
                df_rating = pd.DataFrame({
                    "Date": date,
                    "Team": df_scrape["Team"],
                    page: df_scrape["Rating"]
                })

                if df_day_home is None:
                    df_day_home = df_rating
                    df_day_away = df_rating
                else:
                    df_day_home = pd.merge(df_day_home, df_rating, on=["Date", "Team"], how="left")
                    df_day_away = pd.merge(df_day_away, df_rating, on=["Date", "Team"], how="left")

            else:
                df_stat_home = pd.DataFrame({
                    "Date": date,
                    "Team": df_scrape["Team"],
                    page: df_scrape["2025"],
                    f"{page}.Last3": df_scrape["Last 3"],
                    f"{page}.Last1": df_scrape["Last 1"],
                    f"{page}.Home": df_scrape["Home"]
                })

                df_stat_away = pd.DataFrame({
                    "Date": date,
                    "Team": df_scrape["Team"],
                    page: df_scrape["2025"],
                    f"{page}.Last3": df_scrape["Last 3"],
                    f"{page}.Last1": df_scrape["Last 1"],
                    f"{page}.Away": df_scrape["Away"]
                })

                if df_day_home is None:
                    df_day_home = df_stat_home
                    df_day_away = df_stat_away
                else:
                    df_day_home = pd.merge(df_day_home, df_stat_home, on=["Date", "Team"], how="left")
                    df_day_away = pd.merge(df_day_away, df_stat_away, on=["Date", "Team"], how="left")

        except Exception as e:
            print(f"Failed to scrape {url}: {e}")


    df_stats_home[date] = df_day_home
    df_stats_away[date] = df_day_away

    # Save df_stats_home and df_stats_away to RDS-like files
    with open("Stats_Home.rds", "wb") as f:
        pickle.dump(df_stats_home, f)

    with open("Stats_Away.rds", "wb") as f:
        pickle.dump(df_stats_away, f)

# Print statement to display all known scraped dates
print("All scraped dates for home_stats:", sorted(df_stats_home.keys()))
print("All scraped dates for away_stats:", sorted(df_stats_away.keys()))

#Function to scrape scores from sports-reference.com
def scrape_scores_for_date(date):
    year = date.year
    month = date.month
    day = date.day
    url = f"https://www.sports-reference.com/cbb/boxscores/index.cgi?month={month}&day={day}&year={year}"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        teams = soup.select(".teams")

        daily_scores = []

        for t in teams:
            try:
                rows = t.select("tr")
                
                # if rows[2] contains "Women's", skip it
                gender_row = rows[2]
                gender = gender_row.select_one("td").text
                
                
                womens_game = ["Women's", "Womens", "WBIT", "WNIT"]

                # if womens_game in gender, skip
                if any(g in gender for g in womens_game):
                    continue

                away_row = rows[0]
                home_row = rows[1]

                team_name_away = away_row.select_one("td a").text
                team_name_home = home_row.select_one("td a").text

                try:
                    team_score_away = int(away_row.select("td")[1].text)
                    team_score_home = int(home_row.select("td")[1].text)
                except:
                    print(f"Scores not available for {team_name_away} vs {team_name_home} on {date}")
                    team_score_away = None
                    team_score_home = None
                

                # Sometimes there's a third row (e.g., for overtime info or gender), ignore it
                
                daily_scores.append({
                    "date_game": date,
                    "date_stat": date - timedelta(days=1),
                    "team_name_home": team_name_home,
                    "team_score_home": team_score_home,
                    "team_name_away": team_name_away,
                    "team_score_away": team_score_away
                })
            except Exception as e:
                print(f"Error parsing game: {e}")
                continue

        return pd.DataFrame(daily_scores)

    except Exception as e:
        print(f"Failed to fetch page for {date}: {e}")
        return pd.DataFrame()

#Redefine date_start to offset scores by one day
#date_start = date_start + timedelta(days=1) 
#date_end = datetime.now() + timedelta(days=1)
#today = datetime.now().date()
target_dates = pd.date_range(date_start + timedelta(days=1), date_end).date.tolist()

# Load previously saved scores
try:
    with open("Scores.rds", "rb") as f:
        df_scores = pickle.load(f)
except:
    df_scores = pd.DataFrame()

# Identify missing dates from existing data
existing_dates = pd.to_datetime(df_scores['date_game']).dt.date.unique() if not df_scores.empty else []
missing_dates = [d for d in target_dates if d not in existing_dates]

# Add tomorrow to missing dates if not present
tomorrow = datetime.now().date() + timedelta(days=1)
if tomorrow not in target_dates:
    target_dates.append(tomorrow)

# Combine with target range
scrape_dates = sorted(target_dates)

# If you need strings for scraping URLs, convert later:
scrape_dates_str = [d.strftime("%Y-%m-%d") for d in scrape_dates]

# Create a scores dataframe
df_scores_new = None

for date in scrape_dates:
    print(f"Scraping scores for {date}")
    df_day = scrape_scores_for_date(date)
    if not df_day.empty:
        if df_scores_new is None:
            df_scores_new = df_day.copy()
        else:
            df_scores_new = pd.concat([df_scores_new, df_day], ignore_index=True)


# Drop NAs
df_scores_new.dropna(subset=["team_name_home", "team_name_away"], inplace=True)

# Remove duplicates (based on unique matchups)
df_scores_new.drop_duplicates(
    subset=["date_game", "team_name_home", "team_name_away"],
    keep="first", inplace=True
)

# Append to existing and save
df_scores = pd.concat([df_scores_new, df_scores], ignore_index=True)
df_scores.drop_duplicates(
    subset=["date_game", "team_name_home", "team_name_away"],
    keep="first", inplace=True
)

# Print statement for all scraped dates
print("All scraped dates for scores:", sorted(pd.to_datetime(df_scores['date_game']).dt.strftime("%Y-%m-%d").unique()))

# Save the result
with open("Scores.rds", "wb") as f:
    pickle.dump(df_scores, f)

# Write df_scores to Excel
df_scores.to_excel("df_scores.xlsx", index=False)
print("df_scores has been written to df_scores.xlsx")
