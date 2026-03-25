import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

np.random.seed(42)

df = pd.read_csv("data/ratings.csv")
print(len(df))
df.head()

open = df[df["division"] == "Opens"]
women = df[df["division"] == "Womens"]

def get_prices(df: pd.DataFrame):
    # sort on sum of ratings
    df = df.sort_values(by='total', ascending=False).reset_index(drop=True)
    num_players = len(df)

    bell_values = np.random.normal(loc=12, scale=6, size=num_players)
    bell_values = np.sort(bell_values)[::-1]
    
    df['price'] = bell_values.round().astype(int)
    df['price'] = df.groupby('total')['price'].transform('max')
    df['price'] = df['price'].clip(lower=3)

    print(f"Total Talent Cost: {df['price'].sum()}")
    print(f"Average Player Cost: {df['price'].mean():.2f}")
    print(f"Cost of a 'Dream Team' (Top 9): {df['price'].head(9).sum()}")
    
    return df

df = get_prices(df)

plt.hist(df['price'], bins=10)
plt.ylabel("Count of Players")
plt.xlabel("Cost")

women = get_prices(women)
open = get_prices(open)

plt.hist(open['price'], bins=10, color="green", alpha=0.3, label="open")
plt.hist(women['price'], bins=10, color="blue", alpha=0.3, label="women")
plt.ylabel("Count of Players")
plt.xlabel("Cost")
plt.legend()

all = (pd.concat([open, women], ignore_index=True)
       .sort_values(by=["price", "total"], ascending=False).
       reset_index(drop=True))

all.to_csv("data/test.csv", index=False)