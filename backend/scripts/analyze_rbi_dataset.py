import pandas as pd
from pathlib import Path

csv_path = Path("data/raw/rbi_forex/rbi_forex_reference_rates_long.csv")
df = pd.read_csv(csv_path)

print("Dataset Shape:", df.shape)
print("\nUnique currencies and units:")
print(df.groupby(["currency", "unit"]).agg(
    count=("rate", "count"),
    min_date=("date", "min"),
    max_date=("date", "max"),
    min_rate=("rate", "min"),
    max_rate=("rate", "max"),
    null_rates=("rate", lambda s: s.isnull().sum())
))

print("\nCheck for duplicates (date, currency):")
duplicates = df.duplicated(subset=["date", "currency"], keep=False).sum()
print("Duplicate count:", duplicates)

# Check supported currencies
for curr in ["USD", "EUR", "GBP"]:
    sub = df[df["currency"] == curr].copy()
    sub["date"] = pd.to_datetime(sub["date"])
    sub = sub.sort_values("date")
    print(f"\n{curr}:")
    print(f"  Observations: {len(sub)}")
    print(f"  Range: {sub['date'].min().strftime('%Y-%m-%d')} to {sub['date'].max().strftime('%Y-%m-%d')}")
    print(f"  Units used: {sub['unit'].unique().tolist()}")
    print(f"  Min rate: {sub['rate'].min():.4f}, Max rate: {sub['rate'].max():.4f}")
    
    # Check for non-positive or null
    invalid = sub[(sub["rate"] <= 0) | (sub["rate"].isnull())]
    print(f"  Invalid / Non-positive: {len(invalid)}")

