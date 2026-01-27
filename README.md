# NBA Chemistry Analyzer

Discover which player combinations work best together

Ever wonder why some NBA lineups dominate while others struggle? This app uses real game data to show you which 5-player combinations perform best together.

---

## What This App Does (Simple Explanation)

### Think of it like cooking:
- Some ingredients go great together (peanut butter + jelly)
- Some don't (toothpaste + orange juice)
- NBA players are the same - certain combinations just work

**This app answers:**
- Which 5 players should be on the court together?
- Are coaches missing hidden gem lineups?
- Which combinations dominate opponents?

---

## How to Use It

### 1. Select Your Team
Pick any NBA team from the dropdown (e.g., Los Angeles Lakers)

### 2. Choose a Season
Select which season you want to analyze (2023-24 is most recent)

### 3. Adjust Filters (Optional)
- **Minimum Minutes:** Only show lineups that played together at least X minutes
  - Higher = more reliable data
  - Lower = see more experimental lineups
- **Minimum Games:** Only show lineups that played together in X games
  - Higher = proven combinations
  - Lower = include newer lineups

### 4. Explore Three Tabs

#### Top Lineups
See the best-performing 5-player combinations
- Green rows = lineup dominates (good)
- Red rows = lineup struggles (bad)

#### Hidden Gems
Find underused lineups that actually perform well
- These are lineups coaches should try more often
- High performance but low playing time

#### Analysis
Statistical deep-dive with charts showing:
- Average performance across all lineups
- Best and worst combinations
- Does more playing time = better results?

---

## What the Numbers Mean (Beginner-Friendly)

### Net Rating (Most Important Number)
> "When this lineup is on the court, do we win or lose?"

- **Positive number** (e.g., +5.5) = Lineup outscores opponents
  - Translation: For every 100 possessions, this lineup scores 5.5 more points than opponents
- **Negative number** (e.g., -2.4) = Lineup gets outscored
  - Translation: For every 100 possessions, this lineup scores 2.4 fewer points than opponents
- **Zero** (0.0) = Even matchup

**Examples:**
- Lakers lineup with LeBron + AD: **+5.5** (Very good)
- Lakers lineup without stars: **-12.5** (Bench unit struggles)

### Offensive Rating
> "How many points does this lineup score?"

- Higher is better
- **115+** = Elite offense
- **105-115** = Average
- **<105** = Struggling offense

### Defensive Rating
> "How many points does this lineup allow?"

- Lower is better
- **<105** = Elite defense
- **105-115** = Average
- **115+** = Struggling defense

### Minutes Played
> "How much experience does this lineup have together?"

- More minutes = more reliable data
- Less minutes = small sample size (could be fluky)

---

## Real-World Example

**Lineup:** LeBron James - Anthony Davis - Austin Reaves - Rui Hachimura - D'Angelo Russell

**Stats:**
- Net Rating: **+5.5**
- Minutes: **389** (played together a lot)
- Games: **45**

**What this tells us:**
- This lineup works really well together
- They've played enough to trust the data
- When these 5 are on court, Lakers dominate
- Coach should keep using this combination

---

## Hidden Gems Example

**Lineup:** Anthony Davis - Spencer Dinwiddie - Austin Reaves - Rui Hachimura - Jarred Vanderbilt

**Stats:**
- Net Rating: **+8.2**
- Minutes: **42** (not much playing time)
- Games: **12**

**What this tells us:**
- This lineup performs great when used
- But coach hasn't tried it much
- Maybe worth experimenting with more

---

## Why This Matters

### For Fans:
- Understand why your team wins/loses
- See if coach is making smart lineup decisions
- Predict which lineups will close games

### For Fantasy Players:
- Identify which players benefit from good lineup combos
- Spot players who might get more minutes
- Understand usage patterns

### For Analysts:
- Data-driven lineup optimization
- Compare coach decisions to optimal lineups
- Identify underutilized talent

---

## Where the Data Comes From

**Source:** NBA.com official statistics via their public API

**What's tracked:**
- Every second of every game
- Who's on the court
- Points scored/allowed
- Possessions played

**Updated:** Stats update after each game (usually within hours)

---

## Limitations to Keep in Mind

### 1. Small Sample Sizes
- Lineups with only 10-20 minutes might be fluky
- Use the "Minimum Minutes" filter to focus on proven lineups

### 2. Opponent Strength Not Considered
- A lineup that destroys bad teams might struggle vs elite teams
- Future version could adjust for opponent quality

