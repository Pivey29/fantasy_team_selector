import pandas as pd
import numpy as np
from st_supabase_connection import SupabaseConnection
import streamlit as st
from config import TABLE_PLAYERS, MEAN, STD_DEV, DIV_OPEN_LABEL, DIV_WOMEN_LABEL, SCHEMA

# connect to DB
conn = st.connection("supabase", type=SupabaseConnection)

def calculate_bell_prices(sub_df):
    np.random.seed(42)
    sub_df = sub_df.sort_values(by="total", ascending=False).reset_index(drop=True)
    num_players = len(sub_df)
    
    # Your specific bell curve parameters
    bell_values = np.random.normal(loc=MEAN, scale=STD_DEV, size=num_players)
    bell_values = np.sort(bell_values)[::-1]
    
    sub_df["price"] = bell_values.round().astype(int)
    sub_df["price"] = sub_df["price"].clip(lower=3) # floor price of 3
    
    # ensure players with the same "total" have the same "price"
    sub_df["price"] = sub_df.groupby("total")["price"].transform("max")
    return sub_df

def calculate_pricing():
    # fetch all players who have submitted rankings
    res = (conn.client.schema(SCHEMA)
           .table(TABLE_PLAYERS)
           .select("*")
           .eq("has_submitted_rank", True)
           .execute())
    df = pd.DataFrame(res.data)
    
    if df.empty:
        print("No player data found to price.")
        return

    # 3. Calculate "total" first (Sum of the 5 skill columns)
    skill_cols = ["throwing", "avg_assists", "athleticism", "avg_goals", "game_iq"]
    df["total"] = df[skill_cols].sum(axis=1)

    # 4. Apply your Bell Curve Logic per Division
    # Split, Price, and Recombine
    open_df = calculate_bell_prices(df[df["division"].lower() == DIV_OPEN_LABEL])  # TODO
    women_df = calculate_bell_prices(df[df["division"].lower() == DIV_WOMEN_LABEL])  # TODO
    final_df = pd.concat([open_df, women_df])
    print(F"DEBUG:\n{final_df}\n")

    # 5. Push Updates to Supabase
    print(f"Updating {len(final_df)} player prices in Database...")
    for _, row in final_df.iterrows():
        conn.client.schema(SCHEMA).table(TABLE_PLAYERS).update({
            "total": int(row["total"]),
            "price": int(row["price"])
        }).eq("id", row["id"]).execute()
    
    print("✅ Database pricing sync complete!")


if __name__ == "__main__":
    calculate_pricing()