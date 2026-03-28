import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
# --- 1. Settings --- 
from config import (
    TOURNAMENT_NAME,
    RESULTS_TEAMS_TAB,
    RESULTS_SCORES_TAB,
    RANKING_DATA,
    DRAFT_OPEN
)

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title=TOURNAMENT_NAME, page_icon="🏆", layout="wide")

# --- 3. CONNECTION & DATA LOADING ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=3600)
def load_player_data():
    try:
        df = pd.read_csv(RANKING_DATA)
        df.columns = df.columns.str.strip().str.lower()
        if 'division' in df.columns:
            df['division'] = df['division'].astype(str).str.strip().str.lower()
        if 'team' in df.columns:
            df['team'] = df['team'].astype(str).str.strip()
        return df.sort_values(by='price', ascending=False)
    except Exception as e:
        st.error(f"Error loading player data: {e}")
        return pd.DataFrame()

# @st.cache_data(ttl=3600)
def fetch_raw_sheets(_conn):
    drafts = _conn.read(worksheet=RESULTS_TEAMS_TAB, ttl=0)
    scores = _conn.read(worksheet=RESULTS_SCORES_TAB, ttl=0)
    return drafts, scores

df_players = load_player_data()

# --- 4. LEADERBOARD LOGIC ---
def get_processed_results(conn):
    try:
        drafts_raw, scores_raw = fetch_raw_sheets(conn)
        if drafts_raw.empty or scores_raw.empty: return pd.DataFrame(), pd.DataFrame()

        drafts = drafts_raw.copy()
        scores_df = scores_raw.copy()
        drafts['Manager_Name'] = drafts['Manager_Name'].str.strip()
        counts = drafts['Manager_Name'].value_counts()

        def generate_team_label(row):
            mgr = row['Manager_Name']
            if counts[mgr] > 1:
                mgr_group = drafts[drafts['Manager_Name'] == mgr]
                team_num = list(mgr_group.index).index(row.name) + 1
                return f"{mgr} (Team {team_num})"
            return mgr

        drafts['Unique_Team_Name'] = drafts.apply(generate_team_label, axis=1)
        player_cols = [c for c in drafts.columns if c.startswith("Player_")]
        melted = drafts.melt(id_vars=["Unique_Team_Name", "Manager_Name", "Open_Captain", "Women_Captain"],
                             value_vars=player_cols, value_name="player_name")

        merged = melted.merge(scores_df[['Names', 'Total']], left_on="player_name", right_on="Names", how="left")
        merged['Total'] = pd.to_numeric(merged['Total'], errors='coerce').fillna(0)
        merged['is_cap'] = (merged['player_name'] == merged['Open_Captain']) | (merged['player_name'] == merged['Women_Captain'])
        merged['calc_pts'] = merged.apply(lambda x: x['Total'] * 2 if x['is_cap'] else x['Total'], axis=1)

        leaderboard = merged.groupby("Unique_Team_Name")["calc_pts"].sum().reset_index()
        leaderboard.columns = ["Team", "Score"]
        return leaderboard.sort_values(by="Score", ascending=False).reset_index(drop=True), merged
    except: return pd.DataFrame(), pd.DataFrame()

# --- 5. TOP UI: LEADERBOARD ---
if not DRAFT_OPEN:
    st.title("🏆 Live Tournament Results")
    board, full_data = get_processed_results(conn)
    
    if not board.empty:
        # Calculate Competition Rank (1, 2, 2, 4...)
        # This ensures if two are tied for 1st, the next is 3rd.
        board['Rank'] = board['Score'].rank(method='min', ascending=False).astype(int)
        
        # We only want to display the top 3 "slots"
        top_3_teams = board[board['Rank'] <= 3].copy()
        
        c1, c2, c3 = st.columns(3)
        cols = [c1, c2, c3]
        
        # We loop through the first 3 physical slots on your screen
        for i in range(3):
            with cols[i]:
                if i < len(top_3_teams):
                    row = top_3_teams.iloc[i]
                    rank = row['Rank']
                    score = int(row['Score'])
                    team_name = row['Team']
                    
                    # Determine the Medal/Label
                    if rank == 1:
                        label = "🥇 1st Place"
                    elif rank == 2:
                        label = "🥈 2nd Place"
                    else:
                        label = "🥉 3rd Place"
                    
                    st.metric(label, team_name, f"{score} pts")
                else:
                    # Empty slot if fewer than 3 teams exist
                    st.write("")

        with st.expander("📊 View Full Rankings", expanded=False):
            # THE REFRESH BUTTON
            if st.button("🔄 Sync Fresh Data from Google Sheets"):
                st.cache_data.clear()
                st.rerun()

            # Display rank in the table for clarity
            st.dataframe(
                board[['Rank', 'Team', 'Score']], 
                use_container_width=True, 
                hide_index=True,
                column_config={"Rank": st.column_config.NumberColumn("Rank", format="%d")}
            )
    st.divider()

