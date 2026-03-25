import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="2026 Fantasy Draft", page_icon="🏆", layout="wide")

# --- 2. CONNECTION & DATA LOADING ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_player_data():
    df = pd.read_csv("data/test.csv")
    df.columns = df.columns.str.strip().str.lower()
    if 'division' in df.columns:
        df['division'] = df['division'].astype(str).str.strip().str.lower()
    if 'team' in df.columns:
        df['team'] = df['team'].astype(str).str.strip()
    return df

df_players = load_player_data()

# --- 3. SESSION STATE ---
if 'roster' not in st.session_state:
    st.session_state.roster = []
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'captain_open' not in st.session_state:
    st.session_state.captain_open = None
if 'captain_women' not in st.session_state:
    st.session_state.captain_women = None

# --- 4. CALCULATIONS ---
current_roster_df = df_players[df_players['name'].isin(st.session_state.roster)]
total_spent = current_roster_df['price'].sum()
remaining_budget = 100 - total_spent

open_roster = current_roster_df[current_roster_df['division'] == 'opens']
women_roster = current_roster_df[current_roster_df['division'] == 'womens']

count_open = len(open_roster)
count_women = len(women_roster)
team_counts = current_roster_df['team'].value_counts().to_dict()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("📋 Draft Summary")
    st.metric("Budget Remaining", f"{remaining_budget}")
    
    st.divider()
    st.subheader("Team Usage (Max 2)")
    if team_counts:
        for team, count in team_counts.items():
            color = "orange" if count >= 2 else "gray"
            st.markdown(f":{color}[**{team}**: {count} / 2]")
    else:
        st.caption("No players selected.")

    st.divider()
    st.subheader(f"Opens ({count_open})")
    for _, p in open_roster.iterrows():
        is_cap = (p['name'] == st.session_state.captain_open)
        st.write(f"{'⭐ ' if is_cap else '• '}{p['name']} ({p['team']})")
    
    st.subheader(f"Womens ({count_women})")
    for _, p in women_roster.iterrows():
        is_cap = (p['name'] == st.session_state.captain_women)
        st.write(f"{'⭐ ' if is_cap else '• '}{p['name']} ({p['team']})")

    if st.button("🗑️ Reset All", use_container_width=True):
        st.session_state.roster = []
        st.session_state.captain_open = None
        st.session_state.captain_women = None
        st.rerun()

# --- 6. MAIN UI ---
st.title("🏆 2026 Fantasy Regionals Draft")

# --- NEW: INSTRUCTIONS SECTION ---
with st.expander("📖 **How to Play & Draft Rules**", expanded=True):
    st.markdown("""
    Welcome to the Regional Fantasy Draft! Build your ultimate squad of **9 players** following these constraints:
    * 💰 **Budget:** You have **100 units** to spend.
    * ⚖️ **Gender Balance:** You must select at least **4 players from each gender division** (Opens and Womens).
    * 🤝 **Club Loyalty:** You can select a maximum of **2 players from any single team**.
    * 🌟 **Captains:** You must designate **one Captain per division**. Captains earn double points!
    
    Scoring Points:
    Each time a player throws an assist or scores a goal they will earn 1 point. A player can also earn 3 points for scoring a callahan. Your selected captains will earn you double points, so chose them wisely.

    *Type your name below to begin. Your progress is saved as you browse the tabs.*
    """)

if st.session_state.submitted:
    st.success("🎉 Your team has been submitted! Good luck!")
    if st.button("Start New Draft"):
        st.session_state.submitted = False
        st.session_state.roster = []
        st.session_state.captain_open = None
        st.session_state.captain_women = None
        st.rerun()
    st.stop()

manager_name = st.text_input("Manager Name:", key="mgr_name_persistent").strip()

if not manager_name and not st.session_state.roster:
    st.stop()

# --- 7. TOP COUNTERS ---
c1, c2, c3 = st.columns(3)
c1.metric("Spent", f"{total_spent}/100")
c2.metric("Opens", f"{count_open}/4+", delta="✅" if count_open >= 4 else count_open-4)
c3.metric("Womens", f"{count_women}/4+", delta="✅" if count_women >= 4 else count_women-4)

