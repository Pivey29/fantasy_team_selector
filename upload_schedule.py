import pandas as pd
from datetime import datetime
import pytz
from st_supabase_connection import SupabaseConnection
import streamlit as st

# Connect to Supabase
conn = st.connection("supabase", type=SupabaseConnection)

# Update based on your correction: UCT Bengals = Women, Zephyr = Open
WOMENS_TEAMS = ["Maties Ma'Ladies", "UFH Nalas", "Craft", "Hot Sauce", "Wicked", "Fierce", "UCT Bengals"]


sast = pytz.timezone('Africa/Johannesburg')

# 2. Function to fix the string
def fix_timestamp(ts_str):
    # Parse the naive string
    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
    # Localize it to SAST
    localized_dt = sast.localize(dt)
    # Return as ISO format with offset
    return localized_dt.isoformat()


def get_div(team_a, stage):
    if any(w in team_a for w in WOMENS_TEAMS) or "Women" in stage:
        return "Women"
    return "Open"

# (ID, Time, Field, Team A, Team B, Stage)
raw_schedule = [
    # --- SATURDAY APRIL 25 ---
    ("101", "2026-04-25 08:30+02", "F1", "Mutiny", "Wits Rising", "Pool A"),
    ("102", "2026-04-25 08:30+02", "F2", "U20 South Africa", "UFH Simbas", "Pool A"),
    ("103", "2026-04-25 08:30+02", "F3", "UCT Bengals", "Maties Ma'Ladies", "Women RR"),
    ("104", "2026-04-25 08:30+02", "F4", "UFH Nalas", "Craft", "Women RR"),
    ("105", "2026-04-25 08:30+02", "F5", "Hot Sauce", "Wicked", "Women RR"),
    
    ("106", "2026-04-25 11:00+02", "F1", "Bunnies", "UCT Mancubs", "Pool B"),
    ("107", "2026-04-25 11:00+02", "F2", "Kaalvoet Kaos", "Maties Ma'Gents", "Pool B"),
    ("108", "2026-04-25 11:00+02", "F3", "Rex", "Gradient", "Pool B"),
    ("109", "2026-04-25 11:00+02", "F4", "Wicked", "Fierce", "Women RR"),
    ("110", "2026-04-25 11:00+02", "F5", "Maties Ma'Ladies", "UFH Nalas", "Women RR"),
    
    ("111", "2026-04-25 13:30+02", "F1", "UCT Bengals", "Craft", "Women RR"),
    ("112", "2026-04-25 13:30+02", "F2", "U20 South Africa", "Zephyr", "Pool A"),
    ("113", "2026-04-25 13:30+02", "F3", "UFH Simbas", "Wits Rising", "Pool A"),
    ("114", "2026-04-25 13:30+02", "F4", "Bunnies", "Maties Ma'Gents", "Pool B"),
    ("115", "2026-04-25 13:30+02", "F5", "Rex", "UCT Mancubs", "Pool B"),
    
    ("116", "2026-04-25 16:00+02", "F1", "Kaalvoet Kaos", "Gradient", "Pool B"),
    ("117", "2026-04-25 16:00+02", "F2", "Zephyr", "Wits Rising", "Pool A"),
    ("118", "2026-04-25 16:00+02", "F3", "Mutiny", "UFH Simbas", "Pool A"),
    ("119", "2026-04-25 16:00+02", "F4", "Wicked", "Maties Ma'Ladies", "Women RR"),
    ("120", "2026-04-25 16:00+02", "F5", "UFH Nalas", "Fierce", "Women RR"),
    ("121", "2026-04-25 16:00+02", "F6", "Hot Sauce", "UCT Bengals", "Women RR"),
    ("122", "2026-04-25 16:00+02", "F7", "UCT Mancubs", "Maties Ma'Gents", "Pool B"),
    
    ("123", "2026-04-25 18:30+02", "F1", "Bunnies", "Gradient", "Pool B"),
    ("124", "2026-04-25 18:30+02", "F2", "Rex", "Kaalvoet Kaos", "Pool B"),

    # --- SUNDAY APRIL 26 ---
    ("201", "2026-04-26 08:30+02", "F1", "U20 South Africa", "Wits Rising", "Pool A"),
    ("202", "2026-04-26 08:30+02", "F2", "Hot Sauce", "Fierce", "Women RR"),
    ("203", "2026-04-26 08:30+02", "F3", "UCT Bengals", "UFH Nalas", "Women RR"),
    ("204", "2026-04-26 08:30+02", "F4", "Mutiny", "Zephyr", "Pool A"),
    ("205", "2026-04-26 08:30+02", "F5", "Maties Ma'Ladies", "Craft", "Women RR"),
    
    ("206", "2026-04-26 11:00+02", "F1", "Rex", "Maties Ma'Gents", "Pool B"),
    ("207", "2026-04-26 11:00+02", "F2", "Hot Sauce", "Maties Ma'Ladies", "Women RR"),
    ("208", "2026-04-26 11:00+02", "F3", "UCT Mancubs", "Gradient", "Pool B"),
    ("209", "2026-04-26 11:00+02", "F4", "UCT Bengals", "Fierce", "Women RR"),
    ("210", "2026-04-26 11:00+02", "F5", "Bunnies", "Kaalvoet Kaos", "Pool B"),
    
    ("211", "2026-04-26 13:30+02", "F1", "Zephyr", "UFH Simbas", "Pool A"),
    ("212", "2026-04-26 13:30+02", "F2", "Wicked", "Craft", "Women RR"),
    ("213", "2026-04-26 13:30+02", "F3", "Kaalvoet Kaos", "UCT Mancubs", "Pool B"),
    ("214", "2026-04-26 13:30+02", "F4", "Bunnies", "Rex", "Pool B"),
    ("215", "2026-04-26 13:30+02", "F5", "Mutiny", "U20 South Africa", "Pool A"),
    
    ("216", "2026-04-26 16:00+02", "F1", "Wicked", "UFH Nalas", "Women RR"),
    ("217", "2026-04-26 16:00+02", "F2", "Maties Ma'Ladies", "Fierce", "Women RR"),
    ("218", "2026-04-26 16:00+02", "F3", "Hot Sauce", "Craft", "Women RR"),
    ("219", "2026-04-26 16:00+02", "F4", "Maties Ma'Gents", "Gradient", "Pool B"),
    
    ("220", "2026-04-26 18:30+02", "F1", "A2", "B1", "SF2 (1-4)"),
    ("221", "2026-04-26 18:30+02", "F2", "A1", "B2", "SF1 (1-4)"),

    # --- MONDAY APRIL 27 ---
    ("30+021", "2026-04-27 08:30+02", "F1", "UCT Bengals", "Wicked", "Women RR"),
    ("30+022", "2026-04-27 08:30+02", "F2", "Hot Sauce", "UFH Nalas", "Women RR"),
    ("30+023", "2026-04-27 08:30+02", "F3", "A3", "B4", "SF3 (5-8)"),
    ("30+024", "2026-04-27 08:30+02", "F4", "A4", "B3", "SF4 (5-8)"),
    
    ("30+025", "2026-04-27 11:00+02", "F1", "Winner SF1", "Winner SF2", "Open Final"),
    ("30+026", "2026-04-27 11:00+02", "F2", "Fierce", "Craft", "Women RR"),
    ("30+027", "2026-04-27 11:00+02", "F3", "A5", "B6", "Open 9-11 RR"),
    
    ("30+028", "2026-04-27 13:30+02", "F1", "Women 1st", "Women 2nd", "Women Final"),
    ("30+029", "2026-04-27 13:30+02", "F2", "Loser SF1", "Loser SF2", "Open 3rd Place"),
    ("310", "2026-04-27 13:30+02", "F3", "Winner SF3", "Winner SF4", "Open 5th Place"),
    ("311", "2026-04-27 13:30+02", "F4", "A5", "B5", "Open 9-11 RR"),
]

def upload_full_schedule():
    sast = pytz.timezone('Africa/Johannesburg')
    batch = []
    
    for mid, t_str, fld, ta, tb, stg in raw_schedule:
        # dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M")
        # dt_iso = sast.localize(dt).isoformat()
        
        batch.append({
            "id": mid,
            "start_time": t_str,
            "field": fld,
            "team_a": ta,
            "team_b": tb,
            "stage": stg,
            "division": get_div(ta, stg),
            "status": "scheduled"
        })
    
    try:
        # Upsert allows you to run this multiple times if you need to fix a typo
        res = conn.client.schema("dev").table("matches").upsert(batch).execute()
        st.success(f"Successfully uploaded {len(res.data)} match slots to dev.matches!")
    except Exception as e:
        st.error(f"Upload failed: {e}")

if __name__ == "__main__":
    upload_full_schedule()