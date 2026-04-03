import pandas as pd
import os
from supabase import create_client
from dotenv import load_dotenv
from config import (
    SCHEMA, TABLE_PLAYERS, TABLE_SCORES
)

load_dotenv()

# --- 1. CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- 2. SETUP ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_from_csv(file_path):
    # Load CSV with columns: name, day, score
    df = pd.read_csv(file_path)
    
    # 1. Fetch Player IDs from prd schema
    print(f"Fetching player reference from {SCHEMA}.{TABLE_PLAYERS}...")
    players_res = supabase.schema(SCHEMA).table(TABLE_PLAYERS).select("id, name").execute()
    
    # Create a mapping: "player name" -> "uuid"
    player_ref = {p['name'].lower().strip(): p['id'] for p in players_res.data}

    updates = []
    errors = []

    # 2. Match and Prepare Data
    for _, row in df.iterrows():
        raw_name = str(row['name']).strip()
        day_val = str(row['day']).strip()
        score_val = row['score']
        
        p_id = player_ref.get(raw_name.lower())
        
        if p_id:
            updates.append({
                "player_id": p_id,
                "day_number": day_val,       # Tracks Day 1, Day 2, etc.
                "points_earned": float(score_val)
            })
        else:
            errors.append(f"❌ Skipping: '{raw_name}' (Not found in players table)")

    # 3. Perform the Upsert
    if updates:
        print(f"Syncing {len(updates)} scores to {SCHEMA}.{TABLE_SCORES}...")
        
        # NOTE: For .upsert() to work as an 'Update', you need a Unique Constraint 
        # in Supabase on (player_id, day_number). 
        # Otherwise, it will just keep inserting new rows.
        res = supabase.schema(SCHEMA).table(TABLE_SCORES).upsert(
            updates, 
            on_conflict="player_id, day_number" 
        ).execute()
        
        print("✅ Sync Complete.")
    
    if errors:
        print("\n--- ⚠️ MATCHING ISSUES ---")
        for err in errors:
            print(err)

# --- EXECUTE ---
if __name__ == "__main__":
    # Ensure this path matches your actual file location
    upload_from_csv("data/scores.csv")
