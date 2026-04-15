import pandas as pd
import numpy as np
from st_supabase_connection import SupabaseConnection
import streamlit as st
from config import TABLE_PLAYERS, MEAN, STD_DEV, DIV_OPEN_LABEL, DIV_WOMEN_LABEL, SCHEMA
np.random.seed(42)

# Connect to DB
conn = st.connection("supabase", type=SupabaseConnection)

def calculate_bell_prices(sub_df):
    """Sorts by total and maps to a normal distribution."""
    if sub_df.empty:
        return sub_df
        
    np.random.seed(42)
    # Sort by your new calculated total
    sub_df = sub_df.sort_values(by="total", ascending=False).reset_index(drop=True)
    num_players = len(sub_df)
    
    # Generate bell curve values
    bell_values = np.random.normal(loc=MEAN, scale=STD_DEV, size=num_players)
    bell_values = np.sort(bell_values)[::-1] # Highest total gets highest bell price
    
    sub_df["price"] = bell_values.round(1)  #.astype(int)
    sub_df["price"] = sub_df["price"].clip(lower=3) # Floor price
    
    # Consistency check: tie-breaks for 'total' get the same price
    # sub_df["price"] = sub_df.groupby("total")["price"].transform("max")
    return sub_df


def run_full_pricing_sync():
    """Consolidated logic: Scale contributions -> Calculate Totals -> Apply Bell Curve."""
    try:
        # 1. Fetch Data
        res = conn.client.schema(SCHEMA).table(TABLE_PLAYERS).select("*").eq("has_submitted_rank", True).execute()
        df = pd.DataFrame(res.data)

        if df.empty:
            print("No player data found to price.")
            return

        # 2. Team-Based Scaling (Your new logic)
        df['contribution'] = df['avg_goals'] + df['avg_assists']
        df['team_total'] = df.groupby('team')['contribution'].transform('sum')
        df['submission_count'] = df.groupby('team')['id'].transform('count')

        # Scaling factor with sqrt damping
        df['scaling_factor'] = np.sqrt(df['submission_count'] / 10.0)
        mask = df['team_total'] > 30
        df.loc[mask, 'scaling_factor'] = (30.0 / df['team_total']) * df['scaling_factor']

        # Calculate the normalized 'Total'
        df['scaled_contrib'] = np.ceil(df['contribution'] * df['scaling_factor'])
        df['total'] = (
            df['scaled_contrib'] + 
            df['throwing'] + 
            df['game_iq'] + 
            df['athleticism']
        )

        # 3. Apply Bell Curve per Division
        # Ensure division strings match labels exactly (case-insensitive)
        open_mask = df["division"].str.lower() == DIV_OPEN_LABEL.lower()
        women_mask = df["division"].str.lower() == DIV_WOMEN_LABEL.lower()

        open_df = calculate_bell_prices(df[open_mask].copy())
        women_df = calculate_bell_prices(df[women_mask].copy())
        
        final_df = pd.concat([open_df, women_df])

        # 4. Batch Update Supabase
        print(f"Syncing prices for {len(final_df)} players...")
        for _, row in final_df.iterrows():
            conn.client.schema(SCHEMA).table(TABLE_PLAYERS).update({
                "total": int(row["total"]),
                "price": float(row["price"])
            }).eq("id", row["id"]).execute()
        
        print("✅ Database pricing sync complete!")

    except Exception as e:
        print(f"Error during pricing sync: {e}")

if __name__ == "__main__":
    # If running as a standalone script
    run_full_pricing_sync()