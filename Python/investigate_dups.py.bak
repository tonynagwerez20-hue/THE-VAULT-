import pandas as pd

df = pd.read_csv("algomind_trade_level_dataset.csv")
df["entry_time"] = pd.to_datetime(df["entry_time"], format="%Y.%m.%d %H:%M:%S")

print("=== DUPLICATE trade_id ANALYSIS ===")
print(f"Total rows          : {len(df)}")
print(f"Unique trade_ids    : {df['trade_id'].nunique()}")
dups = df[df.duplicated('trade_id', keep=False)].sort_values('trade_id')
print(f"Rows with dup id    : {len(dups)}")

# Count occurrences per id
id_counts = df['trade_id'].value_counts()
print(f"\nMax occurrences of single id: {id_counts.max()}")
print(f"IDs appearing 2x: {(id_counts == 2).sum()}")
print(f"IDs appearing 3x: {(id_counts == 3).sum()}")
print(f"IDs appearing 4x+: {(id_counts >= 4).sum()}")

# Are duplicates exact rows?
exact_dup_mask = df.duplicated(keep=False)
print(f"\nExact duplicate rows (ALL columns same): {exact_dup_mask.sum()}")

# Are the dup rows identical in every field?
non_exact = df[df.duplicated('trade_id', keep=False) & ~df.duplicated(keep=False)]
print(f"Same trade_id but DIFFERENT data: {len(non_exact)}")

# Show 3 sample duplicated trade_ids
print("\n=== SAMPLE DUPLICATE GROUPS ===")
sample_ids = id_counts[id_counts > 1].head(3).index.tolist()
cols = ["trade_id","entry_time","direction","entry_price","sl","tp","exit_price","net_pnl","r_multiple"]
for tid in sample_ids:
    rows = df[df["trade_id"] == tid]
    print(f"\ntrade_id={tid} ({len(rows)} rows):")
    print(rows[cols].to_string(index=True))

# Chronological check
print("\n=== CHRONOLOGICAL ORDER CHECK ===")
print(f"Is monotonic increasing: {df['entry_time'].is_monotonic_increasing}")
backwards = (df["entry_time"].diff() < pd.Timedelta(0)).sum()
print(f"Out-of-order steps: {backwards}")
print(f"\nFirst 5 timestamps:")
for t in df["entry_time"].head(5):
    print(f"  {t}")
print(f"\nLast 5 timestamps:")
for t in df["entry_time"].tail(5):
    print(f"  {t}")

# After dedup — would it fix chronological?
df_sorted = df.sort_values("entry_time").drop_duplicates("trade_id", keep="first")
print(f"\nAfter sort + dedup: {len(df_sorted)} rows, monotonic={df_sorted['entry_time'].is_monotonic_increasing}")