# --- 8. TABS & SELECTION ---
tab_open, tab_women = st.tabs(["Open Division", "Women's Division"])
divisions = {"Open": "opens", "Women": "womens"}

for label, div_filter in divisions.items():
    current_tab = tab_open if label == "Open" else tab_women
    with current_tab:
        disp_df = df_players[df_players['division'] == div_filter]
        
        h1, h2, h3, h4 = st.columns([3, 1, 1.5, 1.5])
        h1.write("**Player (Team)**")
        h2.write("**Price**")
        h3.write("**Action**")
        h4.write("**Captain**")

        for _, row in disp_df.iterrows():
            p_name, p_price, p_team = row['name'], row['price'], row['team']
            is_in = p_name in st.session_state.roster
            is_cap = (p_name == st.session_state.captain_open or p_name == st.session_state.captain_women)
            
            team_usage = team_counts.get(p_team, 0)
            team_full = team_usage >= 2 and not is_in
            
            col_a, col_b, col_c, col_d = st.columns([3, 1, 1.5, 1.5])
            col_a.write(f"**{p_name}** ({p_team})")
            col_b.write(f"{p_price}")
            
            if is_in:
                if col_c.button("Remove", key=f"rem_{p_name}_{label}", type="primary"):
                    st.session_state.roster.remove(p_name)
                    if st.session_state.captain_open == p_name: st.session_state.captain_open = None
                    if st.session_state.captain_women == p_name: st.session_state.captain_women = None
                    st.rerun()
                
                if is_cap:
                    col_d.markdown("🌟 **Captain**")
                else:
                    if col_d.button("Make Cap", key=f"promo_{p_name}_{label}"):
                        if div_filter == 'opens': st.session_state.captain_open = p_name
                        else: st.session_state.captain_women = p_name
                        st.rerun()
            else:
                can_add = (len(st.session_state.roster) < 9) and (total_spent + p_price <= 100) and (not team_full)
                btn_label = "Add Player" if not team_full else f"Full ({p_team})"
                
                if col_c.button(btn_label, key=f"add_{p_name}_{label}", disabled=not can_add):
                    st.session_state.roster.append(p_name)
                    st.rerun()
                
                if col_d.button("Add as Cap", key=f"acap_{p_name}_{label}", disabled=not can_add):
                    st.session_state.roster.append(p_name)
                    if div_filter == 'opens': st.session_state.captain_open = p_name
                    else: st.session_state.captain_women = p_name
                    st.rerun()

# --- 9. SUBMISSION ---
st.divider()

has_caps = st.session_state.captain_open and st.session_state.captain_women
valid_size = len(st.session_state.roster) == 9
valid_gender = (count_open >= 4) and (count_women >= 4)

if valid_size:
    if not manager_name:
        st.error("⚠️ Enter your name at the top to enable submission.")
    elif not valid_gender:
        st.warning(f"⚠️ Gender balance required (Min 4 of each).")
    elif not has_caps:
        st.warning("⚠️ You must pick a Captain for each division in the sidebar or via the player list.")
    elif total_spent > 100:
        st.error(f"⚠️ Over Budget!")
    else:
        st.success(f"✅ Roster verified for {manager_name}!")
        if st.button("🚀 SUBMIT FINAL TEAM", use_container_width=True):
            try:
                data = conn.read(worksheet="Sheet1", ttl=0)
                sorted_names = list(open_roster['name']) + list(women_roster['name'])
                new_row = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Manager_Name": manager_name,
                    "Total_Cost": total_spent,
                    "Open_Captain": st.session_state.captain_open,
                    "Women_Captain": st.session_state.captain_women
                }
                for i in range(9):
                    new_row[f"Player_{i+1}"] = sorted_names[i] if i < len(sorted_names) else ""
                updated_df = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.session_state.submitted = True
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.info(f"Progress: {len(st.session_state.roster)} / 9 selected.")