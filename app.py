import streamlit as st
import textwrap
import pandas as pd
import pytz
import time
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# --- 1. SETTINGS & CONFIG --- 
from config import (
    DIV_OPEN_LABEL,
    DIV_WOMEN_LABEL,
    MAX_CAPTAIN_CHANGES,
    MAX_PLAYER_TRANSFERS,
    TOURNAMENT_NAME,
    ROSTER_SIZE,
    BUDGET_LIMIT,
    MAX_GENDER_SIZE,
    MAX_TEAM_SIZE,
    CAPTAIN_MULTIPLIER,
    MIN_GENDER_SIZE,
    PIN_LENGTH,
    TABLE_MANAGERS,
    TABLE_PLAYERS,
    TABLE_ROSTERS,
    TABLE_SCORES,
    SCHEMA,
    get_current_stage
)

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title=TOURNAMENT_NAME, page_icon="🏆", layout="wide")

# --- 3. CONNECTION & DATA LOADING ---
conn = st.connection("supabase", type=SupabaseConnection)

@st.cache_data(ttl=300)
def load_player_data():
    try:
        response = (conn.client
                    .schema(SCHEMA)
                    .table(TABLE_PLAYERS)
                    .select("*")
                    .not_.is_("price", "null")
                    .gt("price", 0)
                    .execute())
        df = pd.DataFrame(response.data)
        df.columns = df.columns.str.strip().str.lower()
        df['name'] = df['name'].str.strip()
        if 'division' in df.columns:
            df['division'] = df['division'].astype(str).str.strip().str.lower()
        if 'team' in df.columns:
            df['team'] = df['team'].astype(str).str.strip()
        return df.sort_values(by='price', ascending=False)
    except Exception as e:
        st.error(f"Error loading player data: {e}")
        return pd.DataFrame()

# --- 4. SESSION STATE INITIALIZATION ---
if 'roster' not in st.session_state: st.session_state.roster = []
if 'submitted' not in st.session_state: st.session_state.submitted = False
if 'captain_open' not in st.session_state: st.session_state.captain_open = None
if 'captain_women' not in st.session_state: st.session_state.captain_women = None
if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
if 'db_names' not in st.session_state: st.session_state.db_names = set()
if 'db_caps' not in st.session_state: st.session_state.db_caps = set()
if 'update_success' not in st.session_state: st.session_state.update_success = False
if 'manager_id' not in st.session_state: st.session_state.manager_id = None
if 'auth_key' not in st.session_state: st.session_state.auth_key = None
if 'rank_form_v' not in st.session_state: st.session_state.rank_form_v = 0

# Global Data Load
df_players = load_player_data()
STAGE = get_current_stage()
# --- FETCH MANAGERS FOR DROPDOWN ---
@st.cache_data(ttl=60)
def load_manager_names():
    res = conn.client.schema(SCHEMA).table(TABLE_MANAGERS).select("manager_name").execute()
    return [m['manager_name'] for m in res.data]

all_manager_names = load_manager_names()