# --- 6. SESSION STATE ---
if 'roster' not in st.session_state: st.session_state.roster = []
if 'submitted' not in st.session_state: st.session_state.submitted = False
if 'captain_open' not in st.session_state: st.session_state.captain_open = None
if 'captain_women' not in st.session_state: st.session_state.captain_women = None

# --- 7. CALCULATIONS ---
current_roster_df = df_players[df_players['name'].isin(st.session_state.roster)]
total_spent = current_roster_df['price'].sum()
remaining_budget = 100 - total_spent
open_roster = current_roster_df[current_roster_df['division'] == 'opens']
women_roster = current_roster_df[current_roster_df['division'] == 'womens']
count_open, count_women = len(open_roster), len(women_roster)
team_counts = current_roster_df['team'].value_counts().to_dict()

# --- 8. SIDEBAR (ONLY IF DRAFT OPEN) ---
if DRAFT_OPEN:
    with st.sidebar:
        st.header("📋 Draft Summary")
        st.metric("Budget Remaining", f"{remaining_budget}")
        st.divider()
        st.subheader("Team Usage (Max 2)")
        if team_counts:
            for team, count in team_counts.items():
                st.markdown(f":{'orange' if count >= 2 else 'gray'}[**{team}**: {count} / 2]")
        st.divider()
        st.subheader(f"Opens ({count_open}/4+)")
        for _, p in open_roster.iterrows():
            st.write(f"{'⭐ ' if p['name'] == st.session_state.captain_open else '• '}{p['name']} ({p['team']})")
        st.subheader(f"Womens ({count_women}/4+)")
        for _, p in women_roster.iterrows():
            st.write(f"{'⭐ ' if p['name'] == st.session_state.captain_women else '• '}{p['name']} ({p['team']})")
        st.divider()
        if st.button("🗑️ Reset All", use_container_width=True):
            st.session_state.roster = []; st.session_state.captain_open = None; st.session_state.captain_women = None; st.rerun()

# --- 9. MAIN INTERFACE ---
if DRAFT_OPEN:
    st.title("🏆 2026 Fantasy Regionals Draft")
    with st.expander("📖 **Draft Rules**", expanded=True):
        st.markdown("""
    Welcome to the Regional Fantasy Draft! Build your squad of **9 players** with these rules:
    * 💰 **Budget:** **100 units** max.
    * ⚖️ **Gender Balance:** Min **4 players per division** (Opens and Womens).
    * 🤝 **Team Limit:** Max **2 players per team**.
    * 🌟 **Captains:** Designate **one Captain per division** for **double points**!

    **Scoring:** 1pt per Assist/Goal, 3pts per Callahan.
    """)
else:
    st.title("🛡️ Manager Portal")

if st.session_state.submitted and DRAFT_OPEN:
    st.success("🎉 Team submitted!")
    if st.button("Start New Draft"):
        st.session_state.submitted = False; st.session_state.roster = []; st.rerun()
    st.stop()

manager_name = st.text_input("Manager Name:", key="mgr_name_persistent", placeholder="Type your name...").strip()

if not manager_name and not st.session_state.roster and DRAFT_OPEN:
    st.info("👋 Enter your name to begin drafting.")
    st.stop()

# Live Results View (Team Lookup)
if not DRAFT_OPEN:
    if manager_name:
        st.subheader(f"📋 Rosters for {manager_name}")
        board, full_data = get_processed_results(conn)
        my_teams = full_data[full_data['Manager_Name'].str.lower() == manager_name.lower()]
        if not my_teams.empty:
            for team_label in my_teams['Unique_Team_Name'].unique():
                with st.expander(f"🔍 Details for {team_label}"):
                    this_t = my_teams[my_teams['Unique_Team_Name'] == team_label]
                    st.dataframe(this_t[['player_name', 'is_cap', 'Total', 'calc_pts']].rename(columns={'player_name': 'Player', 'is_cap': 'Captain?', 'Total': 'Base Pts', 'calc_pts': 'Your Pts'}), hide_index=True)
                    st.metric("Score", f"{int(this_t['calc_pts'].sum())} pts")
        else: st.warning("No submission found.")
    st.stop()