### 3. Context Matters
- Garbage time stats inflate numbers
- Injuries change lineup availability
- Playoff intensity differs from regular season

### 4. Correlation Does Not Equal Causation
- Just because a lineup has good stats doesn't mean those exact 5 players are the reason
- Could be luck, opponent weakness, or other factors

---

# Technical Documentation

For developers, data scientists, and basketball analytics enthusiasts

---

## Architecture
```
Frontend: Streamlit (Python web framework)
Data Source: NBA.com Stats API (via nba-api library)
Data Processing: pandas
Visualization: Plotly
Caching: Streamlit cache_data decorator
```

---

## How Net Rating Is Calculated

### Formula:
```
NET_RATING = OFFENSIVE_RATING - DEFENSIVE_RATING
```

### Offensive Rating:
```
OFFENSIVE_RATING = (Points Scored / Possessions) × 100
```

### Defensive Rating:
```
DEFENSIVE_RATING = (Points Allowed / Possessions) × 100
```

### Possession Estimation:
```
Possessions ≈ FGA + (0.44 × FTA) - ORB + TOV
```

Where:
- `FGA` = Field Goal Attempts
- `FTA` = Free Throw Attempts
- `ORB` = Offensive Rebounds (second-chance possessions)
- `TOV` = Turnovers

**Why per 100 possessions?**
- Normalizes for pace of play
- Fair comparison between fast-break teams and slow-grind teams
- Industry standard for advanced stats

---

## Data Pipeline

### 1. API Request
```python
from nba_api.stats.endpoints import leaguedashlineups

lineups = leaguedashlineups.LeagueDashLineups(
    team_id_nullable=1610612747,  # Lakers
    season=2023,
    measure_type_detailed_defense="Advanced",
    per_mode_detailed="PerGame"
)
```

**Returns:** DataFrame with columns:
- `GROUP_NAME`: Player names in lineup
- `GP`: Games played together
- `MIN`: Total minutes together
- `W`, `L`, `W_PCT`: Win/loss record
- `NET_RATING`, `OFF_RATING`, `DEF_RATING`
- `PACE`: Possessions per 48 minutes
- Plus 40+ additional stats

### 2. Data Filtering
```python
df_filtered = df[
    (df['MIN'] >= min_minutes) &  # Reliability threshold
    (df['GP'] >= min_games)        # Sample size requirement
]
```

**Why filter?**
- Lineups with <50 minutes are unreliable (small sample)
- Single-game lineups often have extreme stats (outliers)

### 3. Hidden Gems Algorithm
```python
median_rating = df['NET_RATING'].median()
median_minutes = df['MIN'].median()

gems = df[
    (df['NET_RATING'] > median_rating) &    # Above-average performance
    (df['MIN'] < median_minutes)            # Below-average usage
].sort_values('NET_RATING', ascending=False)
```

**Logic:**
- Find 50th percentile of net rating and minutes
- Flag lineups in upper-right quadrant (good but underused)
- Sorted by performance (best first)

---

## Performance Optimizations

### Caching Strategy
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_lineup_data(team_id, season):
    # Expensive API call
    return lineups.get_data_frames()[0]
```

**Benefits:**
- First load: 3-5 seconds (API request)
- Subsequent loads: <0.01 seconds (memory cache)
- Reduces API load on NBA servers
- Better user experience

**Cache invalidation:**
- TTL (time-to-live): 1 hour
- After 3600 seconds, cache expires
- Next request fetches fresh data

### Rate Limiting Considerations
**NBA API limits (unofficial):**
- Approximately 20-30 requests per minute
- No authentication required
- Blocks excessive requests with 429 errors

**App's approach:**
- Caching reduces request frequency
- Single request per team/season combination
- Realistic usage: <10 requests per user session

---

## Data Quality and Validation

### Known Issues:

1. **Free Agent Data**
   - Players without teams may have incomplete stats
   - API returns `TEAM_ID = 0` or `null`
   - App handles gracefully with fallback logic

2. **Mid-Season Trades**
   - Lineup data spans multiple teams
   - `GROUP_NAME` might include players from different stints
   - Stats aggregate across all teams that season

3. **Garbage Time Inflation**
   - Blowout games skew bench unit stats
   - Deep bench lineups may have inflated ratings
   - Minimum minutes filter mitigates this

4. **Opponent Adjustment Missing**
   - Current version doesn't weight by opponent strength
   - Future enhancement: strength-of-schedule adjustments

### Data Validation:
```python
# Check for empty data
if df_filtered.empty:
    st.warning("No lineups meet criteria")
    st.stop()

