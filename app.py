import streamlit as st
from nba_api.stats.endpoints import leaguedashlineups
from nba_api.stats.static import teams
import pandas as pd
import plotly.express as px

# Page config
st.set_page_config(
    page_title="🧪 NBA Chemistry Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧪 NBA Chemistry Analyzer")
st.caption("Discover which lineups work best together using real NBA data")

# Get all teams
all_teams = teams.get_teams()
team_names = {t['full_name']: t['id'] for t in all_teams}

# Sidebar
with st.sidebar:
    st.header("Settings")
    selected_team = st.selectbox("Select Team", sorted(team_names.keys()))
    
    # Season selector (just year)
    season_options = {
        "2023-24": 2023,
        "2022-23": 2022,
        "2021-22": 2021,
        "2020-21": 2020
    }
    season_display = st.selectbox("Season", list(season_options.keys()))
    season = season_options[season_display]
    
    min_minutes = st.slider("Minimum Minutes Together", 10, 200, 50)
    min_games = st.slider("Minimum Games Together", 5, 30, 10)

# Get team ID
team_id = team_names[selected_team]

# Fetch data
@st.cache_data(ttl=3600)
def get_lineup_data(team_id, season):
    lineups = leaguedashlineups.LeagueDashLineups(
        team_id_nullable=team_id,
        season=season,
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame"
    )
    return lineups.get_data_frames()[0]

with st.spinner(f"Loading lineup data for {selected_team}..."):
    df = get_lineup_data(team_id, season)

# Filter data
df_filtered = df[(df['MIN'] >= min_minutes) & (df['GP'] >= min_games)].copy()

if df_filtered.empty:
    st.warning("No lineups meet the filter criteria. Try lowering the minimums.")
    st.stop()

# Main content
tab1, tab2, tab3 = st.tabs(["📊 Top Lineups", "💎 Hidden Gems", "📈 Analysis"])

with tab1:
    st.subheader("Best Performing Lineups")
    
    top_lineups = df_filtered.nlargest(10, 'NET_RATING')
    
    # Display table
    display_cols = ['GROUP_NAME', 'GP', 'MIN', 'NET_RATING', 'OFF_RATING', 'DEF_RATING']
    st.dataframe(
        top_lineups[display_cols].style.background_gradient(subset=['NET_RATING'], cmap='RdYlGn'),
        use_container_width=True,
        height=400
    )
    
    # Bar chart
    fig = px.bar(
        top_lineups.head(10),
        x='NET_RATING',
        y='GROUP_NAME',
        orientation='h',
        title='Net Rating by Lineup',
        labels={'NET_RATING': 'Net Rating', 'GROUP_NAME': 'Lineup'},
        color='NET_RATING',
        color_continuous_scale='RdYlGn'
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=600)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Underused High-Performing Lineups")
    st.caption("Lineups with high net rating but low playing time")
    
    # Find underused gems (high net rating, low minutes)
    median_rating = df_filtered['NET_RATING'].median()
    median_minutes = df_filtered['MIN'].median()
    
    gems = df_filtered[
        (df_filtered['NET_RATING'] > median_rating) &
        (df_filtered['MIN'] < median_minutes)
    ].sort_values('NET_RATING', ascending=False)
    
    if gems.empty:
        st.info("No hidden gems found with current filters.")
    else:
        st.dataframe(
            gems[display_cols].head(10),
            use_container_width=True
        )
        
        st.markdown("**💡 Insight:**")
        st.markdown(f"Found **{len(gems)}** lineups with above-average performance (+{median_rating:.1f}) but below-average minutes (<{median_minutes:.1f} min).")

with tab3:
    st.subheader("Statistical Analysis")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Average Net Rating",
            f"{df_filtered['NET_RATING'].mean():.1f}",
            f"±{df_filtered['NET_RATING'].std():.1f} std"
        )
    
    with col2:
        best_lineup = df_filtered.loc[df_filtered['NET_RATING'].idxmax()]
        st.metric(
            "Best Lineup",
            f"+{df_filtered['NET_RATING'].max():.1f}",
            f"{best_lineup['MIN']:.0f} min played"
        )
    
    with col3:
        worst_lineup = df_filtered.loc[df_filtered['NET_RATING'].idxmin()]
        st.metric(
            "Worst Lineup",
            f"{df_filtered['NET_RATING'].min():.1f}",
            f"{worst_lineup['MIN']:.0f} min played"
        )
    
    with col4:
        st.metric(
            "Total Lineups",
            len(df_filtered),
            f"of {len(df)} total"
        )
    
    # Show best and worst lineups
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"**Best:** {best_lineup['GROUP_NAME']}")
    with col2:
        st.error(f"**Worst:** {worst_lineup['GROUP_NAME']}")
    
    # Scatter plot: Minutes vs Net Rating
    st.subheader("Minutes vs Performance")
    fig_scatter = px.scatter(
        df_filtered,
        x='MIN',
        y='NET_RATING',
        size='GP',
        hover_data=['GROUP_NAME'],
        title='Do more minutes = better performance?',
        labels={'MIN': 'Minutes Played', 'NET_RATING': 'Net Rating', 'GP': 'Games'},
        color='NET_RATING',
        color_continuous_scale='RdYlGn'
    )
    fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Distribution of net ratings
    st.subheader("Net Rating Distribution")
    fig_hist = px.histogram(
        df_filtered,
        x='NET_RATING',
        nbins=30,
        title='How are net ratings distributed?',
        labels={'NET_RATING': 'Net Rating'},
        color_discrete_sequence=['#1f77b4']
    )
    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", opacity=0.7)
    st.plotly_chart(fig_hist, use_container_width=True)

# Footer
st.markdown("---")
st.caption(f"Data from NBA.com via nba-api | Showing {len(df_filtered)} lineups for {selected_team} ({season_display})")