# --- 10. DRAFTING TABS ---
c1, c2, c3 = st.columns(3)
c1.metric("Spent", f"{total_spent}/100")
c2.metric("Opens", f"{count_open}/4+", delta="✅" if count_open >= 4 else count_open-4)
c3.metric("Womens", f"{count_women}/4+", delta="✅" if count_women >= 4 else count_women-4)

tab_open, tab_women = st.tabs(["Open Division", "Women's Division"])
divisions = {"Open": "opens", "Women": "womens"}

for label, div_filter in divisions.items():
    with (tab_open if label == "Open" else tab_women):
        disp_df = df_players[df_players['division'] == div_filter]
        st.columns([3, 1, 1.5, 1.5])[0].write("**Player (Team)**")
        for _, row in disp_df.iterrows():
            p_n, p_p, p_t = row['name'], row['price'], row['team']
            is_in = p_n in st.session_state.roster
            is_cap = (p_n == st.session_state.captain_open or p_n == st.session_state.captain_women)
            team_full = team_counts.get(p_t, 0) >= 2 and not is_in
            with st.container():
                ca, cb, cc, cd = st.columns([3, 1, 1.5, 1.5])
                ca.write(f"**{p_n}** ({p_t})")
                cb.write(f"{p_p}")
                if is_in:
                    if cc.button("Remove", key=f"r_{p_n}_{label}", type="primary"):
                        st.session_state.roster.remove(p_n)
                        if st.session_state.captain_open == p_n: st.session_state.captain_open = None
                        if st.session_state.captain_women == p_n: st.session_state.captain_women = None
                        st.rerun()
                    if is_cap: cd.markdown("🌟 **Captain**")
                    elif cd.button("Make Cap", key=f"p_{p_n}_{label}"):
                        if div_filter == 'opens': st.session_state.captain_open = p_n
                        else: st.session_state.captain_women = p_n
                        st.rerun()
                else:
                    can = (len(st.session_state.roster) < 9) and (total_spent+p_p <= 100) and not team_full
                    if cc.button("Add Player" if not team_full else f"Full", key=f"a_{p_n}_{label}", disabled=not can):
                        st.session_state.roster.append(p_n); st.rerun()
                    if cd.button("Add as Cap", key=f"ac_{p_n}_{label}", disabled=not can):
                        st.session_state.roster.append(p_n)
                        if div_filter == 'opens': st.session_state.captain_open = p_n
                        else: st.session_state.captain_women = p_n
                        st.rerun()

# --- 11. SUBMISSION ---
st.divider()
if len(st.session_state.roster) == 9:
    if not manager_name: st.error("⚠️ Enter Manager Name.")
    elif not (count_open >= 4 and count_women >= 4): st.warning("⚠️ Gender balance required.")
    elif not (st.session_state.captain_open and st.session_state.captain_women): st.warning("⚠️ Pick Captains.")
    elif total_spent > 100: st.error("⚠️ Over Budget!")
    else:
        st.success(f"✅ Ready, {manager_name}!")
        if st.button("🚀 SUBMIT FINAL TEAM", use_container_width=True):
            try:
                data = conn.read(worksheet=RESULTS_TEAMS_TAB, ttl=0)
                sorted_names = list(open_roster['name']) + list(women_roster['name'])
                new_row = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Manager_Name": manager_name, "Total_Cost": total_spent, "Open_Captain": st.session_state.captain_open, "Women_Captain": st.session_state.captain_women}
                for i in range(9): new_row[f"Player_{i+1}"] = sorted_names[i] if i < len(sorted_names) else ""
                conn.update(worksheet=RESULTS_TEAMS_TAB, data=pd.concat([data, pd.DataFrame([new_row])], ignore_index=True))
                st.session_state.submitted = True; st.rerun()
            except Exception as e: st.error(f"Error: {e}")
else: st.info(f"Progress: {len(st.session_state.roster)} / 9")