# Verify required columns exist
required_cols = ['GROUP_NAME', 'GP', 'MIN', 'NET_RATING']
assert all(col in df.columns for col in required_cols)
```

---

## Statistical Methodology

### Why Net Rating Over Plus/Minus?

**Plus/Minus:**
```
Lakers +15 in 10 minutes with LeBron on court
```
Problem: Not normalized for possessions or pace

**Net Rating:**
```
Lakers +8.0 per 100 possessions with LeBron on court
```
Better: Accounts for tempo, fair comparison across eras

### Sample Size Reliability

**Rule of thumb:**
- `<50 minutes`: Unreliable (ignore)
- `50-100 minutes`: Suggestive (interesting but unproven)
- `100-200 minutes`: Reliable (trust the trend)
- `200+ minutes`: Very reliable (definitive sample)

**Statistical note:**
- Central Limit Theorem applies with approximately 30+ possessions
- At 100 minutes, most lineups have 80-120 possessions
- Sufficient for meaningful inference

---

## Visualization Choices

### Color Gradients
```python
.style.background_gradient(subset=['NET_RATING'], cmap='RdYlGn')
```

**Color scale:**
- Red: Negative net rating (bad)
- Yellow: Near zero (neutral)
- Green: Positive net rating (good)

**Why this colormap?**
- Intuitive (traffic light analogy)
- Colorblind-friendly (red-green but with luminance differences)
- Standard in sports analytics

### Chart Types

1. **Horizontal Bar Chart** (Top Lineups)
   - Easy to read long player names
   - Natural left-to-right reading flow
   - Color-coded by performance

2. **Scatter Plot** (Minutes vs Net Rating)
   - Shows correlation (or lack thereof)
   - Bubble size = games played (third dimension)
   - Identifies outliers

3. **Histogram** (Net Rating Distribution)
   - Shows typical range of lineups
   - Identifies exceptional performers
   - Bell curve expected (normal distribution)

---

## API Endpoints Used

### LeagueDashLineups
```python
Endpoint: stats.nba.com/stats/leaguedashlineups
Method: GET
Parameters:
  - team_id_nullable: int (0 for all teams)
  - season: int (2023 for 2023-24 season)
  - measure_type_detailed_defense: "Advanced" | "Base"
  - per_mode_detailed: "PerGame" | "Totals" | "Per100Possessions"
```

**Response time:** 2-5 seconds typical

**Data volume:**
- Approximately 150-400 lineups per team per season
- Approximately 50 columns of stats per lineup
- Approximately 200KB JSON response

---

## Dependencies
```
streamlit==1.31.0        # Web framework
nba-api==1.4.1           # NBA data wrapper
pandas==2.1.4            # Data manipulation
numpy==1.26.3            # Numerical operations
plotly==5.18.0           # Interactive charts
matplotlib==3.8.2        # Color gradients
```

**Installation:**
```bash
pip install -r requirements.txt
```

---

## Running the Application

### Local Development
```bash
# Clone repository
git clone https://github.com/your-username/nba-chemistry-analyzer.git
cd nba-chemistry-analyzer

# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run app.py
```

Application will open in your browser at `http://localhost:8501`

---

## Future Enhancements

### Planned Features:
1. **Opponent Adjustment**
   - Weight performance by opponent strength
   - Opponent defensive rating normalization

2. **Player Synergy Matrix**
   - Which 2-player combos work best?
   - Network graph visualization

3. **Historical Comparison**
   - Compare this season vs last season
   - Identify improving/declining lineups

4. **Lineup Predictor**
   - ML model to predict untested lineup performance
   - Based on individual player stats + historical combos

5. **Export Functionality**
   - Download data as CSV
   - Generate PDF reports

---

## Project Structure
```
nba-chemistry-analyzer/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── .gitignore            # Git ignore rules
```

---

## Contributing

Found a bug or have a feature request?

**GitHub:** github.com/your-username/nba-chemistry-analyzer

**Issues to tackle:**
- Add opponent-adjusted ratings
- Implement player synergy heatmap
- Add season-over-season comparison
- Improve mobile responsiveness
- Add unit tests

---

## License

MIT License - Use freely, attribution appreciated

---

## Acknowledgments

- **Data Source:** NBA.com via nba-api library
- **Inspiration:** NBA coaching staff analytics teams
- **Methodology:** Based on Dean Oliver's "Four Factors" framework

---

## Contact

Questions? Suggestions? Reach out!

**Author:** Bavanan Bramillan
**GitHub:** github.com/bobbramillan

---

**Last Updated:** January 2026