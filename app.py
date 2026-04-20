import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from nba_api.stats.endpoints import (
    leaguedashteamstats,
    commonteamroster,
    leaguedashplayerstats,
    teamdashboardbygeneralsplits,
)
from nba_api.stats.static import teams
import time

SEASON    = "2025-26"
TIMEOUT   = 30
MAX_TRIES = 3

HEADERS = {
    "Host": "stats.nba.com",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

st.set_page_config(
    page_title="NBA 2025-26 Contender Tracker",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)

# ── retry wrapper ──────────────────────────────────────────────────────────────

def nba_request(fn, *args, **kwargs):
    """
    Wraps any nba_api call with retry + exponential backoff.
    Returns the DataFrame result or raises RuntimeError with a clean message.
    """
    last_err = None
    for attempt in range(MAX_TRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)   # 1s, 2s, 4s
    raise RuntimeError(
        f"stats.nba.com didn't respond after {MAX_TRIES} attempts — "
        f"likely rate-limited or temporarily down. Try again in a minute. "
        f"({type(last_err).__name__}: {last_err})"
    )

# ── data fetching ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_stats():
    time.sleep(0.6)
    return nba_request(
        lambda: leaguedashteamstats.LeagueDashTeamStats(
            season=SEASON,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced",
            per_mode_simple="PerGame",
            headers=HEADERS,
            timeout=TIMEOUT,
        ).get_data_frames()[0]
    )

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_base_stats():
    time.sleep(0.6)
    return nba_request(
        lambda: leaguedashteamstats.LeagueDashTeamStats(
            season=SEASON,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Base",
            per_mode_simple="PerGame",
            headers=HEADERS,
            timeout=TIMEOUT,
        ).get_data_frames()[0]
    )

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_player_stats():
    time.sleep(0.6)
    return nba_request(
        lambda: leaguedashplayerstats.LeagueDashPlayerStats(
            season=SEASON,
            season_type_all_star="Regular Season",
            per_mode_simple="PerGame",
            headers=HEADERS,
            timeout=TIMEOUT,
        ).get_data_frames()[0]
    )

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_roster(team_id):
    time.sleep(0.6)
    return nba_request(
        lambda: commonteamroster.CommonTeamRoster(
            team_id=team_id,
            season=SEASON,
            headers=HEADERS,
            timeout=TIMEOUT,
        ).get_data_frames()[0]
    )

# ── contender score ────────────────────────────────────────────────────────────

def compute_contender_score(df):
    d = df.copy()
    def norm(col):
        mn, mx = col.min(), col.max()
        return (col - mn) / (mx - mn) if mx != mn else col * 0
    d["_wpct_n"] = norm(d["W_PCT"])
    d["_net_n"]  = norm(d["NET_RATING"])
    d["_off_n"]  = norm(d["OFF_RATING"])
    d["CONTENDER_SCORE"] = (
        d["_wpct_n"] * 40 +
        d["_net_n"]  * 35 +
        d["_off_n"]  * 25
    ).round(1)
    d["CONTENDER_RANK"] = d["CONTENDER_SCORE"].rank(ascending=False).astype(int)
    return d.drop(columns=["_wpct_n", "_net_n", "_off_n"])

EAST = {
    "Atlanta Hawks","Boston Celtics","Brooklyn Nets","Charlotte Hornets",
    "Chicago Bulls","Cleveland Cavaliers","Detroit Pistons","Indiana Pacers",
    "Miami Heat","Milwaukee Bucks","New York Knicks","Orlando Magic",
    "Philadelphia 76ers","Toronto Raptors","Washington Wizards",
}

def assign_conference(team_name):
    return "East" if team_name in EAST else "West"

# ── main ───────────────────────────────────────────────────────────────────────

st.title("🏀 NBA 2025-26 Contender Tracker")
st.caption("Live regular season data via stats.nba.com")

with st.spinner("Loading league data..."):
    try:
        adv  = fetch_team_stats()
        adv  = compute_contender_score(adv)
        adv["CONFERENCE"] = adv["TEAM_NAME"].apply(assign_conference)
        all_players = fetch_player_stats()
    except RuntimeError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

tab1, tab2, tab3 = st.tabs(["📊 Standings", "🔍 Team Deep Dive", "🏆 Contender Rankings"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — STANDINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    conf_filter = st.radio("Conference", ["Both", "East", "West"], horizontal=True)

    view = adv if conf_filter == "Both" else adv[adv["CONFERENCE"] == conf_filter]
    view = view.sort_values("W_PCT", ascending=False).reset_index(drop=True)
    view.index += 1

    display = view[[
        "TEAM_NAME", "W", "L", "W_PCT",
        "NET_RATING", "OFF_RATING", "DEF_RATING", "CONTENDER_SCORE"
    ]].rename(columns={
        "TEAM_NAME": "Team", "W": "W", "L": "L", "W_PCT": "Win%",
        "NET_RATING": "Net Rtg", "OFF_RATING": "Off Rtg",
        "DEF_RATING": "Def Rtg", "CONTENDER_SCORE": "Score",
    })
    display["Win%"] = display["Win%"].apply(lambda x: f"{x:.3f}")

    st.dataframe(
        display.style
            .background_gradient(subset=["Net Rtg"], cmap="RdYlGn")
            .background_gradient(subset=["Score"],   cmap="Blues"),
        use_container_width=True,
        height=580,
    )

    st.subheader("Offensive vs Defensive Rating")
    fig = px.scatter(
        adv, x="OFF_RATING", y="DEF_RATING", text="TEAM_NAME",
        color="CONFERENCE",
        color_discrete_map={"East": "#1d428a", "West": "#c8102e"},
        labels={"OFF_RATING": "Offensive Rating", "DEF_RATING": "Defensive Rating"},
        height=520,
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.add_hline(y=adv["DEF_RATING"].mean(), line_dash="dash", line_color="gray", opacity=0.4)
    fig.add_vline(x=adv["OFF_RATING"].mean(), line_dash="dash", line_color="gray", opacity=0.4)
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TEAM DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    all_team_names = sorted(adv["TEAM_NAME"].tolist())
    selected_team  = st.selectbox("Select a team", all_team_names)

    team_row = adv[adv["TEAM_NAME"] == selected_team].iloc[0]
    team_id  = next(t["id"] for t in teams.get_teams() if t["full_name"] == selected_team)
    team_abbr = next(t["abbreviation"] for t in teams.get_teams() if t["full_name"] == selected_team)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Record",     f"{int(team_row['W'])}-{int(team_row['L'])}")
    c2.metric("Win%",       f"{team_row['W_PCT']:.3f}")
    c3.metric("Net Rating", f"{team_row['NET_RATING']:+.1f}")
    c4.metric("Off Rating", f"{team_row['OFF_RATING']:.1f}")
    c5.metric("Def Rating", f"{team_row['DEF_RATING']:.1f}")

    st.divider()
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Roster")
        try:
            with st.spinner("Loading roster..."):
                roster = fetch_roster(team_id)
            st.dataframe(
                roster[["PLAYER","NUM","POSITION","HEIGHT","WEIGHT","EXP"]].rename(columns={
                    "PLAYER": "Player", "NUM": "#", "POSITION": "Pos",
                    "HEIGHT": "Ht", "WEIGHT": "Wt", "EXP": "Exp"
                }),
                use_container_width=True, hide_index=True,
            )
        except RuntimeError as e:
            st.warning(f"Roster unavailable: {e}")

    with col_right:
        st.subheader("Player Stats")
        team_players = all_players[
            all_players["TEAM_ABBREVIATION"] == team_abbr
        ].sort_values("PTS", ascending=False)

        if team_players.empty:
            st.info("No player stats available yet for this season.")
        else:
            player_display = team_players[[
                "PLAYER_NAME","GP","MIN","PTS","REB","AST",
                "FG_PCT","FG3_PCT","STL","BLK","TOV","PLUS_MINUS"
            ]].rename(columns={
                "PLAYER_NAME": "Player", "GP": "G", "MIN": "Min",
                "FG_PCT": "FG%", "FG3_PCT": "3P%", "PLUS_MINUS": "+/-"
            })
            for col in ["FG%", "3P%"]:
                player_display[col] = player_display[col].apply(lambda x: f"{x:.3f}")

            st.dataframe(
                player_display.style.background_gradient(subset=["PTS", "+/-"], cmap="RdYlGn"),
                use_container_width=True, hide_index=True, height=420,
            )

            top8 = team_players.head(8)
            fig2 = px.bar(
                top8, x="PLAYER_NAME", y=["PTS","REB","AST"],
                barmode="group",
                labels={"PLAYER_NAME": "", "value": "Per Game", "variable": ""},
                color_discrete_sequence=["#1d428a","#c8102e","#85714d"],
                height=340,
            )
            fig2.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CONTENDER RANKINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.caption(
        "Contender Score = 40% Win% + 35% Net Rating + 25% Offensive Rating, "
        "each normalized 0–100 across the league."
    )

    east = adv[adv["CONFERENCE"] == "East"].sort_values("CONTENDER_SCORE", ascending=False).reset_index(drop=True)
    west = adv[adv["CONFERENCE"] == "West"].sort_values("CONTENDER_SCORE", ascending=False).reset_index(drop=True)
    east.index += 1
    west.index += 1

    def conf_table(df):
        return df[["TEAM_NAME","W","L","NET_RATING","CONTENDER_SCORE"]].rename(columns={
            "TEAM_NAME": "Team", "NET_RATING": "Net Rtg", "CONTENDER_SCORE": "Score"
        })

    col_e, col_w = st.columns(2)
    with col_e:
        st.subheader("Eastern Conference")
        st.dataframe(
            conf_table(east).style.background_gradient(subset=["Score"], cmap="Blues"),
            use_container_width=True, height=560,
        )
    with col_w:
        st.subheader("Western Conference")
        st.dataframe(
            conf_table(west).style.background_gradient(subset=["Score"], cmap="Reds"),
            use_container_width=True, height=560,
        )

    st.subheader("Top 16 — League Wide")
    top16 = adv.sort_values("CONTENDER_SCORE", ascending=False).head(16)
    fig3 = px.bar(
        top16, x="CONTENDER_SCORE", y="TEAM_NAME", orientation="h",
        color="CONFERENCE",
        color_discrete_map={"East": "#1d428a", "West": "#c8102e"},
        labels={"CONTENDER_SCORE": "Contender Score", "TEAM_NAME": ""},
        height=520,
    )
    fig3.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
st.caption("Data: stats.nba.com via nba_api (swar) · Season: 2025-26 · Refreshes every hour")
