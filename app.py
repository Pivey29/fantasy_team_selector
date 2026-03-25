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
        # Standardize strings to match your data/logic
        df['division'] = df['division'].astype(str).str.strip().str.lower()
    return df

df_players = load_player_data()

# --- 3. SESSION STATE ---
if 'roster' not in st.session_state:
    st.session_state.roster = []
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

# --- 4. CALCULATIONS ---
current_roster_df = df_players[df_players['name'].isin(st.session_state.roster)]
total_spent = current_roster_df['price'].sum()
remaining_budget = 100 - total_spent

# Tracking Gender
count_open = len(current_roster_df[current_roster_df['division'] == 'opens'])
count_women = len(current_roster_df[current_roster_df['division'] == 'womens'])

# --- 5. SIDEBAR STATUS ---
with st.sidebar:
    st.header("📋 Roster Status")
    st.metric("Budget Remaining", f"{remaining_budget} / 100")
    
    # Visual cues for constraints
    open_color = "green" if count_open >= 4 else "red"
    women_color = "green" if count_women >= 4 else "red"
    
    st.markdown(f":{open_color}[**Open Players:** {count_open} (Min 4)]")
    st.markdown(f":{women_color}[**Women Players:** {count_women} (Min 4)]")
    st.write(f"**Total Selected:** {len(st.session_state.roster)} / 9")
    
    st.divider()
    if not current_roster_df.empty:
        for _, p in current_roster_df.iterrows():
            st.write(f"✅ {p['name']} ({p['price']})")
        if st.button("🗑️ Reset Roster"):
            st.session_state.roster = []
            st.rerun()

# --- 6. AUTHENTICATION & SUCCESS STATE ---
st.title("🏆 2026 Fantasy Regionals Draft")

if st.session_state.submitted:
    st.success("🎉 Team successfully submitted!")
    st.balloons()
    if st.button("🏁 Start New Draft"):
        st.session_state.roster = []
        st.session_state.submitted = False
        st.rerun()
    st.stop()

manager_name = st.text_input("Enter Manager Name:").strip()

if not manager_name:
    st.info("Enter your name to unlock the draft room.")
    st.stop()

@st.cache_data(ttl=60)
def check_duplicate(name):
    try:
        data = conn.read(worksheet="Sheet1", ttl=0)
        if not data.empty and 'Manager_Name' in data.columns:
            return name.lower() in data['Manager_Name'].str.lower().values
    except:
        return False
    return False

if check_duplicate(manager_name):
    st.error(f"❌ {manager_name} has already submitted a team.")
    st.stop()

# --- 7. PLAYER SELECTION (ONLY TWO TABS) ---
tab_open, tab_women = st.tabs(["Open Division", "Women's Division"])
divisions = {"Open": "opens", "Women": "womens"}

# Iterate through the two specific tabs
for label, div_filter in divisions.items():
    current_tab = tab_open if label == "Open" else tab_women
    with current_tab:
        disp_df = df_players[df_players['division'] == div_filter]
        
        if disp_df.empty:
            st.warning(f"No players found in the CSV with division: '{div_filter}'")
            continue

        h1, h2, h3 = st.columns([3, 1, 1])
        h1.write("**Player**")
        h2.write("**Price**")
        h3.write("**Action**")

        for _, row in disp_df.iterrows():
            p_name, p_price = row['name'], row['price']
            is_in = p_name in st.session_state.roster
            
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"{p_name} ({row['team']})")
            c2.write(str(p_price))
            
            if is_in:
                if c3.button("Remove", key=f"rem_{p_name}_{label}", type="primary"):
                    st.session_state.roster.remove(p_name)
                    st.rerun()
            else:
                # Add logic: check roster size and budget
                can_add = (len(st.session_state.roster) < 9) and (total_spent + p_price <= 100)
                if c3.button("Add", key=f"add_{p_name}_{label}", disabled=not can_add):
                    st.session_state.roster.append(p_name)
                    st.rerun()

# --- 8. SUBMISSION LOGIC ---
st.divider()

valid_size = len(st.session_state.roster) == 9
valid_budget = total_spent <= 100
valid_gender = (count_open >= 4) and (count_women >= 4)

if valid_size:
    if not valid_gender:
        st.warning(f"⚠️ Gender Constraint: You have {count_open} Open and {count_women} Women. You need at least 4 of each (4/5 or 5/4 split).")
    elif not valid_budget:
        st.error(f"⚠️ Over budget! You've used {total_spent} units.")
    else:
        st.success("✅ Roster Valid! Ready to lock it in.")
        if st.button("🚀 SUBMIT TEAM"):
            try:
                # Append to Sheet1 to avoid overwriting
                existing_data = conn.read(worksheet="Sheet1", ttl=0)
                
                new_row = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Manager_Name": manager_name,
                    "Total_Cost": total_spent,
                }
                # Map players to columns
                for i in range(9):
                    new_row[f"Player_{i+1}"] = st.session_state.roster[i]

                new_row_df = pd.DataFrame([new_row])
                updated_df = pd.concat([existing_data, new_row_df], ignore_index=True)
                
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.session_state.submitted = True
                st.rerun()
                
            except Exception as e:
                st.error(f"Submission Error: {e}")
else:
    st.info(f"Roster Progress: {len(st.session_state.roster)}/9. Select {9 - len(st.session_state.roster)} more players.")