# --- 5. PHASE: RATINGS ---
def show_ratings_phase():
    st.title("⭐ Player Self-Ranking Portal")
    unranked_df = df_players[~df_players['has_submitted_rank'].fillna(False).astype(bool)]
    total_players = len(df_players)
    ranked_count = total_players - len(unranked_df)
    name_to_id = {row['name']: row['id'] for _, row in unranked_df.iterrows()}

    progress = ranked_count / total_players if total_players > 0 else 0
    st.progress(progress, text=f"📊 {ranked_count}/{total_players} players have submitted rankings")

    if unranked_df.empty:
        st.success("✅ All players have submitted! The draft will open soon.")
        return

    st.info("💡 **Tip:** Start typing your name in the box below to find it quickly.")

    v = st.session_state.rank_form_v
    target_name = st.selectbox(
        "Find your name:",
        options=sorted(list(name_to_id.keys())),
        index=None,
        placeholder="Type your name here...",
        help="Search for your name as it appeared on the signup sheet.",
        key=f"rank_target_name_{v}"
    )

    st.write("---")
    st.write("### Rate your skills (1-10)")
    st.caption("""
        These ratings will determine your draft price.
        * A 10 indicates you are the best in South Africa for that category.
        * A 5 indicates you are an average player in South Africa for that category.
        * A 1 indicates you are a complete rookie in South Africa for that category.
               """)
    t = st.slider("Throwing", 1, 10, 1, key=f"rank_throwing_{v}")
    i = st.slider("Game IQ", 1, 10, 1, key=f"rank_game_iq_{v}")
    a = st.slider("Athleticism", 1, 10, 1, key=f"rank_athleticism_{v}")

    st.write("### Estimate your game averages")
    a_a = st.slider("Average Assists per Game", 0, 7, 0, key=f"rank_avg_assists_{v}")
    a_g = st.slider("Average Goals per Game", 0, 7, 0, key=f"rank_avg_goals_{v}")

    st.write("---")
    st.write("### Your Submission Summary")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Throwing", t)
    s2.metric("Game IQ", i)
    s3.metric("Athleticism", a)
    s4.metric("Avg Assists", a_a)
    s5.metric("Avg Goals", a_g)
    st.write("---")
    st.warning("Only submit a ranking for yourself! If you do not find your name. Please contact the admin.")

    if st.button("Submit My Ranking", use_container_width=True):
        if not target_name:
            st.error("❌ Please select your name from the search box.")
        else:
            try:
                player_uuid = name_to_id[target_name]
                res = conn.client.schema(SCHEMA).table(TABLE_PLAYERS).update({
                    "throwing": t, "avg_goals": a_g, "athleticism": a,
                    "avg_assists": a_a, "game_iq": i,
                    "has_submitted_rank": True
                }).eq("id", player_uuid).execute()
                if len(res.data) > 0:
                    st.session_state.rank_form_v += 1
                    st.balloons()
                    st.success(f"🔥 Thank you, {target_name}! Your rankings are locked in.")
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("⚠️ The update ran but affected 0 rows. Please contact the admin.")
            except Exception as e:
                st.error(f"Error: {e}")

