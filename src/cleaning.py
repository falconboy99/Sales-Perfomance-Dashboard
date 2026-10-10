"""Data cleaning and preprocessing for the Sample Superstore sales dataset.

The raw CSV is the Tableau "Sample - Superstore" workbook flattened into one file:
rows 1-9994 are order lines, followed by the regional-manager table ("People")
and the returned-orders table ("Returns") appended underneath. This module splits
those three tables apart, fixes types and gaps, and adds analysis features.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "superstore_raw.csv"
OUT_DIR = ROOT / "data" / "processed"

# Burlington, Vermont is the only city in the data whose postal code is blank.
BURLINGTON_VT_ZIP = 5401


def load_raw(path=RAW_PATH):
    return pd.read_csv(path, dtype={"Row ID": str})


def split_tables(raw):
    """Split the flattened file into orders, people and returns tables."""
    is_order = raw["Row ID"].str.fullmatch(r"\d+")
    orders = raw[is_order].copy()

    tail = raw[~is_order]
    # Drop the two embedded header rows ("Person, Region" and "Returned, Order ID").
    people = tail[~tail["Row ID"].isin(["Yes", "Person", "Returned"])]
    people = people[["Row ID", "Order ID"]].rename(
        columns={"Row ID": "Regional Manager", "Order ID": "Region"}
    )

    returns = tail[tail["Row ID"].eq("Yes")][["Order ID"]].drop_duplicates()
    returns["Returned"] = True
    return orders, people.reset_index(drop=True), returns.reset_index(drop=True)


def clean_orders(orders, returns, people, log=None):
    """Return a typed, de-duplicated, feature-enriched orders table."""
    log = log if log is not None else []
    df = orders.copy()
    df.columns = [c.strip() for c in df.columns]

    df["Row ID"] = df["Row ID"].astype(int)
    for col in ["Order Date", "Ship Date"]:
        df[col] = pd.to_datetime(df[col], format="%m/%d/%Y")
    df["Quantity"] = df["Quantity"].astype(int)

    # Trim whitespace in every text column.
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    df[text_cols] = df[text_cols].apply(lambda s: s.str.strip())

    # Missing postal codes (all Burlington, VT).
    missing_zip = df["Postal Code"].isna()
    log.append(f"Filled {missing_zip.sum()} missing postal codes (Burlington, VT -> 05401)")
    df.loc[missing_zip, "Postal Code"] = BURLINGTON_VT_ZIP
    df["Postal Code"] = df["Postal Code"].astype(int).astype(str).str.zfill(5)

    # Exact duplicate order lines (ignoring the surrogate Row ID).
    dupes = df.drop(columns="Row ID").duplicated()
    log.append(f"Removed {dupes.sum()} duplicate order line(s)")
    df = df[~dupes]

    # Sanity checks: shipping never precedes ordering, discounts within 0-80%.
    assert (df["Ship Date"] >= df["Order Date"]).all()
    assert df["Discount"].between(0, 0.8).all()
    assert (df["Sales"] > 0).all() and (df["Quantity"] > 0).all()

    # Feature engineering.
    df["Returned"] = df["Order ID"].isin(returns["Order ID"])
    df = df.merge(people, on="Region", how="left")
    df["Year"] = df["Order Date"].dt.year
    df["Quarter"] = df["Order Date"].dt.quarter
    df["Month"] = df["Order Date"].dt.month
    df["Order Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    df["Weekday"] = df["Order Date"].dt.day_name()
    df["Days to Ship"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df["Profit Margin"] = df["Profit"] / df["Sales"]
    df["Unit Price"] = df["Sales"] / df["Quantity"] / (1 - df["Discount"])
    df["Discount Band"] = pd.cut(
        df["Discount"], bins=[-0.01, 0, 0.2, 0.4, 0.8],
        labels=["No discount", "1-20%", "21-40%", "41-80%"],
    )
    df["Loss Making"] = df["Profit"] < 0
    log.append(f"Clean table: {len(df):,} rows x {df.shape[1]} columns")
    return df.reset_index(drop=True)


def run(raw_path=RAW_PATH, out_dir=OUT_DIR):
    raw = load_raw(raw_path)
    orders, people, returns = split_tables(raw)
    log = [f"Raw file: {len(raw):,} rows ({len(orders):,} order lines, "
           f"{len(people)} manager rows, {len(returns)} returned orders)"]
    clean = clean_orders(orders, returns, people, log)

    out_dir.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out_dir / "superstore_clean.csv", index=False, date_format="%Y-%m-%d")
    people.to_csv(out_dir / "regional_managers.csv", index=False)
    returns.to_csv(out_dir / "returns.csv", index=False)
    return clean, people, returns, log


if __name__ == "__main__":
    *_, log = run()
    print("\n".join(log))
