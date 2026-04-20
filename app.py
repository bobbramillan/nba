import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="NBA Chemistry Analyzer 25-26",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 1rem; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 600; }
    div[data-testid="stMetricLabel"] { font-size: 0.75rem; color: #888; }
    div[data-testid="stMetricDelta"] { font-size: 0.85rem; }
    .section-header {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 0.12em;
        text-transform: uppercase; color: #888; margin-bottom: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# ── load from files ───────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data():
    base = os.path.dirname(__file__)
    with open(os.path.join(base, "data", "teams.json")) as f:
        teams_list = json.load(f)
    with open(os.path.join(base, "data", "games.json")) as f:
        games = json.load(f)
    try:
        with open(os.path.join(base, "data", "last_updated.json")) as f:
            last_updated = json.load(f)["timestamp"]
    except Exception:
        last_updated = "unknown"
    teams = {t["id"]: t for t in teams_list}
    return teams, games, last_updated

try:
    teams, games, last_updated = load_data()
except FileNotFoundError:
    st.error("Data files not found. Run `python fetch_data.py` locally and commit the `data/` folder to your repo.")
    st.stop()

# ── derived stats ─────────────────────────────────────────────────────────────

def build_team_stats(games, teams):
    import statistics
    rows = {}
    for t in teams.values():
        rows[t["id"]] = {
            "id": t["id"], "name": t["full_name"],
            "abbr": t["abbreviation"], "conf": t["conference"],
            "div": t["division"],
            "W": 0, "L": 0,
            "home_W": 0, "home_L": 0,
            "away_W": 0, "away_L": 0,
            "clutch_W": 0, "clutch_L": 0,
            "margins": [], "pts_scored": [], "pts_allowed": [],
        }

    for g in games:
        if g["status"] != "Final":
            continue
        ht = g["home_team"]["id"]
        vt = g["visitor_team"]["id"]
        hs = g.get("home_team_score", 0) or 0
        vs = g.get("visitor_team_score", 0) or 0
        if hs == 0 and vs == 0:
            continue

        margin   = abs(hs - vs)
        clutch   = margin <= 5
        home_win = hs > vs

        for tid, scored, allowed, is_home in [
            (ht, hs, vs, True),
            (vt, vs, hs, False),
        ]:
            if tid not in rows:
                continue
            r   = rows[tid]
            win = (is_home and home_win) or (not is_home and not home_win)
            r["W" if win else "L"] += 1
            if is_home:
                r["home_W" if win else "home_L"] += 1
            else:
                r["away_W" if win else "away_L"] += 1
            if clutch:
                r["clutch_W" if win else "clutch_L"] += 1
            r["margins"].append(hs - vs if is_home else vs - hs)
            r["pts_scored"].append(scored)
            r["pts_allowed"].append(allowed)

    df_rows = []
    for r in rows.values():
        gp = r["W"] + r["L"]
        if gp == 0:
            continue
        margins     = r["margins"]
        avg_margin  = sum(margins) / len(margins) if margins else 0
        consistency = 100 - min(statistics.stdev(margins) if len(margins) > 1 else 0, 30) * 3.33
        avg_pts     = sum(r["pts_scored"])  / len(r["pts_scored"])  if r["pts_scored"]  else 0
        avg_allowed = sum(r["pts_allowed"]) / len(r["pts_allowed"]) if r["pts_allowed"] else 0
        w_pct       = r["W"] / gp
        clutch_gp   = r["clutch_W"] + r["clutch_L"]
        clutch_pct  = r["clutch_W"] / clutch_gp if clutch_gp else 0
        home_gp     = r["home_W"] + r["home_L"]
        away_gp     = r["away_W"] + r["away_L"]
        home_pct    = r["home_W"] / home_gp if home_gp else 0
        away_pct    = r["away_W"] / away_gp if away_gp else 0
        chemistry   = round(
            (consistency / 100) * 40 +
            clutch_pct          * 35 +
            w_pct               * 25,
        1)

        df_rows.append({
            "id": r["id"], "Team": r["name"], "Abbr": r["abbr"],
            "Conf": r["conf"], "Div": r["div"],
            "W": r["W"], "L": r["L"], "GP": gp,
            "W%": round(w_pct, 3),
            "Avg Margin": round(avg_margin, 1),
            "Consistency": round(consistency, 1),
            "Pts/G": round(avg_pts, 1),
            "Allowed/G": round(avg_allowed, 1),
            "Clutch W": r["clutch_W"], "Clutch L": r["clutch_L"],
            "Clutch%": round(clutch_pct, 3),
            "Home W%": round(home_pct, 3),
            "Away W%": round(away_pct, 3),
            "Home/Away Gap": round(home_pct - away_pct, 3),
            "Chemistry": chemistry,
        })

    return pd.DataFrame(df_rows).sort_values("W%", ascending=False).reset_index(drop=True)

def team_game_log(games, team_id):
    rows = []
    for g in sorted(games, key=lambda x: x["date"]):
        if g["status"] != "Final":
            continue
        ht = g["home_team"]["id"]
        vt = g["visitor_team"]["id"]
        if team_id not in (ht, vt):
            continue
        hs = g.get("home_team_score", 0) or 0
        vs = g.get("visitor_team_score", 0) or 0
        if hs == 0 and vs == 0:
            continue
        is_home = team_id == ht
        scored  = hs if is_home else vs
        allowed = vs if is_home else hs
        win     = scored > allowed
        rows.append({
            "Date":    g["date"][:10],
            "H/A":     "Home" if is_home else "Away",
            "Opp ID":  vt if is_home else ht,
            "Pts":     scored,
            "Opp Pts": allowed,
            "Margin":  scored - allowed,
            "W/L":     "W" if win else "L",
        })
    return pd.DataFrame(rows)

def compute_streak(game_log):
    if game_log.empty:
        return "—"
    results = game_log["W/L"].tolist()[::-1]
    cur     = results[0]
    count   = 1
    for r in results[1:]:
        if r == cur:
            count += 1
        else:
            break
    return f"{'W' if cur == 'W' else 'L'}{count}"

# ── build stats ───────────────────────────────────────────────────────────────

team_df    = build_team_stats(games, teams)
id_to_name = {t["id"]: t["full_name"] for t in teams.values()}

# ── header ────────────────────────────────────────────────────────────────────

st.title("🏀 NBA Chemistry Analyzer — 2025-26")
finished = sum(1 for g in games if g["status"] == "Final")
try:
    updated_dt = datetime.fromisoformat(last_updated).strftime("%b %d, %Y")
except Exception:
    updated_dt = last_updated
st.caption(f"{finished} games · last updated {updated_dt} · data via balldontlie.io")

tab1, tab2, tab3 = st.tabs(["📊 League Overview", "🔬 Team Deep Dive", "⚔️ Head to Head"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LEAGUE OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    conf = st.radio("Conference", ["All", "East", "West"], horizontal=True)
    view = team_df if conf == "All" else team_df[team_df["Conf"] == conf]

    st.markdown('<p class="section-header">League Averages</p>', unsafe_allow_html=True)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Avg Pts/G",       f"{view['Pts/G'].mean():.1f}")
    m2.metric("Avg Allowed/G",   f"{view['Allowed/G'].mean():.1f}")
    m3.metric("Avg Margin",      f"{view['Avg Margin'].mean():+.1f}")
    m4.metric("Avg Chemistry",   f"{view['Chemistry'].mean():.1f}")
    m5.metric("Avg Clutch%",     f"{view['Clutch%'].mean():.3f}")
    m6.metric("Avg Consistency", f"{view['Consistency'].mean():.1f}")

    st.divider()

    col_left, col_right = st.columns([1.2, 1], gap="large")

    with col_left:
        st.markdown('<p class="section-header">Standings</p>', unsafe_allow_html=True)
        display = view[[
            "Team", "Conf", "W", "L", "W%", "Pts/G",
            "Allowed/G", "Avg Margin", "Clutch%", "Consistency", "Chemistry"
        ]].copy()
        display.index = range(1, len(display) + 1)
        st.dataframe(
            display.style
                .background_gradient(subset=["Chemistry"],   cmap="YlGn")
                .background_gradient(subset=["Consistency"], cmap="Blues")
                .background_gradient(subset=["Avg Margin"],  cmap="RdYlGn"),
            use_container_width=True, height=530,
        )

    with col_right:
        st.markdown('<p class="section-header">Chemistry Score by Team</p>', unsafe_allow_html=True)
        top = view.sort_values("Chemistry", ascending=True).tail(20)
        fig = px.bar(
            top, x="Chemistry", y="Team", orientation="h",
            color="Chemistry", color_continuous_scale="YlGn", height=530,
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=10),
            coloraxis_showscale=False,
            yaxis_title="", xaxis_title="Chemistry Score",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<p class="section-header">Consistency vs Clutch Performance</p>', unsafe_allow_html=True)
        fig2 = px.scatter(
            view, x="Consistency", y="Clutch%",
            text="Abbr", color="Chemistry",
            color_continuous_scale="YlGn",
            size="GP", hover_data=["Team", "W", "L"], height=380,
        )
        fig2.update_traces(textposition="top center", textfont_size=9)
        fig2.add_hline(y=view["Clutch%"].mean(), line_dash="dash", line_color="gray", opacity=0.4)
        fig2.add_vline(x=view["Consistency"].mean(), line_dash="dash", line_color="gray", opacity=0.4)
        fig2.update_layout(margin=dict(l=0, r=0, t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown('<p class="section-header">Home vs Away Win Rate</p>', unsafe_allow_html=True)
        fig3 = px.scatter(
            view, x="Home W%", y="Away W%",
            text="Abbr", color="Conf",
            color_discrete_map={"East": "#1d428a", "West": "#c8102e"},
            hover_data=["Team"], height=380,
        )
        fig3.update_traces(textposition="top center", textfont_size=9)
        fig3.add_shape(type="line", x0=0.2, y0=0.2, x1=0.9, y1=0.9,
                       line=dict(dash="dash", color="gray", width=1))
        fig3.update_layout(margin=dict(l=0, r=0, t=10, b=10))
        st.plotly_chart(fig3, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — TEAM DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    team_names = sorted(team_df["Team"].tolist())
    selected   = st.selectbox("Select a team", team_names, key="dive_team")
    row        = team_df[team_df["Team"] == selected].iloc[0]
    tid        = int(row["id"])
    gl         = team_game_log(games, tid)

    st.markdown('<p class="section-header">Season at a Glance</p>', unsafe_allow_html=True)
    a, b, c, d, e, f, g, h = st.columns(8)
    a.metric("Record",      f"{int(row['W'])}-{int(row['L'])}")
    b.metric("Win%",        f"{row['W%']:.3f}")
    c.metric("Chemistry",   f"{row['Chemistry']}")
    d.metric("Consistency", f"{row['Consistency']}")
    e.metric("Pts/G",       f"{row['Pts/G']}")
    f.metric("Allowed/G",   f"{row['Allowed/G']}")
    g.metric("Clutch%",     f"{row['Clutch%']:.3f}",
             f"{int(row['Clutch W'])}W-{int(row['Clutch L'])}L")
    h.metric("Streak",      compute_streak(gl))

    st.divider()

    if not gl.empty:
        gl["Opp"]    = gl["Opp ID"].map(lambda x: id_to_name.get(x, str(x)))
        gl["Game #"] = range(1, len(gl) + 1)

        col_log, col_charts = st.columns([1, 1.6], gap="large")

        with col_log:
            st.markdown('<p class="section-header">Game Log</p>', unsafe_allow_html=True)
            display_gl = gl[["Date","H/A","Opp","Pts","Opp Pts","Margin","W/L"]].copy()
            display_gl = display_gl.iloc[::-1].reset_index(drop=True)
            display_gl.index += 1

            def color_wl(val):
                return "color: #2ecc71; font-weight:600" if val == "W" else "color: #e74c3c; font-weight:600"

            st.dataframe(
                display_gl.style
                    .applymap(color_wl, subset=["W/L"])
                    .background_gradient(subset=["Margin"], cmap="RdYlGn"),
                use_container_width=True, height=480,
            )

        with col_charts:
            st.markdown('<p class="section-header">Point Margin Over Season</p>', unsafe_allow_html=True)
            gl["Rolling Margin"] = gl["Margin"].rolling(5, min_periods=1).mean()
            fig4 = go.Figure()
            fig4.add_bar(
                x=gl["Game #"], y=gl["Margin"],
                marker_color=["#2ecc71" if m > 0 else "#e74c3c" for m in gl["Margin"]],
                name="Margin", opacity=0.5,
            )
            fig4.add_scatter(
                x=gl["Game #"], y=gl["Rolling Margin"],
                mode="lines", name="5-game avg",
                line=dict(color="#f39c12", width=2),
            )
            fig4.add_hline(y=0, line_color="gray", line_dash="dash", opacity=0.4)
            fig4.update_layout(height=220, margin=dict(l=0,r=0,t=10,b=10),
                               legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig4, use_container_width=True)

            st.markdown('<p class="section-header">Home vs Away Win Rate</p>', unsafe_allow_html=True)
            ha_data = pd.DataFrame({
                "Location": ["Home", "Away"],
                "Win%": [row["Home W%"], row["Away W%"]],
            })
            fig5 = px.bar(
                ha_data, x="Location", y="Win%",
                color="Location",
                color_discrete_map={"Home": "#1d428a", "Away": "#c8102e"},
                height=200, text="Win%",
            )
            fig5.update_traces(texttemplate="%{text:.3f}", textposition="inside")
            fig5.update_layout(margin=dict(l=0,r=0,t=10,b=10),
                               showlegend=False, yaxis_range=[0, 1])
            st.plotly_chart(fig5, use_container_width=True)

        st.markdown('<p class="section-header">Scoring vs Allowed This Season</p>', unsafe_allow_html=True)
        gl["Pts Roll"] = gl["Pts"].rolling(5, min_periods=1).mean()
        gl["Opp Roll"] = gl["Opp Pts"].rolling(5, min_periods=1).mean()
        fig6 = go.Figure()
        fig6.add_scatter(x=gl["Game #"], y=gl["Pts Roll"],
                         name="Scored (5g avg)", line=dict(color="#2ecc71", width=2))
        fig6.add_scatter(x=gl["Game #"], y=gl["Opp Roll"],
                         name="Allowed (5g avg)", line=dict(color="#e74c3c", width=2))
        fig6.update_layout(height=200, margin=dict(l=0,r=0,t=10,b=10),
                            legend=dict(orientation="h", y=1.2))
        st.plotly_chart(fig6, use_container_width=True)

        st.divider()
        st.markdown('<p class="section-header">League Context</p>', unsafe_allow_html=True)
        r1, r2, r3, r4, r5 = st.columns(5)
        for col_name, col_widget in [
            ("Chemistry", r1), ("Consistency", r2),
            ("Pts/G", r3), ("Clutch%", r4), ("Avg Margin", r5),
        ]:
            rank = int(team_df[col_name].rank(ascending=False, method="min")[team_df["Team"] == selected].values[0])
            col_widget.metric(col_name, f"#{rank} of {len(team_df)}", f"{row[col_name]}")

        with st.expander("Full season stats"):
            st.dataframe(row.to_frame().T, use_container_width=True, hide_index=True)
    else:
        st.info("No completed games found for this team yet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HEAD TO HEAD
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        team_a = st.selectbox("Team A", team_names, index=0, key="h2h_a")
    with c2:
        team_b = st.selectbox("Team B", team_names, index=1, key="h2h_b")

    if team_a == team_b:
        st.warning("Pick two different teams.")
        st.stop()

    row_a = team_df[team_df["Team"] == team_a].iloc[0]
    row_b = team_df[team_df["Team"] == team_b].iloc[0]
    id_a  = int(row_a["id"])
    id_b  = int(row_b["id"])

    h2h = [g for g in games
           if g["status"] == "Final"
           and {g["home_team"]["id"], g["visitor_team"]["id"]} == {id_a, id_b}]

    st.divider()

    st.markdown('<p class="section-header">Season Stats Comparison</p>', unsafe_allow_html=True)
    compare_metrics = ["W%", "Chemistry", "Consistency", "Pts/G",
                       "Allowed/G", "Avg Margin", "Clutch%", "Home W%", "Away W%"]

    hdr, ca, cm, cb = st.columns([0.8, 1, 0.3, 1])
    hdr.markdown("**Stat**")
    ca.markdown(f"**{row_a['Abbr']}**")
    cm.markdown("**vs**")
    cb.markdown(f"**{row_b['Abbr']}**")

    for metric in compare_metrics:
        val_a    = row_a[metric]
        val_b    = row_b[metric]
        better_a = val_a >= val_b
        h, ca2, cm2, cb2 = st.columns([0.8, 1, 0.3, 1])
        h.write(metric)
        ca2.markdown(f"{'🟢' if better_a else '🔴'} **{val_a}**" if better_a else f"🔴 {val_a}")
        cm2.write("—")
        cb2.markdown(f"{'🟢' if not better_a else '🔴'} **{val_b}**" if not better_a else f"🔴 {val_b}")

    st.divider()

    st.markdown('<p class="section-header">Radar Comparison</p>', unsafe_allow_html=True)
    radar_metrics = ["Chemistry", "Consistency", "Clutch%", "Home W%", "Away W%"]

    def norm_val(metric, val):
        mn = team_df[metric].min()
        mx = team_df[metric].max()
        return (val - mn) / (mx - mn) * 100 if mx != mn else 50

    vals_a  = [norm_val(m, row_a[m]) for m in radar_metrics] 
    vals_b  = [norm_val(m, row_b[m]) for m in radar_metrics]
    vals_a += [vals_a[0]]
    vals_b += [vals_b[0]]
    labels  = radar_metrics + [radar_metrics[0]]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=vals_a, theta=labels, fill="toself",
        name=row_a["Abbr"], line_color="#1d428a", opacity=0.7,
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=vals_b, theta=labels, fill="toself",
        name=row_b["Abbr"], line_color="#c8102e", opacity=0.7,
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=420, margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", y=-0.1),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()
    st.markdown('<p class="section-header">Head to Head This Season</p>', unsafe_allow_html=True)

    if not h2h:
        st.info("No completed head-to-head games this season.")
    else:
        h2h_rows = []
        for g in sorted(h2h, key=lambda x: x["date"]):
            ht     = g["home_team"]["id"]
            hs     = g.get("home_team_score", 0)
            vs     = g.get("visitor_team_score", 0)
            vt     = g["visitor_team"]["id"]
            winner = id_to_name.get(ht if hs > vs else vt, "?")
            h2h_rows.append({
                "Date":   g["date"][:10],
                "Home":   id_to_name.get(ht, str(ht)),
                "Away":   id_to_name.get(vt, str(vt)),
                "Score":  f"{hs} - {vs}",
                "Margin": abs(hs - vs),
                "Winner": winner,
            })
        h2h_df = pd.DataFrame(h2h_rows)
        wins_a = sum(1 for r in h2h_rows if r["Winner"] == team_a)
        wins_b = sum(1 for r in h2h_rows if r["Winner"] == team_b)

        hc1, hc2, hc3 = st.columns(3)
        hc1.metric(f"{row_a['Abbr']} wins", wins_a)
        hc2.metric("Games played", len(h2h_rows))
        hc3.metric(f"{row_b['Abbr']} wins", wins_b)
        st.dataframe(h2h_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Data via balldontlie.io · Season 2025-26 · Chemistry = consistency + clutch + win rate")
