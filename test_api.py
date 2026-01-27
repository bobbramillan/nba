from nba_api.stats.endpoints import leaguedashlineups
from nba_api.stats.static import teams

# Get Lakers team ID
lakers = [t for t in teams.get_teams() if t['full_name'] == 'Los Angeles Lakers'][0]
print(f"Lakers ID: {lakers['id']}")

# Fetch lineup data (simplified parameters)
lineups = leaguedashlineups.LeagueDashLineups(
    team_id_nullable=lakers['id'],
    season=2023,
    measure_type_detailed_defense="Advanced",
    per_mode_detailed="PerGame"
)

df = lineups.get_data_frames()[0]
print(f"\nFound {len(df)} lineups")
print("\nTop 5 lineups:")
print(df[['GROUP_NAME', 'MIN', 'NET_RATING']].head())