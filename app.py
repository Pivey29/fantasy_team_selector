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
    DRAFT_END_DT,
    get_current_stage,
    PLAYER_ROLES,
    ROLE_MULTIPLIERS,
    ROLE_DESCRIPTIONS
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
if 'db_roles' not in st.session_state: st.session_state.db_roles = {}  # Maps player name -> role from DB
if 'update_success' not in st.session_state: st.session_state.update_success = False
if 'manager_id' not in st.session_state: st.session_state.manager_id = None
if 'auth_key' not in st.session_state: st.session_state.auth_key = None
if 'confirmed_team_name' not in st.session_state: st.session_state.confirmed_team_name = None
if 'rank_form_v' not in st.session_state: st.session_state.rank_form_v = 0

# Global Data Load
df_players = load_player_data()
STAGE = get_current_stage()
# --- FETCH TEAMS FOR DROPDOWN ---
@st.cache_data(ttl=60)
def load_team_names():
    res = conn.client.schema(SCHEMA).table(TABLE_MANAGERS).select("team_name").execute()
    return [m['team_name'] for m in res.data if m.get('team_name')]

all_team_names = load_team_names()

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
            "is_captain, player_role, manager_id, managers(manager_name, team_name), player_id, players(name), valid_from, valid_to"
        ).execute()  # .is_("valid_to", "null")
        
        # Pull Scores
        score_res = (conn.client.schema(SCHEMA)
                     .table(TABLE_SCORES)
                     .select("player_id, points_earned")
                     .execute())
        
        if not roster_res.data:
            return pd.DataFrame(), pd.DataFrame()

        df_rosters = pd.json_normalize(roster_res.data)
        df_rosters = df_rosters.rename(columns={
            'managers.manager_name': 'Manager_Name',
            'managers.team_name': 'Team_Name',
            'players.name': 'player_name'
        })

        if not score_res.data:
            df_scores = pd.DataFrame(columns=['player_id', 'points_earned'])
        else:
            df_scores = pd.DataFrame(score_res.data).groupby('player_id')['points_earned'].sum().reset_index()

        merged = df_rosters.merge(df_scores, on="player_id", how="left")
        merged['points_earned'] = merged['points_earned'].fillna(0)
        
        # Apply role and captain multipliers
        def calculate_points(row):
            base_points = row['points_earned']
            
            # Apply role multiplier (simplified - would need to break down goals vs assists in real implementation)
            # For now, apply uniform role bonus
            role = row.get('player_role', 'hybrid') or 'hybrid'
            role_mult = 1.0  # Default, would need actual goal/assist breakdown for proper multiplier
            
            # Apply captain multiplier first
            if row['is_captain']:
                return base_points * CAPTAIN_MULTIPLIER * role_mult
            else:
                return base_points * role_mult
        
        merged['calc_pts'] = merged.apply(calculate_points, axis=1)

        leaderboard = merged.groupby("Team_Name")["calc_pts"].sum().reset_index()
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

    # Use confirmed_team_name as the single "logged in" signal
    already_confirmed = bool(st.session_state.get('confirmed_team_name'))

    if not already_confirmed:
        if is_live:
            # LIVE MODE: Select existing team by team name
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                team_name = st.selectbox(
                    "Select Your Team:",
                    options=all_team_names,
                    index=None,
                    placeholder="Choose your team...",
                    key="team_name_select"
                )
            with col_l2:
                manager_pin = st.text_input("🔓 Enter PIN:", key="mgr_pin_persistent", type="password", max_chars=PIN_LENGTH)
            manager_name = ""  # populated from DB after auth
        else:
            # DRAFT MODE: team name (unique) + manager name (new only) + PIN
            team_name = st.text_input(
                "Team Name (unique):",
                placeholder="Your fantasy team name...",
                key="team_name_persistent"
            ).strip()

            is_existing_team = team_name in all_team_names
            if team_name:
                if is_existing_team:
                    st.caption(f"✅ Found existing team: **{team_name}**")
                else:
                    st.caption(f"✨ New team — enter your name and create a PIN.")

            # Manager name only needed for new registrations
            if team_name and not is_existing_team:
                manager_name = st.text_input(
                    "Your Full Name:",
                    key="mgr_name_persistent"
                ).strip()
            else:
                manager_name = ""  # populated from DB for existing teams

            pin_label = "🔓 Enter PIN:" if is_existing_team else ("🛡️ Create 4-digit PIN:" if team_name else "4-digit PIN:")
            manager_pin = st.text_input(pin_label, key="mgr_pin_persistent", type="password", max_chars=PIN_LENGTH)

            # New team: require all fields before showing Start Drafting
            if team_name and not is_existing_team and manager_name and len(manager_pin) == PIN_LENGTH:
                if st.button("🚀 Start Drafting", type="primary", use_container_width=True):
                    st.session_state.confirmed_team_name = team_name
                    st.session_state.confirmed_mgr_name = manager_name
                    st.session_state.confirmed_mgr_pin = manager_pin
                    st.rerun()
                st.stop()

        if not team_name or len(manager_pin) < PIN_LENGTH:
            st.stop()
    else:
        team_name = st.session_state.confirmed_team_name
        manager_name = st.session_state.confirmed_mgr_name
        manager_pin = st.session_state.confirmed_mgr_pin

    if st.session_state.submitted:

        st.balloons()
        st.success(f"Great job, {manager_name}! Your roster ('{team_name}') is officially registered.")
    
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🛡️ Your Squad")
            # Filter the original dataframe to show only their selected names
            final_df = df_players[df_players['name'].isin(st.session_state.roster)]
            for _, row in final_df.iterrows():
                is_cap = row['name'] in [st.session_state.captain_open, st.session_state.captain_women]
                div_label = DIV_OPEN_LABEL.title() if row['division'] == DIV_OPEN_LABEL else DIV_WOMEN_LABEL.title()
                role_key = f"role_{row['name']}_{div_label}"
                p_role = st.session_state.get(role_key, 'hybrid')
                st.write(f"{'⭐' if is_cap else '•'} {row['name']} ({row['team']}) - {p_role}")
                
        with col2:
            st.subheader("📊 Financials")
            total_spent = round(final_df['price'].sum(), 1)
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
                    'confirmed_team_name', 'confirmed_mgr_name', 'confirmed_mgr_pin',
                    'team_name_persistent', 'mgr_name_persistent', 'mgr_pin_persistent', 'team_name_select'
                ]
                for key in keys_to_reset:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.cache_data.clear()
                st.rerun()
            
        st.stop()

    # Authentication Logic
    auth_key = f"{team_name}:{manager_pin}"
    if st.session_state.auth_key != auth_key:
        auth_res = conn.client.schema(SCHEMA).table(TABLE_MANAGERS).select("*").eq("team_name", team_name).eq("pin", manager_pin).execute()
        if auth_res.data:
            st.session_state.auth_user = auth_res.data[0]
            st.session_state.manager_id = auth_res.data[0]['id']
            manager_name = auth_res.data[0]['manager_name']
            st.session_state.confirmed_team_name = team_name
            st.session_state.confirmed_mgr_name = manager_name
            st.session_state.confirmed_mgr_pin = manager_pin
            st.session_state.auth_key = auth_key
            st.rerun()
        else:
            st.session_state.manager_id = None
            if not is_live and team_name in all_team_names:
                st.error("❌ Incorrect PIN."); st.stop()
            elif is_live:
                st.error("❌ Invalid Login."); st.stop()
        st.session_state.auth_key = auth_key

    # Roster Sync
    m_id = st.session_state.manager_id
    if m_id and not st.session_state.roster:
        curr = conn.client.schema(SCHEMA).table(TABLE_ROSTERS).select(
            "is_captain, player_role, players(name, division)"
        ).eq("manager_id", m_id).is_("valid_to", "null").execute()
        
        if curr.data:
            # 1. Capture names
            names = [item['players']['name'] for item in curr.data]
            st.session_state.roster = names
            st.session_state.db_names = set(names)
            
            # 2. Initialize db_caps and db_roles
            st.session_state.db_caps = set() 
            st.session_state.db_roles = {}
            
            # 3. Standardization for label comparison
            target_open = DIV_OPEN_LABEL.lower()

            for item in curr.data:
                p_n = item['players']['name']
                p_div = item['players']['division'].lower() if item['players']['division'] else ""
                p_role = item.get('player_role', 'hybrid') or 'hybrid'
                
                # Store role in db_roles for tracking
                st.session_state.db_roles[p_n] = p_role
                
                # Initialize selectbox key with DB value
                div_label = DIV_OPEN_LABEL.title() if p_div == target_open else DIV_WOMEN_LABEL.title()
                role_key = f"role_{p_n}_{div_label}"
                st.session_state[role_key] = p_role
                
                if item['is_captain']:
                    st.session_state.db_caps.add(p_n)
                    if p_div == target_open:
                        st.session_state.captain_open = p_n
                    else:
                        st.session_state.captain_women = p_n
            st.rerun()

    # --- 7. PHASE: DRAFT & LIVE ---
    # Show banner + logout for ALL confirmed users (new and existing managers)
    l_col1, l_col2 = st.columns([3, 1])
    with l_col1:
        if m_id:
            st.success(f"✅ Authenticated: **{manager_name}** | Team: **{team_name}**")
        else:
            st.info(f"👋 Drafting as: **{manager_name}** | Team: **{team_name}** (New)")
    with l_col2:
        if st.button("🚪 Logout", use_container_width=True):
            keys_to_reset = [
                'manager_id', 'auth_user', 'roster', 'db_names',
                'db_caps', 'submitted', 'edit_mode', 'auth_key',
                'confirmed_team_name', 'confirmed_mgr_name', 'confirmed_mgr_pin',
                'team_name_persistent', 'mgr_name_persistent', 'mgr_pin_persistent', 'team_name_select',
                'captain_open', 'captain_women', 'db_roles', 'update_success'
            ]
            for key in keys_to_reset:
                if key in st.session_state:
                    del st.session_state[key]
            st.cache_data.clear()
            st.rerun()

    if m_id:
        
        # 1. Show Transfer Rules ONLY if Live
        if st.session_state.get('manager_id'):
            if is_live:
                with st.expander("🔄 **How Transfers Work**", expanded=True):
                    st.markdown(f"""
                                * **{MAX_PLAYER_TRANSFERS} transfers allowed** (swapping a player OR changing a player's role each count as 1 transfer)
                                * **{MAX_CAPTAIN_CHANGES} captain changes allowed**
                                * Transfers can't be undone. Once you have confirmed your selection, they are final!
                                """)
                    st.caption(f"Used: {st.session_state.auth_user.get('transfers_used', 0)}/{MAX_PLAYER_TRANSFERS} Transfers, {st.session_state.auth_user.get('captain_changes_used', 0)}/{MAX_CAPTAIN_CHANGES} Captain Changes")
            
            # 2. Show Current Roster
            with st.expander("📋 Your Roster", expanded=True):
                if is_live and 'full_data' in locals() and not full_data.empty:
                    my_points = full_data[full_data['manager_id'] == m_id] if m_id else pd.DataFrame()
                    if not my_points.empty:
                        _display = my_points[['player_name', 'points_earned', 'is_captain', 'player_role', 'calc_pts', 'valid_from', 'valid_to']].copy()
                        def fmt_ts(val):
                            if not val or val == 0:
                                return ''
                            try:
                                return pd.to_datetime(val, utc=True).strftime('%-d %b %H:%M')
                            except Exception:
                                return str(val)
                        _display['valid_from'] = _display['valid_from'].apply(fmt_ts)
                        _display['valid_to'] = _display['valid_to'].apply(fmt_ts)
                        _display = _display.sort_values(by=["player_name", "valid_from"])
                        st.dataframe(_display, hide_index=True, use_container_width=True)
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
    live_role_changes = sum(
        1 for p_n in st.session_state.roster
        if p_n in st.session_state.db_names
        and st.session_state.get(
            f"role_{p_n}_{DIV_OPEN_LABEL.title() if df_players[df_players['name'] == p_n].iloc[0]['division'] == DIV_OPEN_LABEL else DIV_WOMEN_LABEL.title()}",
            'hybrid'
        ) != st.session_state.db_roles.get(p_n, 'hybrid')
    )
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
        st.subheader(f"Opens ({count_open}/{MIN_GENDER_SIZE})")
        for p in st.session_state.roster:
            p_m = df_players[df_players['name'] == p]
            if not p_m.empty and p_m.iloc[0]['division'] == DIV_OPEN_LABEL:
                role_key = f"role_{p}_{DIV_OPEN_LABEL.title()}"
                p_role = st.session_state.get(role_key, 'hybrid')
                st.write(f"{'⭐' if p == st.session_state.captain_open else '•'} {p} ({p_role})")
        st.subheader(f"Womens ({count_women}/{MIN_GENDER_SIZE})")
        for p in st.session_state.roster:
            p_m = df_players[df_players['name'] == p]
            if not p_m.empty and p_m.iloc[0]['division'] == DIV_WOMEN_LABEL:
                role_key = f"role_{p}_{DIV_WOMEN_LABEL.title()}"
                p_role = st.session_state.get(role_key, 'hybrid')
                st.write(f"{'⭐' if p == st.session_state.captain_women else '•'} {p} ({p_role})")
        if st.button("🗑️ Reset All"):
            st.session_state.roster = []; st.session_state.captain_open = None; st.session_state.captain_women = None; st.rerun()

    # --- 9. DRAFT INTERFACE ---
    with st.expander("📖 **Draft Rules**", expanded=not is_live):
        rules_text = textwrap.dedent(f"""
            * Select a full roster (**{ROSTER_SIZE} players**)
            * **{BUDGET_LIMIT}** units to spend
            * **{MIN_GENDER_SIZE}** players per division
            * Max **{MAX_TEAM_SIZE}** players per club
            * Select 1 captain per division
            * Assign each player a role: **Handler**, **Cutter**, or **Hybrid** (default)
            * Unlimited changes allowed until {DRAFT_END_DT.strftime("%Y-%m-%d %H:%M")} - just log back in to your profile to make the changes.

            **Player Roles:**
            * **Handler** 🎯: Primary ball handler - earns bonus points for assists
            * **Cutter** 🏃: Field runner - earns bonus points for goals
            * **Hybrid** ⚪: Versatile player - standard point multipliers

            **In Tournament/Live Transfers:**
            * {MAX_PLAYER_TRANSFERS} player transfers and {MAX_CAPTAIN_CHANGES} captain transfers allowed throughout the tournament.
            * switching a player's role (e.g. from 'cutter' to 'handler' counts as a transfer)
            * these changes will only come into effect the next round of matches.
            * points DO NOT count retrospectively for transfers/captain changes.
            
            **Scoring (Per Player Role):**
            * 🎯 **Handler**: 6 pts per assist, 2 pts per goal
            * 🏃 **Cutter**: 2 pts per assist, 6 pts per goal
            * ⚪ **Hybrid**: 4 pts per assist, 4 pts per goal
            * **Callahan**: 10 points
            * **Captains**: Earn double points (x2 all scoring above)
            """)
        st.markdown(rules_text)

    # --- ROLE ASSIGNMENT GUIDE ---
    st.info("""
        **🎯 Assign Each Player a Role** – Choose the role that best matches how they'll play:
        * **🎯 Handler** (6 pts/assist, 2 pts/goal): Primary ball handler & play-maker
        * **🏃 Cutter** (2 pts/assist, 6 pts/goal): Field runner & finisher
        * **⚪ Hybrid** (4 pts/assist, 4 pts/goal): Versatile/Unknown role
    """, icon="💡")

    if not is_live or st.session_state.get('edit_mode'):
        m_cols = st.columns(5 if is_live else 3)
        m_cols[0].metric("Spent", f"{total_spent}/{BUDGET_LIMIT}")
        m_cols[1].metric(DIV_OPEN_LABEL.title(), f"{count_open}/{max_o}")
        m_cols[2].metric(DIV_WOMEN_LABEL.title(), f"{count_women}/{max_w}")
        if is_live:
            auth_user = st.session_state.get('auth_user', {})
            lp, lc = auth_user.get('transfers_used', 0), auth_user.get('captain_changes_used', 0)
            m_cols[3].metric("Swaps", f"{lp + live_swaps + live_role_changes}/{MAX_PLAYER_TRANSFERS}")
            m_cols[4].metric("Cap Changes", f"{lc + live_cap_changes}/{MAX_CAPTAIN_CHANGES}")

        # Tabs
        t_o, t_w = st.tabs(["Open Division", "Women's Division"])
        for label, div_f, tab in [(DIV_OPEN_LABEL.title(), DIV_OPEN_LABEL, t_o), (DIV_WOMEN_LABEL.title(), DIV_WOMEN_LABEL, t_w)]:
            with tab:
                disp_df = df_players[df_players['division'] == div_f]
                # Captain status for this division
                div_cap = st.session_state.captain_open if div_f == DIV_OPEN_LABEL else st.session_state.captain_women
                if div_cap:
                    st.success(f"🌟 Captain: **{div_cap}**")
                else:
                    st.warning(f"⭐ No captain selected yet — click '⭐ Make Cap' next to a player below.")
                st.columns([3, 1, 1.5, 1.5, 2.5])[0].write("**Player (Team)**")
                for _, row in disp_df.iterrows():
                    p_n, p_p, p_t = row['name'], row['price'], row['team']
                    is_in = p_n in st.session_state.roster
                    is_cap = (p_n in [st.session_state.captain_open, st.session_state.captain_women])
                    
                    # Get current role from selectbox session state key
                    div_label = DIV_OPEN_LABEL.title() if div_f == DIV_OPEN_LABEL else DIV_WOMEN_LABEL.title()
                    role_key = f"role_{p_n}_{div_label}"
                    current_role = st.session_state.get(role_key, 'hybrid')
                    
                    ca, cb, cc, cd, ce = st.columns([3, 1, 1.5, 1.5, 2.5])
                    ca.write(f"**{p_n}** ({p_t})"); cb.write(f"{p_p}")
                    if is_in:
                        def _do_remove(name=p_n):
                            st.session_state.roster.remove(name)
                            if st.session_state.captain_open == name: st.session_state.captain_open = None
                            if st.session_state.captain_women == name: st.session_state.captain_women = None
                        cc.button("Remove", key=f"r_{p_n}_{label}", type="primary", on_click=_do_remove)
                        if is_cap:
                            cd.markdown("🌟 **Captain**")
                        else:
                            # Show whether a captain for this division is already set
                            div_cap = st.session_state.captain_open if div_f == DIV_OPEN_LABEL else st.session_state.captain_women
                            btn_label = "⭐ Make Cap" if not div_cap else "⭐ Swap Cap"
                            if cd.button(btn_label, key=f"p_{p_n}_{label}"):
                                if div_f == DIV_OPEN_LABEL: st.session_state.captain_open = p_n
                                else: st.session_state.captain_women = p_n
                                st.rerun()
                        
                        # Role selection for players in roster - styled buttons
                        role_display = {
                            "handler": "🎯 Handler",
                            "cutter": "🏃 Cutter",
                            "hybrid": "⚪ Hybrid"
                        }
                        role_cols = st.columns(3)
                        for i, role in enumerate(PLAYER_ROLES):
                            if role_cols[i].button(
                                role_display[role],
                                key=f"role_btn_{p_n}_{label}_{role}",
                                use_container_width=True,
                                type="primary" if current_role == role else "secondary"
                            ):
                                role_key = f"role_{p_n}_{label}"
                                st.session_state[role_key] = role
                                st.rerun()
                    else:
                        reason = "Add"
                        if team_counts.get(p_t, 0) >= MAX_TEAM_SIZE: reason = "Club Full"
                        elif (count_open if div_f == DIV_OPEN_LABEL else count_women) >= (max_o if div_f == DIV_OPEN_LABEL else max_w): reason = "Div Max"
                        elif len(st.session_state.roster) >= ROSTER_SIZE: reason = "Squad Full"
                        elif total_spent + p_p > BUDGET_LIMIT: reason = "Budget"
                        elif is_live and (st.session_state.auth_user['transfers_used'] + live_swaps + live_role_changes >= MAX_PLAYER_TRANSFERS): reason = "Swap Limit"
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
                        
                        # 1. TRAP: Check if team already exists by team_name (unique)
                        existing_res = conn.client.schema(SCHEMA).table(TABLE_MANAGERS)\
                            .select("id")\
                            .eq("team_name", team_name)\
                            .execute()
                        
                        if existing_res.data:
                            # Use the existing ID
                            active_m_id = existing_res.data[0]['id']
                            # Optionally update the PIN/Timestamp if you want
                        else:
                            # Truly a new manager, so insert
                            new_mgr = conn.client.schema(SCHEMA).table(TABLE_MANAGERS).insert({
                                "manager_name": manager_name,
                                "team_name": team_name,
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
                            
                            # Get role from selectbox session state key
                            div_label = DIV_OPEN_LABEL.title() if p_info['division'] == DIV_OPEN_LABEL else DIV_WOMEN_LABEL.title()
                            role_key = f"role_{p}_{div_label}"
                            p_role = st.session_state.get(role_key, 'hybrid')
                            
                            rows.append({
                                "manager_id": active_m_id, 
                                "player_id": p_info['id'], 
                                "division": p_info['division'], 
                                "is_captain": (p in new_caps),
                                "player_role": p_role,
                                "acquired_at": now_ts, 
                                "valid_from": now_ts
                            })
                        
                        conn.client.schema(SCHEMA).table(TABLE_ROSTERS).insert(rows).execute()
                        
                        load_team_names.clear()
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

                # Detect role-only changes for retained players
                role_changes = set()
                for p_n in st.session_state.roster:
                    if p_n in p_in:
                        continue  # new player, handled by p_in
                    p_i = df_players[df_players['name'] == p_n].iloc[0]
                    div_label = DIV_OPEN_LABEL.title() if p_i['division'] == DIV_OPEN_LABEL else DIV_WOMEN_LABEL.title()
                    current_role = st.session_state.get(f"role_{p_n}_{div_label}", 'hybrid')
                    db_role = st.session_state.db_roles.get(p_n, 'hybrid')
                    if current_role != db_role:
                        role_changes.add(p_n)

                if p_in or p_out or caps_in or caps_out or role_changes:
                    st.subheader("📝 Pending Changes")
                    c_in, c_out = st.columns(2)
                    with c_in:
                        if p_in: st.success(f"➕ **Adding:** {', '.join(p_in)}")
                        if caps_in: st.info(f"⭐ **New Captain:** {', '.join(caps_in)}")
                        if role_changes: st.info(f"🔄 **Role Change:** {', '.join(role_changes)}")
                    with c_out:
                        if p_out: st.error(f"➖ **Removing:** {', '.join(p_out)}")
                        if caps_out: st.warning(f"⚪ **Demoting:** {', '.join(caps_out)}")

                    # Limit Calculation
                    limit_p = st.session_state.auth_user.get('transfers_used', 0) + len(p_in) + len(role_changes)
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

                                to_sunset = [data['id'] for p_n, data in active_map.items() if p_n not in st.session_state.roster or (p_n in new_caps) != data['is_cap'] or p_n in role_changes]
                                to_insert = [p_n for p_n in st.session_state.roster if p_n not in active_map or (p_n in new_caps) != active_map[p_n]['is_cap'] or p_n in role_changes]
                                
                                if to_sunset:
                                    conn.client.schema(SCHEMA).table(TABLE_ROSTERS).update({"valid_to": now_ts}).in_("id", to_sunset).execute()
                                if to_insert:
                                    ins_rows = []
                                    for p_n in to_insert:
                                        p_i = df_players[df_players['name'] == p_n].iloc[0]
                                        
                                        # Get role from selectbox session state key
                                        div_label = DIV_OPEN_LABEL.title() if p_i['division'] == DIV_OPEN_LABEL else DIV_WOMEN_LABEL.title()
                                        role_key = f"role_{p_n}_{div_label}"
                                        p_role = st.session_state.get(role_key, 'hybrid')
                                        
                                        ins_rows.append({
                                            "manager_id": m_id, "player_id": p_i['id'], "division": p_i['division'],
                                            "is_captain": (p_n in new_caps), "player_role": p_role, "valid_from": now_ts, "acquired_at": now_ts
                                        })
                                    conn.client.schema(SCHEMA).table(TABLE_ROSTERS).insert(ins_rows).execute()
                                
                                # 2. Update Manager Table (Increment)
                                conn.client.schema(SCHEMA).table(TABLE_MANAGERS).update({
                                    "transfers_used": limit_p, 
                                    "captain_changes_used": limit_c
                                }).eq("id", m_id).execute()

                                st.session_state.db_names = set(st.session_state.roster)
                                st.session_state.db_caps = {st.session_state.captain_open, st.session_state.captain_women}
                                for p_n in to_insert:
                                    p_i = df_players[df_players['name'] == p_n].iloc[0]
                                    div_label = DIV_OPEN_LABEL.title() if p_i['division'] == DIV_OPEN_LABEL else DIV_WOMEN_LABEL.title()
                                    st.session_state.db_roles[p_n] = st.session_state.get(f"role_{p_n}_{div_label}", 'hybrid')
                                
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
            if st.session_state.roster:
                players_needed = ROSTER_SIZE - len(st.session_state.roster)
                if players_needed > 0:
                    st.warning(f"⚠️ Still need **{players_needed} more player{'s' if players_needed > 1 else ''}** to complete your squad.")
                if not st.session_state.captain_open:
                    st.error("🚫 **No Open Division captain selected.** Click '⭐ Make Cap' next to an Open player to assign one.")
                if not st.session_state.captain_women:
                    st.error("🚫 **No Women's Division captain selected.** Click '⭐ Make Cap' next to a Women's player to assign one.")
                if not captains_set:
                    st.info("ℹ️ You must select 1 captain per division before you can submit your team.")

# --- MAIN ROUTER ---
if STAGE == "RATINGS":
    show_ratings_phase()
elif STAGE == "DRAFT":
    show_main_interface(is_live=False)
elif STAGE == "LIVE":
    show_main_interface(is_live=True)
