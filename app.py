import streamlit as st
# from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from st_supabase_connection import SupabaseConnection
# --- 1. Settings --- 
from config import (
    TOURNAMENT_NAME,
    RESULTS_TEAMS_TAB,
    RESULTS_SCORES_TAB,
    DRAFT_OPEN,
    ROSTER_SIZE,
    BUDGET_LIMIT,
    MAX_GENDER_SIZE,
    MAX_TEAM_SIZE,
    CAPTAIN_MULTIPLIER,
    MIN_GENDER_SIZE,
    PIN_LENGTH
)

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title=TOURNAMENT_NAME, page_icon="🏆", layout="wide")

# --- 3. CONNECTION & DATA LOADING ---
# conn = st.connection("gsheets", type=GSheetsConnection)
conn = st.connection("supabase", type=SupabaseConnection)

@st.cache_data(ttl=3600)
def load_player_data():
    try:
        response = conn.table("players").select("*").execute()
        df = pd.DataFrame(response.data)
        df.columns = df.columns.str.strip().str.lower()
        if 'division' in df.columns:
            df['division'] = df['division'].astype(str).str.strip().str.lower()
        if 'team' in df.columns:
            df['team'] = df['team'].astype(str).str.strip()
        return df.sort_values(by='price', ascending=False)
    except Exception as e:
        st.error(f"Error loading player data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
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
        merged['calc_pts'] = merged.apply(lambda x: x['Total'] * CAPTAIN_MULTIPLIER if x['is_cap'] else x['Total'], axis=1)

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
remaining_budget = BUDGET_LIMIT - total_spent
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
        st.subheader(f"Team Usage (Max {MAX_TEAM_SIZE})")
        if team_counts:
            for team, count in team_counts.items():
                st.markdown(f":{'orange' if count >= MAX_TEAM_SIZE else 'gray'}[**{team}**: {count} / {MAX_TEAM_SIZE}]")
        st.divider()
        st.subheader(f"Opens ({count_open}/{MIN_GENDER_SIZE}+)")
        for _, p in open_roster.iterrows():
            st.write(f"{'⭐ ' if p['name'] == st.session_state.captain_open else '• '}{p['name']} ({p['team']})")
        st.subheader(f"Womens ({count_women}/{MIN_GENDER_SIZE}+)")
        for _, p in women_roster.iterrows():
            st.write(f"{'⭐ ' if p['name'] == st.session_state.captain_women else '• '}{p['name']} ({p['team']})")
        st.divider()
        if st.button("🗑️ Reset All", use_container_width=True):
            st.session_state.roster = []; st.session_state.captain_open = None; st.session_state.captain_women = None; st.rerun()

# --- 9. MAIN INTERFACE ---
if DRAFT_OPEN:
    st.title(f"🏆 {TOURNAMENT_NAME}")
    with st.expander("📖 **Draft Rules**", expanded=True):
        st.markdown(f"""
    Welcome to the Regional Fantasy Draft! Build your squad of **{ROSTER_SIZE} players** with these rules:
    * **Squad Size:** You must select {ROSTER_SIZE} players.
    * 💰 **Budget:** **{BUDGET_LIMIT} units** max.
    * ⚖️ **Gender Balance:** Min **{MIN_GENDER_SIZE} per division** (Opens and Womens).
    * 🤝 **Team Limit:** Max **{MAX_TEAM_SIZE} per club**.
    * 🌟 **Captains:** Designate **one Captain per division** for **double points**!
    """)

    # --- THE DYNAMIC GATE ---
    col_a, col_b = st.columns(2)
    with col_a:
        manager_name = st.text_input("Manager Name:", key="mgr_name_persistent", placeholder="Type your name...").strip()   

    # Determine PIN Label dynamically based on whether the name exists
    pin_label = f"{PIN_LENGTH}-digit PIN:" 
    is_new_user = True

    if manager_name:
        name_check = conn.table("managers").select("id").eq("manager_name", manager_name).execute()
        if name_check.data:
            pin_label = f"🔓 Enter your {PIN_LENGTH}-digit PIN:"
            is_new_user = False
        else:
            pin_label = f"✨ Create a {PIN_LENGTH}-digit PIN:"
            is_new_user = True

    with col_b:
        # Use the dynamic pin_label here
        manager_pin = st.text_input(pin_label, type="password", max_chars=PIN_LENGTH)

    # SUCCESS STATE HANDLING (Moves it above the .stop() gates)
    if st.session_state.submitted:
        st.success("🎉 Team submitted successfully! You can edit it anytime before the tournament starts.")
        if st.button("Start New Draft / Edit Existing Draft"):
            # This wipes the session but the name/pin inputs stay, 
            # so the "Pre-load" logic will instantly catch them and reload.
            st.session_state.submitted = False
            st.session_state.roster = []
            st.rerun()
        st.stop()

    # STOP GATE: Block progress if credentials are incomplete
    if not manager_name or len(manager_pin) < PIN_LENGTH:
        st.info(f"👋 Enter your Manager Name and a {PIN_LENGTH}-digit PIN to begin.")
        st.stop()

    # --- AUTH & PRE-LOAD LOGIC ---
    # Try to find a match for Name + PIN
    exist_check = conn.table("managers").select("id").eq("manager_name", manager_name).eq("pin", manager_pin).execute()
    
    if exist_check.data:
        # CORRECT CREDENTIALS -> Load existing team
        manager_id = exist_check.data[0]['id']
        if not st.session_state.roster:
            with st.spinner("🔄 Loading your current roster..."):
                current_roster = conn.table("rosters").select("is_captain, players(name, division)").eq("manager_id", manager_id).execute()
                if current_roster.data:
                    st.session_state.roster = []
                    for item in current_roster.data:
                        p_name = item['players']['name']
                        p_div = item['players']['division']
                        st.session_state.roster.append(p_name)
                        if item['is_captain']:
                            if p_div == 'opens': st.session_state.captain_open = p_name
                            else: st.session_state.captain_women = p_name
                    st.rerun()
    else:
        # FAILED LOGIN: Check if the name is taken or if this is just a brand new user
        name_exists_query = conn.table("managers").select("id").eq("manager_name", manager_name).execute()
        if name_exists_query.data:
            # Name is in DB, but PIN was wrong
            st.error("❌ Incorrect PIN for this Manager Name. Please try again.")
            st.stop()
        else:
            # Name is NOT in DB. This is a new user. 
            # We let them through to the drafting tabs!
            st.caption(f"✨ New Manager: **{manager_name}**. Your team will be saved when you hit submit.")

else:
    # --- 🛡️ MANAGER PORTAL (Draft Closed) ---
    st.title("🛡️ Manager Portal")
    manager_name = st.text_input("Manager Name:", key="mgr_name_persistent").strip()
    manager_pin = st.text_input(f"{PIN_LENGTH}-digit PIN:", type="password", max_chars=PIN_LENGTH)

    if manager_name and len(manager_pin) == PIN_LENGTH:
        auth_res = conn.table("managers").select("id").eq("manager_name", manager_name).eq("pin", manager_pin).execute()
        if auth_res.data:
            st.subheader(f"📋 Roster for {manager_name}")
            # Results logic goes here
        else:
            st.error("❌ Invalid Name or PIN.")
    st.stop()

# --- 10. DRAFTING TABS ---
if st.session_state.roster:
    st.caption(f"✍️ Editing team for **{manager_name}**")
c1, c2, c3 = st.columns(3)
c1.metric("Spent", f"{total_spent}/{BUDGET_LIMIT}")

max_opens = min(MAX_GENDER_SIZE, ROSTER_SIZE - count_women)
max_womens = min(MAX_GENDER_SIZE, ROSTER_SIZE - count_open)

# Updated metrics to show the n-player cap
c2.metric("Opens", f"{count_open}/{MIN_GENDER_SIZE}", 
          delta=f"{max_opens-count_open} left" if count_open < MAX_GENDER_SIZE else "MAX",
          delta_color="normal" if count_open < MAX_GENDER_SIZE else "inverse")

c3.metric("Womens", f"{count_women}/{MIN_GENDER_SIZE}", 
          delta=f"{max_womens-count_women} left" if count_women < MAX_GENDER_SIZE else "MAX",
          delta_color="normal" if count_women < MAX_GENDER_SIZE else "inverse")

tab_open, tab_women = st.tabs(["Open Division", "Women's Division"])
divisions = {"Open": "opens", "Women": "womens"}

for label, div_filter in divisions.items():
    with (tab_open if label == "Open" else tab_women):
        disp_df = df_players[df_players['division'] == div_filter]
        
        # Header Row
        st.columns([3, 1, 1.5, 1.5])[0].write("**Player (Team)**")
        
        # Gender-specific count check
        current_gender_count = count_open if div_filter == 'opens' else count_women
        gender_full = current_gender_count >= MAX_GENDER_SIZE

        for _, row in disp_df.iterrows():
            p_n, p_p, p_t = row['name'], row['price'], row['team']
            is_in = p_n in st.session_state.roster
            is_cap = (p_n == st.session_state.captain_open or p_n == st.session_state.captain_women)
            team_full = team_counts.get(p_t, 0) >= MAX_TEAM_SIZE and not is_in
            
            with st.container():
                ca, cb, cc, cd = st.columns([3, 1, 1.5, 1.5])
                ca.write(f"**{p_n}** ({p_t})")
                cb.write(f"{p_p}")
                
                if is_in:
                    # REMOVE Logic
                    if cc.button("Remove", key=f"r_{p_n}_{label}", type="primary"):
                        st.session_state.roster.remove(p_n)
                        # Clean up captains if removed
                        if st.session_state.captain_open == p_n: st.session_state.captain_open = None
                        if st.session_state.captain_women == p_n: st.session_state.captain_women = None
                        st.rerun()
                    
                    # CAPTAIN Logic
                    if is_cap: 
                        cd.markdown("🌟 **Captain**")
                    elif cd.button("Make Cap", key=f"p_{p_n}_{label}"):
                        if div_filter == 'opens': st.session_state.captain_open = p_n
                        else: st.session_state.captain_women = p_n
                        st.rerun()
                else:
                    # ADD Logic with Gender Cap (Max n)
                    can_add = (
                        len(st.session_state.roster) < ROSTER_SIZE and 
                        (total_spent + p_p <= BUDGET_LIMIT) and 
                        not team_full and 
                        not gender_full
                    )
                    
                    # Button Labels for better UX
                    add_label = "Add Player"
                    if team_full: add_label = "Club Max"
                    elif gender_full: add_label = "Gender Max"
                    elif total_spent + p_p > BUDGET_LIMIT: add_label = "Too Expensive"
                    
                    if cc.button(add_label, key=f"a_{p_n}_{label}", disabled=not can_add):
                        st.session_state.roster.append(p_n)
                        st.rerun()
                        
                    if cd.button("Add + Cap", key=f"ac_{p_n}_{label}", disabled=not can_add):
                        st.session_state.roster.append(p_n)
                        if div_filter == 'opens': st.session_state.captain_open = p_n
                        else: st.session_state.captain_women = p_n
                        st.rerun()

# --- 11. SUBMISSION & VALIDATION ---
st.divider()

# 1. Check current status
roster_count = len(st.session_state.roster)
is_complete = roster_count == ROSTER_SIZE
has_captains = st.session_state.captain_open and st.session_state.captain_women

if is_complete:
    # 2. Final Logic Checks
    if not manager_name or len(manager_pin) < PIN_LENGTH:
        st.error(f"⚠️ Please enter your Manager Name and a {PIN_LENGTH}-digit PIN.")
    elif not (count_open >= MIN_GENDER_SIZE and count_women >= MIN_GENDER_SIZE):
        st.warning(f"⚠️ Gender balance required: {MIN_GENDER_SIZE} Opens (You: {count_open}) and {MIN_GENDER_SIZE} Womens (You: {count_women}).")
    elif not has_captains:
        st.warning("⚠️ Please designate a Captain for both divisions (🌟).")
    elif total_spent > BUDGET_LIMIT:
        st.error(f"⚠️ Over budget! You spent {total_spent} / {BUDGET_LIMIT}.")
    else:
        st.success(f"✅ Your team of {ROSTER_SIZE} is valid, {manager_name}!")
        
        # 3. The Actual Database Action
        if st.button("🚀 SUBMIT / UPDATE FINAL TEAM", use_container_width=True):
            try:
                # STEP A: Check if manager exists with this PIN
                m_check = conn.table("managers").select("id").eq("manager_name", manager_name).eq("pin", manager_pin).execute()
                
                if m_check.data:
                    # EXISTING MANAGER: Use their ID and wipe their old roster
                    m_id = m_check.data[0]['id']
                    conn.table("rosters").delete().eq("manager_id", m_id).execute()
                else:
                    # NEW MANAGER: Create them and get the ID
                    m_insert = conn.table("managers").insert({"manager_name": manager_name, "pin": manager_pin}).execute()
                    m_id = m_insert.data[0]['id']

                # STEP B: Prepare the n new roster rows
                new_entries = []
                for p_name in st.session_state.roster:
                    p_info = df_players[df_players['name'] == p_name].iloc[0]
                    new_entries.append({
                        "manager_id": m_id,
                        "player_id": p_info['id'],
                        "division": p_info['division'],
                        "is_captain": (p_name == st.session_state.captain_open or p_name == st.session_state.captain_women)
                    })

                # STEP C: Push to Supabase
                conn.table("rosters").insert(new_entries).execute()
                
                st.session_state.submitted = True
                st.balloons()
                st.rerun()

            except Exception as e:
                st.error(f"❌ Database Error: {e}")

else:
    # 4. Progress Feedback (Hides the button if they don't have n players)
    st.info(f"📋 Progress: {roster_count} / {ROSTER_SIZE} players selected. Add {ROSTER_SIZE - roster_count} more to submit.")
    st.button("🚀 SUBMIT FINAL TEAM", disabled=True, use_container_width=True, help=f"Select {ROSTER_SIZE} players first!")