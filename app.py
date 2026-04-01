import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
from st_supabase_connection import SupabaseConnection

# --- 1. Settings --- 
from config import (
    DIV_OPEN_LABEL,
    DIV_WOMEN_LABEL,
    MAX_CAPTAIN_CHANGES,
    MAX_PLAYER_TRANSFERS,
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

# --- 3. SESSION STATE INITIALIZATION ---
if 'roster' not in st.session_state: st.session_state.roster = []
if 'submitted' not in st.session_state: st.session_state.submitted = False
if 'captain_open' not in st.session_state: st.session_state.captain_open = None
if 'captain_women' not in st.session_state: st.session_state.captain_women = None
if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
if 'db_names' not in st.session_state: st.session_state.db_names = set()
if 'db_caps' not in st.session_state: st.session_state.db_caps = set()
if 'update_success' not in st.session_state: st.session_state.update_success = False

# --- 4. CONNECTION & DATA LOADING ---
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
    import streamlit_gsheets
    gs_conn = st.connection("gsheets", type=streamlit_gsheets.GSheetsConnection)
    drafts = gs_conn.read(worksheet=RESULTS_TEAMS_TAB, ttl=0)
    scores = gs_conn.read(worksheet=RESULTS_SCORES_TAB, ttl=0)
    return drafts, scores

df_players = load_player_data()

# --- 5. LEADERBOARD LOGIC ---
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

# --- 6. UNIFIED INTERFACE LOGIC ---
if not DRAFT_OPEN:
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
    st.subheader("🛡️ Manager Portal")

    if st.session_state.get('update_success'):
        st.balloons()
        st.success("✅ Team updated successfully! Your new roster is now live.")
        st.session_state['update_success'] = False

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        manager_name = st.text_input("Manager Name:", key="mgr_name_persistent").strip()
    with col_l2:
        manager_pin = st.text_input(f"{PIN_LENGTH}-digit PIN:", key="mgr_pin_persistent", type="password", max_chars=PIN_LENGTH)

    if manager_name and len(manager_pin) == PIN_LENGTH:
        auth_res = conn.table("managers").select("id, transfers_used").eq("manager_name", manager_name).eq("pin", manager_pin).execute()
        if auth_res.data:
            st.session_state.auth_user = auth_res.data[0]
            m_id = st.session_state.auth_user['id']
            st.success(f"✅ Authenticated: {manager_name}")

            with st.expander("🔄 **How Transfers Work**", expanded=True):
                st.markdown(f"""
                            * **{MAX_PLAYER_TRANSFERS} transfers allowed**
                            * **{MAX_CAPTAIN_CHANGES} captain changes allowed**.\n
                            Transfers used: {auth_res.data[0]['transfers_used'] or 0}""")
            
            with st.expander("📋 Your Current Roster", expanded=True):
                if not st.session_state.roster:
                    current_roster = conn.table("rosters").select("is_captain, players(name, division)").eq("manager_id", m_id).is_("valid_to", "null").execute()
                    if current_roster.data:
                        st.session_state.roster = [item['players']['name'] for item in current_roster.data]
                        st.session_state.db_names = set(st.session_state.roster)
                        for item in current_roster.data:
                            p_name, p_div = item['players']['name'], str(item['players'].get('division', '')).lower().strip()
                            if item['is_captain']:
                                st.session_state.db_caps.add(p_name)
                                if p_div == DIV_OPEN_LABEL: st.session_state.captain_open = p_name
                                else: st.session_state.captain_women = p_name
                        st.rerun()

                my_points_df = full_data[full_data['Manager_Name'] == manager_name]
                if not my_points_df.empty:
                    st.dataframe(my_points_df[['player_name', 'Total', 'is_cap', 'calc_pts']], hide_index=True, use_container_width=True)
                else:
                    st.write(f"**Players:** {', '.join(st.session_state.roster)}")
                    st.write(f"**Captains:** {st.session_state.captain_open} & {st.session_state.captain_women}")

            if st.checkbox("🛠️ Make Mid-Tournament Transfers"):
                st.session_state.edit_mode = True
            else:
                st.session_state.edit_mode = False; st.stop()
        else: st.error("❌ Invalid Name/PIN."); st.stop()
    else: st.stop()

else:
    # --- DRAFTING MODE ---
    st.title(f"🏆 {TOURNAMENT_NAME}")
    col_a, col_b = st.columns(2)
    with col_a: manager_name = st.text_input("Manager Name:", key="mgr_name_persistent", placeholder="Type name...").strip()   
    if manager_name:
        name_check = conn.table("managers").select("id").eq("manager_name", manager_name).execute()
        pin_label = f"🔓 Enter PIN:" if name_check.data else f"✨ Create PIN:"
    else: pin_label = f"{PIN_LENGTH}-digit PIN:"
    with col_b: manager_pin = st.text_input(pin_label, type="password", max_chars=PIN_LENGTH)

    if st.session_state.submitted: st.success("🎉 Team submitted!"); st.stop()
    if not manager_name or len(manager_pin) < PIN_LENGTH: st.info("👋 Log in to begin."); st.stop()

    exist_check = conn.table("managers").select("id").eq("manager_name", manager_name).eq("pin", manager_pin).execute()
    if exist_check.data:
        m_id = exist_check.data[0]['id']
        if not st.session_state.roster:
            current_roster = conn.table("rosters").select("is_captain, players(name, division)").eq("manager_id", m_id).is_("valid_to", "null").execute()
            if current_roster.data:
                st.session_state.roster = [item['players']['name'] for item in current_roster.data]
                for item in current_roster.data:
                    p_name, p_div = item['players']['name'], str(item['players'].get('division', '')).lower().strip()
                    if item['is_captain']:
                        if p_div == DIV_OPEN_LABEL: st.session_state.captain_open = p_name
                        else: st.session_state.captain_women = p_name
                st.rerun()
    else:
        name_exists_query = conn.table("managers").select("id").eq("manager_name", manager_name).execute()
        if name_exists_query.data:
            st.error("❌ Incorrect PIN for this Manager Name."); st.stop()

# --- 7. CALCULATIONS ---
current_roster_df = df_players[df_players['name'].isin(st.session_state.roster)]
total_spent = current_roster_df['price'].sum()
remaining_budget = BUDGET_LIMIT - total_spent
count_open = len(current_roster_df[current_roster_df['division'] == DIV_OPEN_LABEL])
count_women = len(current_roster_df[current_roster_df['division'] == DIV_WOMEN_LABEL])
team_counts = current_roster_df['team'].value_counts().to_dict()

# --- 8. LIVE AUDIT CALCS ---
live_swaps = len(set(st.session_state.roster) - st.session_state.db_names)
live_cap_changes = len({st.session_state.captain_open, st.session_state.captain_women} - st.session_state.db_caps)

# --- SIDEBAR (RESTORED SPLIT) ---
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
        p_info = df_players[df_players['name'] == p].iloc[0]
        if p_info['division'] == DIV_OPEN_LABEL:
            is_c = (p == st.session_state.captain_open)
            st.write(f"{'⭐' if is_c else '•'} {p}")
            
    st.subheader(f"Womens ({count_women}/{MIN_GENDER_SIZE}+)")
    for p in st.session_state.roster:
        p_info = df_players[df_players['name'] == p].iloc[0]
        if p_info['division'] == DIV_WOMEN_LABEL:
            is_c = (p == st.session_state.captain_women)
            st.write(f"{'⭐' if is_c else '•'} {p}")
            
    if st.button("🗑️ Reset All", use_container_width=True):
        st.session_state.roster = []; st.session_state.captain_open = None; st.session_state.captain_women = None; st.rerun()

# --- 9. DRAFT RULES ---
with st.expander("📖 **Draft Rules**", expanded=True):
    st.markdown(f"""
    Build your squad of **{ROSTER_SIZE} players**:
    * **Squad Size:** You must select **{ROSTER_SIZE} Players**.
    * 💰 **Budget:** **{BUDGET_LIMIT} units** max.
    * ⚖️ **Gender Balance:** Min **{MIN_GENDER_SIZE} per division** ({DIV_OPEN_LABEL} and {DIV_WOMEN_LABEL}).
    * 🤝 **Team Limit:** Max **{MAX_TEAM_SIZE} per club**.
    * 🌟 **Captains:** Designate **one Captain per division** for **{CAPTAIN_MULTIPLIER}x points**!
    """)

# --- 10. DRAFTING TABS ---
m_cols = st.columns(5 if not DRAFT_OPEN else 3)
m_cols[0].metric("Spent", f"{total_spent}/{BUDGET_LIMIT}", delta=f"{remaining_budget} left")

max_o = min(MAX_GENDER_SIZE, ROSTER_SIZE - count_women)
max_w = min(MAX_GENDER_SIZE, ROSTER_SIZE - count_open)

m_cols[1].metric("Opens", f"{count_open}/{max_o}", delta=f"{max_o-count_open} left")
m_cols[2].metric("Womens", f"{count_women}/{max_w}", delta=f"{max_w-count_women} left")

if not DRAFT_OPEN:
    m_cols[3].metric("Swaps", f"{live_swaps}/{MAX_PLAYER_TRANSFERS}", delta=f"{MAX_PLAYER_TRANSFERS - live_swaps} left")
    m_cols[4].metric("Cap Changes", f"{live_cap_changes}/{MAX_CAPTAIN_CHANGES}", delta=f"{MAX_CAPTAIN_CHANGES - live_cap_changes} left")

tab_open, tab_women = st.tabs(["Open Division", "Women's Division"])
divisions = {"Open": DIV_OPEN_LABEL, "Women": DIV_WOMEN_LABEL}

for label, div_filter in divisions.items():
    with (tab_open if label == "Open" else tab_women):
        disp_df = df_players[df_players['division'] == div_filter]
        st.columns([3, 1, 1.5, 1.5])[0].write("**Player (Team)**")
        limit_for_this_div = max_o if div_filter == DIV_OPEN_LABEL else max_w
        
        for _, row in disp_df.iterrows():
            p_n, p_p, p_t = row['name'], row['price'], row['team']
            is_in = p_n in st.session_state.roster
            is_cap = (p_n == st.session_state.captain_open or p_n == st.session_state.captain_women)
            team_full = team_counts.get(p_t, 0) >= MAX_TEAM_SIZE and not is_in
            
            with st.container():
                ca, cb, cc, cd = st.columns([3, 1, 1.5, 1.5])
                ca.write(f"**{p_n}** ({p_t})"); cb.write(f"{p_p}")
                if is_in:
                    if cc.button("Remove", key=f"r_{p_n}_{label}", type="primary"):
                        st.session_state.roster.remove(p_n); st.rerun()
                    if is_cap: cd.markdown("🌟 Captain")
                    else:
                        if cd.button("Make Cap", key=f"p_{p_n}_{label}"):
                            if div_filter == DIV_OPEN_LABEL: st.session_state.captain_open = p_n
                            else: st.session_state.captain_women = p_n
                            st.rerun()
                else:
                    # BLOCKING REASONS (RESTORED)
                    auth_user = st.session_state.get('auth_user', {})
                    lifetime_transfers = auth_user.get('transfers_used', 0) or 0
                    reason = "Add"
                    transfer_hit = (not DRAFT_OPEN and (lifetime_transfers >= MAX_PLAYER_TRANSFERS) and live_swaps >= (MAX_PLAYER_TRANSFERS - lifetime_transfers))
                    gender_full_now = (count_open if div_filter == DIV_OPEN_LABEL else count_women) >= limit_for_this_div
                    roster_full = len(st.session_state.roster) >= ROSTER_SIZE
                    over_budget = total_spent + p_p > BUDGET_LIMIT

                    if team_full: reason = "Club Full"
                    elif gender_full_now: reason = "Div Max"
                    elif roster_full: reason = "Squad Full"
                    elif over_budget: reason = "Budget"
                    elif transfer_hit: reason = "Swap Limit"
                    
                    if cc.button(reason, key=f"a_{p_n}_{label}", disabled=(reason != "Add")):
                        st.session_state.roster.append(p_n); st.rerun()

# --- 11. SUBMISSION ---
st.divider()
is_complete = len(st.session_state.roster) == ROSTER_SIZE
has_captains = st.session_state.captain_open and st.session_state.captain_women

if is_complete:
    if total_spent > BUDGET_LIMIT: st.error("⚠️ Over budget!")
    elif not has_captains: st.warning("⚠️ Need captains.")
    else:
        if DRAFT_OPEN:
            if st.button("🚀 SUBMIT FINAL TEAM", use_container_width=True):
                try:
                    # 1. GENERATE SAST TIMESTAMP
                    sast = pytz.timezone('Africa/Johannesburg')
                    now_ts = datetime.now(sast).strftime('%Y-%m-%d %H:%M:%S')

                    m_res = conn.table("managers").select("id").eq("manager_name", manager_name).eq("pin", manager_pin).execute()
                    
                    if m_res.data:
                        m_id = m_res.data[0]['id']
                    else:
                        # Create manager with created_at timestamp
                        m_id = conn.table("managers").insert({
                            "manager_name": manager_name, 
                            "pin": manager_pin,
                            "created_at": now_ts # Added timestamp here
                        }).execute().data[0]['id']
                    
                    # Clean up old drafts if they exist
                    conn.table("rosters").delete().eq("manager_id", m_id).execute()
                    
                    # 2. PREPARE ENTRIES WITH TIMESTAMPS
                    new_entries = []
                    for p in st.session_state.roster:
                        p_info = df_players[df_players['name'] == p].iloc[0]
                        new_entries.append({
                            "manager_id": m_id,
                            "player_id": p_info['id'],
                            "division": p_info['division'],
                            "is_captain": (p in [st.session_state.captain_open, st.session_state.captain_women]),
                            "acquired_at": now_ts, # Added timestamp here
                            "valid_from": now_ts,  # Added timestamp here
                            "valid_to": None       # Ensure this is Null for active players
                        })
                    
                    conn.table("rosters").insert(new_entries).execute()
                    st.session_state.submitted = True
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Draft Submission Error: {e}")
        else:
            st.subheader("📝 Pending Changes")
            # 1. IDENTIFY CHANGES FOR UI AND COUNTERS
            p_in = set(st.session_state.roster) - st.session_state.db_names
            p_out = st.session_state.db_names - set(st.session_state.roster)
            
            new_caps = {st.session_state.captain_open, st.session_state.captain_women}
            caps_in = new_caps - st.session_state.db_caps
            caps_out = st.session_state.db_caps - new_caps
            
            # Use this for the actual DB billing count
            actual_cap_swaps = len(caps_in)
            
            c1, c2 = st.columns(2)
            with c1: 
                st.write("**Players:**")
                if not p_in and not p_out:
                    st.caption("No player changes")
                else:
                    for p in p_out: st.write(f"❌ {p}")
                    for p in p_in: st.write(f"✅ {p}")
            with c2:
                st.write("**🌟 Captaincy:**")
                if not caps_in and not caps_out:
                    st.caption("No captain changes")
                else:
                    for c in caps_out: st.write(f"❌ {c} (Uncap)")
                    for c in caps_in: st.write(f"✅ {c} (Cap)")

            # Check limits against DB + Live changes
            auth_user = st.session_state.get('auth_user', {})
            lifetime_p = auth_res.data[0]['transfers_used'] or 0
            lifetime_c = auth_res.data[0].get('captain_changes_used', 0)

            if (lifetime_p + len(p_in)) > MAX_PLAYER_TRANSFERS: 
                st.error(f"⚠️ Player swap limit exceeded! ({lifetime_p + len(p_in)}/{MAX_PLAYER_TRANSFERS})")
            elif (lifetime_c + actual_cap_swaps) > MAX_CAPTAIN_CHANGES: 
                st.error(f"⚠️ Captain change limit exceeded! ({lifetime_c + actual_cap_swaps}/{MAX_CAPTAIN_CHANGES})")
            elif len(p_in) == 0 and actual_cap_swaps == 0: 
                st.info("No changes detected.")
            else:
                if st.button("💾 CONFIRM & UPDATE", type="primary", use_container_width=True):
                    try:
                        sast = pytz.timezone('Africa/Johannesburg')
                        now_ts = datetime.now(sast).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # A. Fetch Active State
                        active_db = conn.table("rosters").select("id, player_id, is_captain, players(name)") \
                            .eq("manager_id", m_id).is_("valid_to", "null").execute().data
                        active_map = {r['players']['name']: {'is_cap': r['is_captain'], 'id': r['id']} for r in active_db}
                        
                        to_sunset = []
                        to_insert = []
                        
                        # SUNSET Logic: Close rows for players removed OR players who stayed but changed captaincy
                        for p_name, data in active_map.items():
                            is_still_on_team = p_name in st.session_state.roster
                            new_is_cap = (p_name in [st.session_state.captain_open, st.session_state.captain_women])
                            
                            if not is_still_on_team or new_is_cap != data['is_cap']:
                                to_sunset.append(data['id'])

                        # INSERT Logic: New rows for new players OR stayed players with new roles
                        for p_name in st.session_state.roster:
                            was_in_db = p_name in active_map
                            was_cap_in_db = active_map[p_name]['is_cap'] if was_in_db else False
                            new_is_cap = (p_name in [st.session_state.captain_open, st.session_state.captain_women])
                            
                            if not was_in_db or new_is_cap != was_cap_in_db:
                                to_insert.append(p_name)

                        # EXECUTE DB ROSTER CHANGES
                        if to_sunset:
                            conn.table("rosters").update({"valid_to": now_ts}).in_("id", to_sunset).execute()
                        
                        if to_insert:
                            rows = []
                            for p_name in to_insert:
                                p_info = df_players[df_players['name'] == p_name].iloc[0]
                                rows.append({
                                    "manager_id": m_id,
                                    "player_id": p_info['id'],
                                    "division": p_info['division'],
                                    "is_captain": (p_name in [st.session_state.captain_open, st.session_state.captain_women]),
                                    "valid_from": now_ts,
                                    "acquired_at": now_ts if p_name not in active_map else active_map[p_name].get('acquired_at', now_ts)
                                })
                            conn.table("rosters").insert(rows).execute()

                        # UPDATE MANAGER TOTALS
                        new_p_total = lifetime_p + len(p_in)
                        new_c_total = lifetime_c + actual_cap_swaps

                        conn.table("managers").update({
                            "transfers_used": new_p_total,
                            "captain_changes_used": new_c_total
                        }).eq("id", m_id).execute()

                        # REFRESH LOCAL STATE
                        st.session_state.auth_user['transfers_used'] = new_p_total
                        st.session_state.auth_user['captain_changes_used'] = new_c_total
                        st.session_state.db_names = set(st.session_state.roster)
                        st.session_state.db_caps = new_caps
                        st.session_state.update_success = True
                        st.session_state.edit_mode = False 
                        st.rerun()
                    

                    except Exception as e:
                        st.error(f"Error in Sync: {e}")
else: 
    st.info(f"📋 Progress: {len(st.session_state.roster)}/{ROSTER_SIZE}")
