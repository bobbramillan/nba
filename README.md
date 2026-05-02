# NBA Chemistry Analyzer 🏀

Discover which NBA teams have the best chemistry — and what's driving it.

**[Live Demo](https://nba-chemistry-2024.streamlit.app/)**

Ever wonder why some NBA teams dominate while others with great players still struggle? This app uses real game data to measure team chemistry across the entire league.

---

## What This App Does

### Think of it like a sports report card:
- Every NBA team gets graded on consistency, clutch performance, and overall win rate
- You can compare any two teams head-to-head
- You can dig into a single team's full season story

**This app answers:**
- Which teams have the best chemistry this season?
- How do teams perform in close games vs. blowouts?
- Which teams are stronger at home vs. away?
- How have two specific teams matched up this season?

---

## How to Use It

### 1. Pick a Tab

#### 📊 League Overview
See the full league standings with chemistry scores, consistency ratings, clutch performance, and more. Filter by East or West conference.

#### 🔬 Team Deep Dive
Select any team to see:
- Season stats at a glance (record, chemistry, consistency, scoring)
- Game-by-game margin chart with 5-game rolling average
- Home vs. away win rate breakdown
- Scoring vs. points allowed trend over the season
- Where the team ranks in the league for each stat

#### ⚔️ Head to Head
Pick two teams and compare them side by side:
- Stat comparison with winner highlighted
- Radar chart for visual comparison (chemistry, clutch, consistency, home/away)
- Every game they've played against each other this season

---

## What the Numbers Mean

### Chemistry Score (Most Important)
> "How well does this team perform as a unit?"

A composite score (0–100) made up of:
- **Consistency (40%)** — how stable their win margins are game to game
- **Clutch% (35%)** — win rate in games decided by 5 points or fewer
- **Win% (25%)** — overall winning percentage

Higher = better team chemistry.

### Consistency
> "Do they show up every night, or are they unpredictable?"

- Derived from the standard deviation of point margins
- High consistency = reliable, hard to surprise
- Low consistency = boom or bust team

### Clutch%
> "Can they win when it matters most?"

Win rate in games decided by ≤5 points. This separates teams that perform in pressure situations vs. teams that only beat bad opponents by a lot.

### Avg Margin
> "How dominant are their wins (and losses)?"

- Positive = they're winning by more than they're losing
- Negative = getting outscored on average

---

## Real Example

**Boston Celtics — League Overview**

| Stat | Value |
|------|-------|
| Record | 51-19 |
| Chemistry | 78.4 |
| Consistency | 72.1 |
| Clutch% | 0.621 |
| Pts/G | 117.3 |
| Allowed/G | 108.9 |

**What this tells us:**
- Strong chemistry score = cohesive unit
- High clutch % = they close games out
- Positive avg margin = consistently winning by more than they lose

---

## Where the Data Comes From

**Source:** [balldontlie.io](https://balldontlie.io) — a free NBA stats API

**What's tracked:**
- Every completed game this season (2025-26)
- Final scores, home/away, win/loss for every team
- Updated automatically every day via GitHub Actions

**Last updated:** shown at the top of the app

---

## Limitations

### 1. No Player-Level Data
This app tracks team performance only — not individual player stats or lineups.

### 2. Opponent Strength Not Adjusted
A team that beats bad opponents a lot can look better than they are. Future version could adjust for strength of schedule.

### 3. Small Clutch Sample Sizes
Early in the season, teams may have played very few close games, making clutch % unreliable.

### 4. Correlation vs. Causation
A high chemistry score doesn't mean those exact players are the reason — it could be coaching, schedule, luck, or other factors.

---

# Technical Documentation

---

## Architecture

```
Data Source:    balldontlie.io API
Data Pipeline:  Python (fetch_data.py) → JSON files in data/
Automation:     GitHub Actions (runs daily at 8am UTC)
Frontend:       Streamlit (Python web framework)
Data Processing: pandas
Visualization:  Plotly
Hosting:        Streamlit Community Cloud
```

---

## Chemistry Score Formula

```python
chemistry = (consistency / 100) * 40 + clutch_pct * 35 + win_pct * 25
```

### Consistency Calculation
```python
consistency = 100 - min(stdev(point_margins), 30) * 3.33
```
Capped so even the most inconsistent teams get a non-zero score.

### Clutch%
```python
clutch_pct = clutch_wins / (clutch_wins + clutch_losses)
# where clutch = games decided by ≤5 points
```

---

## Data Pipeline

### Step 1 — Fetch (fetch_data.py)
Pulls all teams and every completed game for the 2025-26 season from balldontlie.io, then saves them as JSON files in `data/`.

```python
# Teams
GET /v1/teams → data/teams.json

# Games (paginated, 100 per page)
GET /v1/games?seasons[]=2025 → data/games.json

# Timestamp
data/last_updated.json
```

Rate limiting handled with retry logic (up to 5 attempts, 13s delay between pages).

### Step 2 — Compute (app.py)
On load, the app reads the JSON files and derives all stats in memory — no database needed.

```python
# Per team, per game:
- W/L, home/away split, clutch flag (margin ≤5)
- Rolling averages, win streaks, point margins

# Chemistry score computed once per session via build_team_stats()
```

### Step 3 — Cache (Streamlit)
```python
@st.cache_data(show_spinner=False)
def load_data():
    # Reads JSON files once per session
    # Cached in memory for the rest of the session
```

---

## Automated Data Updates

GitHub Actions runs `fetch_data.py` every day at 8am UTC and commits the updated `data/` folder back to the repo. Streamlit Cloud then serves the latest data on the next load.

```yaml
# .github/workflows/update_data.yml
on:
  schedule:
    - cron: "0 8 * * *"   # daily at 8am UTC
  workflow_dispatch:        # manual trigger available
```

The workflow:
1. Checks out the repo
2. Installs Python dependencies
3. Runs `fetch_data.py` (requires `BALLDONTLIE_API_KEY` secret)
4. Commits and pushes the updated `data/` folder

---

## Project Structure

```
nba/
├── app.py                          # Main Streamlit app
├── fetch_data.py                   # Data fetch script
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── data/
│   ├── games.json                  # All games this season
│   ├── teams.json                  # All NBA teams
│   └── last_updated.json           # Timestamp of last fetch
└── .github/
    └── workflows/
        └── update_data.yml         # Daily data update CI/CD
```

---

## Running Locally

```bash
# Clone the repo
git clone https://github.com/bobbramillan/nba.git
cd nba

# Install dependencies
pip install -r requirements.txt

# Set your API key
export BALLDONTLIE_API_KEY=your_key_here

# Fetch data (first time setup)
python fetch_data.py

# Run the app
streamlit run app.py
```

App opens at `http://localhost:8501`

Get a free API key at [balldontlie.io](https://balldontlie.io).

---

## Dependencies

```
streamlit      # Web framework
pandas         # Data processing
plotly         # Interactive charts
matplotlib     # Color gradients
requests       # HTTP (fetch_data.py only)
```

Full versions in `requirements.txt`.

---

## Future Enhancements

1. **Player-level data** — track individual stats alongside team chemistry
2. **Opponent-adjusted ratings** — weight performance by strength of schedule
3. **Season-over-season comparison** — is this team improving or declining?
4. **Lineup predictor** — ML model to predict untested lineup performance
5. **Export to CSV/PDF** — download data for your own analysis

---

## Acknowledgments

- **Data:** [balldontlie.io](https://balldontlie.io)
- **Methodology:** Inspired by Dean Oliver's Four Factors framework

---

**Author:** Bavanan Bramillan · [GitHub](https://github.com/bobbramillan)  
**Last Updated:** May 2026
