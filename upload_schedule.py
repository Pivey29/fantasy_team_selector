from datetime import datetime
import pytz
from st_supabase_connection import SupabaseConnection
import streamlit as st
from config import SCHEMA

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
    # --- FRIDAY APRIL 24 ---
    ("001", "2026-04-24 19:00", "F1", "Hot Sauce", "UCT Bengals", "Women RR"),
    ("002", "2026-04-24 19:00", "F2", "Mutiny", "Zephyr", "Pool A"),

    # --- SATURDAY APRIL 25 ---
    ("101", "2026-04-25 08:30", "F1", "Maties Ma'Ladies", "Fierce", "Women RR"),
    ("102", "2026-04-25 08:30", "F2", "Inyhwagi", "Gradient", "Pool B"),
    ("103", "2026-04-25 08:30", "F3", "Rex", "Maties Ma'Gents", "Pool B"),
    ("104", "2026-04-25 08:30", "F4", "Bunnies", "UCT Mancubs", "Pool B"),
    ("105", "2026-04-25 08:30", "F5", "UCT Bengals", "UFH Nalas", "Women RR"),
    ("106", "2026-04-25 08:30", "F6", "Hot Sauce", "Craft", "Women RR"),
    ("107", "2026-04-25 08:30", "F7", "Mutiny", "Kaalvoet Kaos", "Pool A"),

    ("108", "2026-04-25 11:00", "F1", "UFH Nalas", "Craft", "Women RR"),
    ("109", "2026-04-25 11:00", "F2", "Mutiny", "Wits Rising", "Pool A"),
    ("110", "2026-04-25 11:00", "F3", "Bunnies", "Inyhwagi", "Pool B"),
    ("111", "2026-04-25 11:00", "F4", "UCT Bengals", "Maties Ma'Ladies", "Women RR"),
    ("112", "2026-04-25 11:00", "F5", "Hot Sauce", "Wicked", "Women RR"),

    ("113", "2026-04-25 13:30", "F1", "Zephyr", "UFH Simbas", "Pool A"),
    ("114", "2026-04-25 13:30", "F2", "Rex", "Gradient", "Pool B"),
    ("115", "2026-04-25 13:30", "F3", "UCT Mancubs", "Maties Ma'Gents", "Pool B"),
    ("116", "2026-04-25 13:30", "F4", "Hot Sauce", "Fierce", "Women RR"),
    ("117", "2026-04-25 13:30", "F5", "Kaalvoet Kaos", "Wits Rising", "Pool A"),

    ("118", "2026-04-25 16:00", "F1", "Rex", "Bunnies", "Pool B"),
    ("119", "2026-04-25 16:00", "F2", "Wicked", "Fierce", "Women RR"),
    ("120", "2026-04-25 16:00", "F3", "Maties Ma'Gents", "Gradient", "Pool B"),
    ("121", "2026-04-25 16:00", "F4", "Maties Ma'Ladies", "UFH Nalas", "Women RR"),
    ("122", "2026-04-25 16:00", "F5", "Mutiny", "UFH Simbas", "Pool A"),
    ("123", "2026-04-25 16:00", "F6", "UCT Bengals", "Craft", "Women RR"),
    ("124", "2026-04-25 16:00", "F7", "Inyhwagi", "UCT Mancubs", "Pool B"),

    ("125", "2026-04-25 18:30", "F1", "Zephyr", "Kaalvoet Kaos", "Pool A"),
    ("126", "2026-04-25 18:30", "F2", "UFH Simbas", "Wits Rising", "Pool A"),

    # --- SUNDAY APRIL 26 ---
    ("201", "2026-04-26 07:30", "F1", "UCT Mancubs", "Gradient", "Pool B"),
    ("202", "2026-04-26 07:30", "F2", "Rex", "Inyhwagi", "Pool B"),
    ("203", "2026-04-26 07:30", "F3", "Hot Sauce", "Maties Ma'Ladies", "Women RR"),
    ("204", "2026-04-26 07:30", "F4", "Wicked", "Craft", "Women RR"),
    ("205", "2026-04-26 07:30", "F5", "Bunnies", "Maties Ma'Gents", "Pool B"),
    ("206", "2026-04-26 07:30", "F6", "Kaalvoet Kaos", "UFH Simbas", "Pool A"),
    ("207", "2026-04-26 07:30", "F7", "UCT Bengals", "Fierce", "Women RR"),
    ("208", "2026-04-26 07:30", "F8", "Zephyr", "Wits Rising", "Pool A"),

    ("209", "2026-04-26 09:10", "F1", "Inyhwagi", "Maties Ma'Gents", "Pool B"),
    ("210", "2026-04-26 09:10", "F2", "Bunnies", "Gradient", "Pool B"),
    ("211", "2026-04-26 09:10", "F3", "Wicked", "UFH Nalas", "Women RR"),
    ("212", "2026-04-26 09:10", "F4", "Maties Ma'Ladies", "Craft", "Women RR"),
    ("213", "2026-04-26 09:10", "F5", "Rex", "UCT Mancubs", "Pool B"),

    # --- MONDAY APRIL 27 ---
    ("301", "2026-04-27 08:30", "F1", "SF 1", "SF 1", "Open SF"),
    ("302", "2026-04-27 08:30", "F2", "SF 2", "SF 2", "Open SF"),
    ("303", "2026-04-27 08:30", "F3", "TBC", "TBC", "Open 5-8 SF"),
    ("304", "2026-04-27 08:30", "F4", "UFH Nalas", "Fierce", "Women RR"),
    ("305", "2026-04-27 08:30", "F5", "Wicked", "Maties Ma'Ladies", "Women RR"),
    ("306", "2026-04-27 08:30", "F6", "TBC", "TBC", "Open 5-8 SF"),

    ("307", "2026-04-27 11:00", "F1", "UCT Bengals", "Wicked", "Women RR"),
    ("308", "2026-04-27 11:00", "F2", "TBC", "TBC", "Open 7th Place"),
    ("309", "2026-04-27 11:00", "F3", "A5", "B6", "Open 9-11 RR"),
    ("310", "2026-04-27 11:00", "F4", "Hot Sauce", "UFH Nalas", "Women RR"),
    ("311", "2026-04-27 11:00", "F5", "Fierce", "Craft", "Women RR"),

    ("312", "2026-04-27 13:30", "F1", "Women 1st", "Women 2nd", "Women Final"),
    ("313", "2026-04-27 13:30", "F2", "Open Final", "Open Final", "Open Final"),
    ("314", "2026-04-27 13:30", "F3", "TBC", "TBC", "Open 3rd Place"),
    ("315", "2026-04-27 13:30", "F4", "TBC", "TBC", "Open 5th Place"),
    ("316", "2026-04-27 13:30", "F5", "A5", "B5", "Open 9-11 RR"),
]

def upload_full_schedule():
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
        res = conn.client.schema(SCHEMA).table("matches").upsert(batch).execute()
        print(f"Successfully uploaded {len(res.data)} match slots to {SCHEMA}.matches!")
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    upload_full_schedule()