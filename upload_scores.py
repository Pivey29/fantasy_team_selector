import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
import os
load_dotenv()

# --- 1. CONFIG (Replace with your actual Supabase URL/Key) ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- 2. SETUP ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_from_csv(file_path):
    df = pd.read_csv(file_path)
    
    # 1. Fetch Player IDs from DB to ensure name matching
    print("Fetching player reference from Supabase...")
    players_res = supabase.table("players").select("id, name").execute()
    player_ref = {p['name'].lower().strip(): p['id'] for p in players_res.data}

    updates = []
    errors = []

    # 2. Match and Prepare Data
    for _, row in df.iterrows():
        name = str(row['player_name']).strip()
        score = row['total_score']
        
        p_id = player_ref.get(name.lower())
        
        if p_id:
            updates.append({
                "player_id": p_id,
                "player_name": name,
                "total_score": float(score)
            })
        else:
            errors.append(f"Skipping: '{name}' (Not found in players table)")

    # 3. Perform the Upsert
    if updates:
        print(f"Syncing {len(updates)} scores...")
        # .upsert() handles "Insert or Update" based on the player_id
        res = supabase.table("player_scores").upsert(updates, on_conflict="player_id").execute()
        print("✅ Sync Complete.")
    
    if errors:
        print("\n--- ISSUES ---")
        for err in errors:
            print(err)

# --- EXECUTE ---
if __name__ == "__main__":
    # Change 'scores.csv' to whatever your filename is
    upload_from_csv("data/scores.csv")