# -- 6. Leaderberboard ---
def get_processed_results(conn):
    if st.session_state.get('edit_mode', False):
        return pd.DataFrame(), pd.DataFrame()

    try:
        # Pull Active Rosters from prd
        roster_res = conn.client.schema(SCHEMA).table(TABLE_ROSTERS).select(
            "is_captain, manager_id, managers(manager_name), player_id, players(name)"
        ).is_("valid_to", "null").execute()
        
        # Pull Scores
        score_res = (conn.client.schema(SCHEMA)
                     .table(TABLE_SCORES)
                     .select("player_id, points_earned")
                     )
        
        if not roster_res.data:
            return pd.DataFrame(), pd.DataFrame()

        df_rosters = pd.json_normalize(roster_res.data)
        df_rosters = df_rosters.rename(columns={
            'managers.manager_name': 'Manager_Name',
            'players.name': 'player_name'
        })

        if not score_res.data:
            df_scores = pd.DataFrame(columns=['player_id', 'points_earned'])
        else:
            df_scores = pd.DataFrame(score_res.data).groupby('player_id')['points_earned'].sum().reset_index()

        merged = df_rosters.merge(df_scores, on="player_id", how="left").fillna(0)
        merged['calc_pts'] = merged.apply(
            lambda x: x['points_earned'] * CAPTAIN_MULTIPLIER if x['is_captain'] else x['points_earned'], 
            axis=1
        )

        leaderboard = merged.groupby("Manager_Name")["calc_pts"].sum().reset_index()
        leaderboard.columns = ["Team", "Score"]
        
        return leaderboard.sort_values(by="Score", ascending=False).reset_index(drop=True), merged
    except Exception as e:
        st.sidebar.error(f"Leaderboard Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 7. PHASE: DRAFT & LIVE ---
def show_main_interface(is_live):
    if is_live:
        st.title("🏆 Live Tournament Results")
        board, full_data = get_processed_results(conn)
        
        if not board.empty:
            board['Rank'] = board['Score'].rank(method='min', ascending=False).astype(int)
            top_3_teams = board[board['Rank'] <= 3].copy()
            c1, c2, c3 = st.columns(3)
            cols = [c1, c2, c3]
            for i in range(3):
                with cols[i]:
                    if i < len(top_3_teams):
                        row = top_3_teams.iloc[i]
                        st.metric(f"{['🥇 1st', '🥈 2nd', '🥉 3rd'][i]} Place", row['Team'], f"{int(row['Score'])} pts")

            with st.expander("📊 View Full Rankings", expanded=False):
                if st.button("🔄 Sync Fresh Data"):
                    st.cache_data.clear(); st.rerun()
                st.dataframe(board[['Rank', 'Team', 'Score']], use_container_width=True, hide_index=True)
        st.divider()

    # --- DRAFTING / LOGIN LOGIC ---
    if is_live: st.subheader("🛡️ Manager Transfer Portal")
    else: st.title(f"🏆 {TOURNAMENT_NAME}")

    if st.session_state.get('update_success'):
        st.balloons(); st.success("✅ Team updated successfully!")
        st.session_state['update_success'] = False

    col_l1, col_l2 = st.columns(2)

    with col_l1:
        if is_live:
            # 1. LIVE MODE: Strict list of existing managers only
            manager_name = st.selectbox(
                "Select Your Manager Name:", 
                options=all_manager_names, 
                index=None, 
                placeholder="Choose your name...",
                key="mgr_name_select"
            )
            pin_label = "🔓 Enter PIN:"
        else:
            # 2. DRAFT MODE: Allow typing for new registrations (Option B logic)
            manager_name = st.text_input(
                "Manager/Team Name:", 
                placeholder="Enter existing/new name to login or register...",
                key="mgr_name_persistent"
            ).strip()
            
            is_existing = manager_name in all_manager_names
            if manager_name == "":
                # st.caption("👋 Enter your name to begin.")
                pin_label = "4-digit PIN:"
            elif is_existing:
                st.caption(f"✅ Found existing manager: **{manager_name}**")
                pin_label = "🔓 Enter PIN:"
            else:
                st.caption(f"✨ New Manager detected! Choose a 4-digit PIN.")
                pin_label = "🛡️ Create PIN:"

    with col_l2:
        # The PIN box now uses the dynamic label from the logic above
        manager_pin = st.text_input(
            pin_label, 
            key="mgr_pin_persistent", 
            type="password", 
            max_chars=PIN_LENGTH
        )

    if st.session_state.submitted:

        st.title("🎉 Team Successfully Locked!")
        st.balloons()
        st.success(f"Great job, {manager_name}! Your roster for {TOURNAMENT_NAME} is officially registered.")
    
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🛡️ Your Squad")
            # Filter the original dataframe to show only their selected names
            final_df = df_players[df_players['name'].isin(st.session_state.roster)]
            for _, row in final_df.iterrows():
                is_cap = row['name'] in [st.session_state.captain_open, st.session_state.captain_women]
                st.write(f"{'⭐' if is_cap else '•'} {row['name']} ({row['team']})")
                
        with col2:
            st.subheader("📊 Financials")
            total_spent = final_df['price'].sum()
            st.metric("Total Value", f"{total_spent} units")
            st.metric("Remaining Budget", f"{round(BUDGET_LIMIT - total_spent, 1)} units")
            
        st.divider()
        
        # --- ACTION BUTTONS ---
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.button("⬅️ Edit This Team", use_container_width=True):
                st.session_state.submitted = False
                st.rerun()
        
        with btn_col2:
            # THIS IS THE LOGOUT/NEW TEAM TRIGGER
            if st.button("➕ Register Another Team", type="primary", use_container_width=True):
                # Wipe all session keys to get back to a blank login
                keys_to_reset = [
                    'manager_id', 'auth_user', 'roster', 'db_names', 
                    'db_caps', 'submitted', 'edit_mode', 'auth_key',
                    'confirmed_mgr_name', 'confirmed_mgr_pin',
                    'mgr_name_persistent', 'mgr_pin_persistent'
                ]
                for key in keys_to_reset:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.cache_data.clear()
                st.rerun()
            
        st.stop()
      
    if not manager_name or len(manager_pin) < PIN_LENGTH:
        st.stop()

    # Authentication Logic
    auth_key = f"{manager_name}:{manager_pin}"
    if st.session_state.auth_key != auth_key:
        auth_res = conn.client.schema(SCHEMA).table(TABLE_MANAGERS).select("*").eq("manager_name", manager_name).eq("pin", manager_pin).execute()
        if auth_res.data:
            st.session_state.auth_user = auth_res.data[0]
            st.session_state.manager_id = auth_res.data[0]['id']
            st.session_state.confirmed_mgr_name = manager_name
            st.session_state.confirmed_mgr_pin = manager_pin
        else:
            st.session_state.manager_id = None
            if not is_live and st.session_state.get(f"name_exists_{manager_name}"):
                st.error("❌ Incorrect PIN."); st.stop()
            elif is_live:
                st.error("❌ Invalid Login."); st.stop()
        st.session_state.auth_key = auth_key

    # Roster Sync
    m_id = st.session_state.manager_id
    if m_id and not st.session_state.roster:
        curr = conn.client.schema(SCHEMA).table(TABLE_ROSTERS).select(
            "is_captain, players(name, division)"
        ).eq("manager_id", m_id).is_("valid_to", "null").execute()
        
        if curr.data:
            # 1. Capture names
            names = [item['players']['name'] for item in curr.data]
            st.session_state.roster = names
            st.session_state.db_names = set(names)
            
            # 2. Initialize db_caps
            st.session_state.db_caps = set() 
            
            # 3. Standardization for label comparison
            target_open = DIV_OPEN_LABEL.lower()

            for item in curr.data:
                p_n = item['players']['name']
                p_div = item['players']['division'].lower() if item['players']['division'] else ""
                
                if item['is_captain']:
                    st.session_state.db_caps.add(p_n)
                    if p_div == target_open:
                        st.session_state.captain_open = p_n
                    else:
                        st.session_state.captain_women = p_n
            st.rerun()

    # --- 7. PHASE: DRAFT & LIVE ---
    if m_id:
        l_col1, l_col2 = st.columns([3, 1])
        with l_col1:
            st.success(f"✅ Authenticated: {manager_name}")
        with l_col2:
            if st.button("🚪 Logout", use_container_width=True):
                # Wipe all user-specific data from the browser's memory
                keys_to_reset = [
                    'manager_id', 'auth_user', 'roster', 'db_names', 
                    'db_caps', 'submitted', 'edit_mode', 'auth_key',
                    'confirmed_mgr_name', 'confirmed_mgr_pin'
                ]
                for key in keys_to_reset:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.cache_data.clear()
                st.rerun()
                st.stop()
        
        # 1. Show Transfer Rules ONLY if Live
        if st.session_state.get('manager_id'):
            if is_live:
                with st.expander("🔄 **How Transfers Work**", expanded=True):
                    st.markdown(f"""
                                * **{MAX_PLAYER_TRANSFERS} transfers allowed**
                                * **{MAX_CAPTAIN_CHANGES} captain changes allowed**
                                * Transfers can't be undone. Once you have confirmed your selection, they are final!
                                """)
                    st.caption(f"Used: {st.session_state.auth_user.get('transfers_used', 0)} Transfers, {st.session_state.auth_user.get('captain_changes_used', 0)} Captain Changes")
            
            # 2. Show Current Roster
            with st.expander("📋 Your Current Roster", expanded=True):
                if is_live and 'full_data' in locals() and not full_data.empty:
                    my_points = full_data[full_data['Manager_Name'] == manager_name]
                    if not my_points.empty:
                        st.dataframe(my_points[['player_name', 'points_earned', 'is_captain', 'calc_pts']], hide_index=True, use_container_width=True)
                    else: 
                        st.write(f"**Players:** {', '.join(st.session_state.roster)}")
                else: 
                    st.write(f"**Players:** {', '.join(st.session_state.roster)}")

        # 3. Transfer/Edit Logic Gate
        if not is_live:
            # During DRAFT: Always allow editing, no checkbox needed
            st.session_state.edit_mode = True
        else:
            # During LIVE: Check limits and offer a toggle
            used_p = st.session_state.auth_user.get('transfers_used', 0)
            used_c = st.session_state.auth_user.get('captain_changes_used', 0)
            
            if (used_p < MAX_PLAYER_TRANSFERS) or (used_c < MAX_CAPTAIN_CHANGES):
                if st.checkbox("🛠️ Make Mid-Tournament Transfers"):
                    st.session_state.edit_mode = True
                else:
                    st.session_state.edit_mode = False
                    # We ONLY stop here in LIVE mode so the user just sees the leaderboard/roster
                    st.stop()
            else:
                st.warning("🚫 Transfer limits reached.")
                st.session_state.edit_mode = False
                # Stop here so they can't access the draft tabs
                st.stop()

    # --- 8. CALCULATIONS ---
    current_roster_df = df_players[df_players['name'].isin(st.session_state.roster)]
    total_spent = round(current_roster_df['price'].sum(), 1)
    remaining_budget = round(BUDGET_LIMIT - total_spent, 1)
    count_open = len(current_roster_df[current_roster_df['division'] == DIV_OPEN_LABEL])
    count_women = len(current_roster_df[current_roster_df['division'] == DIV_WOMEN_LABEL])
    team_counts = current_roster_df['team'].value_counts().to_dict()
    max_o, max_w = min(MAX_GENDER_SIZE, ROSTER_SIZE - count_women), min(MAX_GENDER_SIZE, ROSTER_SIZE - count_open)
    
    live_swaps = len(set(st.session_state.roster) - st.session_state.db_names)
    live_cap_changes = len({st.session_state.captain_open, st.session_state.captain_women} - st.session_state.db_caps)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("📋 Draft Summary")
        st.metric("Budget Remaining", f"{remaining_budget}", delta=f"{remaining_budget} units")
        st.divider()
        st.subheader(f"Team Usage (Max {MAX_TEAM_SIZE})")
        for team, count in team_counts.items():
            st.markdown(f":{'orange' if count >= MAX_TEAM_SIZE else 'gray'}[**{team}**: {count}/{MAX_TEAM_SIZE}]")
        st.divider()
        st.subheader(f"Opens ({count_open}/{MIN_GENDER_SIZE}+)")
        for p in st.session_state.roster:
            p_m = df_players[df_players['name'] == p]
            if not p_m.empty and p_m.iloc[0]['division'] == DIV_OPEN_LABEL:
                st.write(f"{'⭐' if p == st.session_state.captain_open else '•'} {p}")
        st.subheader(f"Womens ({count_women}/{MIN_GENDER_SIZE}+)")
        for p in st.session_state.roster:
            p_m = df_players[df_players['name'] == p]
            if not p_m.empty and p_m.iloc[0]['division'] == DIV_WOMEN_LABEL:
                st.write(f"{'⭐' if p == st.session_state.captain_women else '•'} {p}")
        if st.button("🗑️ Reset All"):
            st.session_state.roster = []; st.session_state.captain_open = None; st.session_state.captain_women = None; st.rerun()

    # --- 9. DRAFT INTERFACE ---
    with st.expander("📖 **Draft Rules**", expanded=not is_live):
        rules_text = textwrap.dedent(f"""
            * Select a full roster (**{ROSTER_SIZE} players**)
            * **{BUDGET_LIMIT}** units to spend
            * Min **{MIN_GENDER_SIZE}** per division
            * Max **{MAX_TEAM_SIZE}** per club
            * Select 1 captain per division

            **Transfers:**
            * 2 transfers and 2 captain switches allowed per day.
            * these changes will only come into effect the next day.
            * points DO NOT count retrospectively for transfers.
            
            **Scoring:**
            * 1 point per assist / goal
            * 2 points per callahan
            * Captains earn **double points**
            """)
        st.markdown(rules_text)

    if not is_live or st.session_state.get('edit_mode'):
        m_cols = st.columns(5 if is_live else 3)
        m_cols[0].metric("Spent", f"{total_spent}/{BUDGET_LIMIT}")
        m_cols[1].metric(DIV_OPEN_LABEL.title(), f"{count_open}/{max_o}")
        m_cols[2].metric(DIV_WOMEN_LABEL.title(), f"{count_women}/{max_w}")
        if is_live:
            auth_user = st.session_state.get('auth_user', {})
            lp, lc = auth_user.get('transfers_used', 0), auth_user.get('captain_changes_used', 0)
            m_cols[3].metric("Swaps", f"{lp + live_swaps}/{MAX_PLAYER_TRANSFERS}")
            m_cols[4].metric("Cap Changes", f"{lc + live_cap_changes}/{MAX_CAPTAIN_CHANGES}")

        # Tabs
        t_o, t_w = st.tabs(["Open Division", "Women's Division"])
        for label, div_f, tab in [(DIV_OPEN_LABEL.title(), DIV_OPEN_LABEL, t_o), (DIV_WOMEN_LABEL.title(), DIV_WOMEN_LABEL, t_w)]:
            with tab:
                disp_df = df_players[df_players['division'] == div_f]
                st.columns([3, 1, 1.5, 1.5])[0].write("**Player (Team)**")
                for _, row in disp_df.iterrows():
                    p_n, p_p, p_t = row['name'], row['price'], row['team']
                    is_in = p_n in st.session_state.roster
                    is_cap = (p_n in [st.session_state.captain_open, st.session_state.captain_women])
                    ca, cb, cc, cd = st.columns([3, 1, 1.5, 1.5])
                    ca.write(f"**{p_n}** ({p_t})"); cb.write(f"{p_p}")
                    if is_in:
                        if cc.button("Remove", key=f"r_{p_n}_{label}", type="primary"):
                            st.session_state.roster.remove(p_n)
                            if st.session_state.captain_open == p_n: st.session_state.captain_open = None
                            if st.session_state.captain_women == p_n: st.session_state.captain_women = None
                            st.rerun()
                        if is_cap: cd.markdown("🌟 Captain")
                        elif cd.button("Make Cap", key=f"p_{p_n}_{label}"):
                            if div_f == DIV_OPEN_LABEL: st.session_state.captain_open = p_n
                            else: st.session_state.captain_women = p_n
                            st.rerun()
                    else:
                        reason = "Add"
                        if team_counts.get(p_t, 0) >= MAX_TEAM_SIZE: reason = "Club Full"
                        elif (count_open if div_f == DIV_OPEN_LABEL else count_women) >= (max_o if div_f == DIV_OPEN_LABEL else max_w): reason = "Div Max"
                        elif len(st.session_state.roster) >= ROSTER_SIZE: reason = "Squad Full"
                        elif total_spent + p_p > BUDGET_LIMIT: reason = "Budget"
                        elif is_live and (st.session_state.auth_user['transfers_used'] + live_swaps >= MAX_PLAYER_TRANSFERS): reason = "Swap Limit"
                        if cc.button(reason, key=f"a_{p_n}_{label}", disabled=(reason != "Add")):
                            st.session_state.roster.append(p_n)
                            st.rerun()

# --- 10. UNIFIED SUBMISSION LOGIC ---
        st.divider()
        
        # Define the baseline requirements
        squad_complete = len(st.session_state.roster) == ROSTER_SIZE
        captains_set = st.session_state.captain_open and st.session_state.captain_women
        
        if squad_complete and captains_set:
            # Common variables for both modes
            sast = pytz.timezone('Africa/Johannesburg')
            now_ts = datetime.now(sast).strftime('%Y-%m-%d %H:%M:%S')
            new_caps = {st.session_state.captain_open, st.session_state.captain_women}

            if not is_live:
                if st.button("🚀 SUBMIT FINAL TEAM", use_container_width=True, type="primary"):
                    try:
                        sast = pytz.timezone('Africa/Johannesburg')
                        now_ts = datetime.now(sast).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 1. TRAP: Check if manager already exists by NAME
                        # This prevents the duplicate UUIDs seen in your screenshot
                        existing_res = conn.client.schema(SCHEMA).table(TABLE_MANAGERS)\
                            .select("id")\
                            .eq("manager_name", manager_name)\
                            .execute()
                        
                        if existing_res.data:
                            # Use the existing ID
                            active_m_id = existing_res.data[0]['id']
                            # Optionally update the PIN/Timestamp if you want
                        else:
                            # Truly a new manager, so insert
                            new_mgr = conn.client.schema(SCHEMA).table(TABLE_MANAGERS).insert({
                                "manager_name": manager_name, 
                                "pin": manager_pin, 
                                "created_at": now_ts,
                                "transfers_used": 0,
                                "captain_changes_used": 0
                            }).execute()
                            active_m_id = new_mgr.data[0]['id']
                        
                        # Set this to session state for safety
                        st.session_state.manager_id = active_m_id

                        # 2. CLEAR ROSTER (Now we know for sure which ID to wipe)
                        conn.client.schema(SCHEMA).table(TABLE_ROSTERS).delete().eq("manager_id", active_m_id).execute()
                        
                        # 3. INSERT NEW ROSTER
                        rows = []
                        new_caps = {st.session_state.captain_open, st.session_state.captain_women}
                        for p in st.session_state.roster:
                            p_info = df_players[df_players['name'] == p].iloc[0]
                            rows.append({
                                "manager_id": active_m_id, 
                                "player_id": p_info['id'], 
                                "division": p_info['division'], 
                                "is_captain": (p in new_caps), 
                                "acquired_at": now_ts, 
                                "valid_from": now_ts
                            })
                        
                        conn.client.schema(SCHEMA).table(TABLE_ROSTERS).insert(rows).execute()
                        
                        load_manager_names.clear()
                        st.session_state.submitted = True
                        st.balloons()
                        st.rerun()
                        
                    except Exception as e: 
                        st.error(f"Draft Submission Error: {e}")

            else:
                # --- LIVE MODE (TRANSFER) SUBMISSION ---
                p_in = set(st.session_state.roster) - st.session_state.db_names
                p_out = st.session_state.db_names - set(st.session_state.roster)
                caps_in = new_caps - st.session_state.db_caps
                caps_out = st.session_state.db_caps - new_caps

                if p_in or p_out or caps_in or caps_out:
                    st.subheader("📝 Pending Changes")
                    c_in, c_out = st.columns(2)
                    with c_in:
                        if p_in: st.success(f"➕ **Adding:** {', '.join(p_in)}")
                        if caps_in: st.info(f"⭐ **New Captain:** {', '.join(caps_in)}")
                    with c_out:
                        if p_out: st.error(f"➖ **Removing:** {', '.join(p_out)}")
                        if caps_out: st.warning(f"⚪ **Demoting:** {', '.join(caps_out)}")

                    # Limit Calculation
                    limit_p = st.session_state.auth_user.get('transfers_used', 0) + len(p_in)
                    limit_c = st.session_state.auth_user.get('captain_changes_used', 0) + len(caps_in)

                    if limit_p > MAX_PLAYER_TRANSFERS:
                        st.error(f"🚫 Swap limit exceeded! ({limit_p}/{MAX_PLAYER_TRANSFERS})")
                    elif limit_c > MAX_CAPTAIN_CHANGES:
                        st.error(f"🚫 Captain limit exceeded! ({limit_c}/{MAX_CAPTAIN_CHANGES})")
                    else:
                        if st.button("💾 CONFIRM & UPDATE", type="primary", use_container_width=True):
                            try:
                                # 1. Update Roster rows (Sunset old, Insert new)
                                active_db = conn.client.schema(SCHEMA).table(TABLE_ROSTERS).select("id, player_id, is_captain, players(name)").eq("manager_id", m_id).is_("valid_to", "null").execute().data
                                active_map = {r['players']['name']: {'is_cap': r['is_captain'], 'id': r['id']} for r in active_db}
                                
                                to_sunset = [data['id'] for p_n, data in active_map.items() if p_n not in st.session_state.roster or (p_n in new_caps) != data['is_cap']]
                                to_insert = [p_n for p_n in st.session_state.roster if p_n not in active_map or (p_n in new_caps) != active_map[p_n]['is_cap']]
                                
                                if to_sunset:
                                    conn.client.schema(SCHEMA).table(TABLE_ROSTERS).update({"valid_to": now_ts}).in_("id", to_sunset).execute()
                                if to_insert:
                                    ins_rows = []
                                    for p_n in to_insert:
                                        p_i = df_players[df_players['name'] == p_n].iloc[0]
                                        ins_rows.append({
                                            "manager_id": m_id, "player_id": p_i['id'], "division": p_i['division'],
                                            "is_captain": (p_n in new_caps), "valid_from": now_ts, "acquired_at": now_ts
                                        })
                                    conn.client.schema(SCHEMA).table(TABLE_ROSTERS).insert(ins_rows).execute()
                                
                                # 2. Update Manager Table (Increment)
                                conn.client.schema(SCHEMA).table(TABLE_MANAGERS).update({
                                    "transfers_used": limit_p, 
                                    "captain_changes_used": limit_c
                                }).eq("id", m_id).execute()

                                st.session_state.db_names = set(st.session_state.roster)
                                st.session_state.db_caps = {st.session_state.captain_open, st.session_state.captain_women}
                                
                                # 3. Sync Session State so UI updates before rerun
                                st.session_state.auth_user['transfers_used'] = limit_p
                                st.session_state.auth_user['captain_changes_used'] = limit_c
                                
                                st.session_state.update_success = True
                                st.session_state.edit_mode = False
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"Sync Error: {e}")
        else:
            # Feedback for incomplete squad
            missing = []
            if len(st.session_state.roster) < ROSTER_SIZE: missing.append(f"{ROSTER_SIZE - len(st.session_state.roster)} more players")
            if not st.session_state.captain_open: missing.append("an Open Captain (⭐)")
            if not st.session_state.captain_women: missing.append("a Women's Captain (⭐)")
            if st.session_state.roster:
                st.warning(f"⚠️ **Almost there:** {', '.join(missing)}")

# --- MAIN ROUTER ---
if STAGE == "RATINGS":
    show_ratings_phase()
elif STAGE == "DRAFT":
    show_main_interface(is_live=False)
elif STAGE == "LIVE":
    show_main_interface(is_live=True)
