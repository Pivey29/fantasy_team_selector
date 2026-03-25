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
    # Ensure this points to your committed CSV path
    df = pd.read_csv("data/test.csv")
    df.columns = df.columns.str.strip().str.lower()
    if 'division' in df.columns:
        df['division'] = df['division'].astype(str).str.strip().str.lower()
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

# Split the dataframes for the Sidebar and Validation
open_roster = current_roster_df[current_roster_df['division'] == 'opens']
women_roster = current_roster_df[current_roster_df['division'] == 'womens']

count_open = len(open_roster)
count_women = len(women_roster)

# --- 5. SIDEBAR: ORGANIZED VIEW ---
with st.sidebar:
    st.header("📋 Draft Summary")
    st.metric("Budget Remaining", f"{remaining_budget}")
    
    st.divider()

    # --- OPENS SECTION ---
    st.subheader(f"Opens ({count_open})")
    if not open_roster.empty:
        for _, p in open_roster.iterrows():
            is_cap = (p['name'] == st.session_state.captain_open)
            st.write(f"{'⭐ ' if is_cap else '• '}{p['name']} ({p['price']})")
    else:
        st.caption("No Open players selected.")

    st.write("") 

    # --- WOMENS SECTION ---
    st.subheader(f"Womens ({count_women})")
    if not women_roster.empty:
        for _, p in women_roster.iterrows():
            is_cap = (p['name'] == st.session_state.captain_women)
            st.write(f"{'⭐ ' if is_cap else '• '}{p['name']} ({p['price']})")
    else:
        st.caption("No Women players selected.")

    st.divider()
    if st.button("🗑️ Reset Entire Roster", use_container_width=True):
        st.session_state.roster = []
        st.session_state.captain_open = None
        st.session_state.captain_women = None
        st.rerun()

# --- 6. MAIN UI ---
st.title("🏆 2026 Fantasy Regionals Draft")

if st.session_state.submitted:
    st.success("🎉 Your team has been successfully recorded!")
    if st.button("🏁 Start New Draft"):
        st.session_state.submitted = False
        st.session_state.roster = []
        st.session_state.captain_open = None
        st.session_state.captain_women = None
        st.rerun()
    st.stop()

# Persistent Name Input using key to prevent clearing on rerun
manager_name = st.text_input("Manager Name:", key="mgr_name_persistent").strip()

if not manager_name and not st.session_state.roster:
    st.info("👋 Enter your name to begin the draft.")
    st.stop()

# --- 7. TOP COUNTERS ---
c1, c2, c3 = st.columns(3)
c1.metric("Units Spent", f"{total_spent}/100")
c2.metric("Open Count", f"{count_open}/4+", delta="✅" if count_open >= 4 else count_open-4)
c3.metric("Women Count", f"{count_women}/4+", delta="✅" if count_women >= 4 else count_women-4)

# --- 8. TABS & SELECTION ---
tab_open, tab_women = st.tabs(["Open Division", "Women's Division"])
divisions = {"Open": "opens", "Women": "womens"}

for label, div_filter in divisions.items():
    current_tab = tab_open if label == "Open" else tab_women
    with current_tab:
        disp_df = df_players[df_players['division'] == div_filter]
        
        # Grid Header
        h1, h2, h3, h4 = st.columns([3, 1, 1.5, 1.5])
        h1.write("**Player (Team)**")
        h2.write("**Price**")
        h3.write("**Standard Add**")
        h4.write("**Captaincy**")

        for _, row in disp_df.iterrows():
            p_name, p_price = row['name'], row['price']
            is_in = p_name in st.session_state.roster
            is_cap = (p_name == st.session_state.captain_open or p_name == st.session_state.captain_women)
            
            c1, c2, c3, c4 = st.columns([3, 1, 1.5, 1.5])
            c1.write(f"**{p_name}** ({row['team']})")
            c2.write(f"{p_price}")
            
            # Action Logic
            if is_in:
                if c3.button("Remove", key=f"rem_{p_name}_{label}", type="primary"):
                    st.session_state.roster.remove(p_name)
                    if st.session_state.captain_open == p_name: st.session_state.captain_open = None
                    if st.session_state.captain_women == p_name: st.session_state.captain_women = None
                    st.rerun()
                
                # Show Captain status in Column 4 if already in
                if is_cap:
                    c4.markdown("🌟 **Captain**")
                else:
                    if c4.button("Promote", key=f"promo_{p_name}_{label}"):
                        if div_filter == 'opens': st.session_state.captain_open = p_name
                        else: st.session_state.captain_women = p_name
                        st.rerun()
            else:
                can_add = (len(st.session_state.roster) < 9) and (total_spent + p_price <= 100)
                
                if c3.button("Add Player", key=f"add_{p_name}_{label}", disabled=not can_add):
                    st.session_state.roster.append(p_name)
                    st.rerun()
                
                if c4.button("Add as Cap", key=f"acap_{p_name}_{label}", disabled=not can_add):
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
        st.error("⚠️ Almost there! Please enter your name at the top to enable submission.")
    elif not valid_gender:
        st.warning(f"⚠️ Gender Balance: Need 4+ from each division. Currently {count_open}O / {count_women}W.")
    elif not has_caps:
        st.warning("⚠️ You must designate one Captain for each division.")
    elif total_spent > 100:
        st.error(f"⚠️ Over Budget: {total_spent}/100.")
    else:
        st.success(f"✅ Roster Verified for {manager_name}!")
        if st.button("🚀 SUBMIT TEAM TO LEAGUE", use_container_width=True):
            try:
                # Append to Google Sheet
                data = conn.read(worksheet="Sheet1", ttl=0)
                
                # We sort the final list for the spreadsheet columns
                # Opens first, then Womens
                sorted_roster = list(open_roster['name']) + list(women_roster['name'])
                
                new_row = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Manager_Name": manager_name,
                    "Total_Cost": total_spent,
                    "Open_Captain": st.session_state.captain_open,
                    "Women_Captain": st.session_state.captain_women
                }
                for i in range(9):
                    new_row[f"Player_{i+1}"] = sorted_roster[i] if i < len(sorted_roster) else ""

                updated_df = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.session_state.submitted = True
                st.rerun()
            except Exception as e:
                st.error(f"Error saving to Sheets: {e}")
else:
    st.info(f"Roster Status: {len(st.session_state.roster)} / 9 selected.")