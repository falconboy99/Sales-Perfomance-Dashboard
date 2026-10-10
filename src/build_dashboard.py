"""Build the interactive HTML dashboard from the cleaned dataset.

Writes two files:
  dashboard/index.html     standalone page, open it in any browser
  dashboard/fragment.html  same page without the <html>/<head> wrapper (for hosting
                           as a claude.ai Artifact, which supplies its own skeleton)
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "processed" / "superstore_clean.csv"
TEMPLATE = ROOT / "dashboard" / "template.html"


def encode(df):
    """Pack the order lines into compact arrays of dictionary indexes."""
    dims = {
        "region": "Region", "category": "Category", "sub": "Sub-Category",
        "segment": "Segment", "state": "State", "product": "Product Name",
        "customer": "Customer Name", "order": "Order ID", "ship": "Ship Mode",
    }
    dicts, codes = {}, {}
    for key, col in dims.items():
        cat = df[col].astype("category")
        dicts[key] = list(cat.cat.categories)
        codes[key] = cat.cat.codes
    # Product -> sub-category lookup, for the product table.
    sub_of_product = (df.groupby("Product Name")["Sub-Category"].first()
                      .reindex(dicts["product"]).map(dicts["sub"].index).tolist())
    dicts.pop("order")  # order ids only need to be distinct numbers

    month0 = pd.Period("2015-01", "M")
    month_idx = (df["Order Date"].dt.to_period("M") - month0).apply(lambda p: p.n)
    rows = [
        [int(m), int(r), int(c), int(s), int(g), int(st), int(p), int(cu), int(o),
         round(float(sa), 2), round(float(pr), 2), int(q), float(d), int(ret), int(sh)]
        for m, r, c, s, g, st, p, cu, o, sa, pr, q, d, ret, sh in zip(
            month_idx, codes["region"], codes["category"], codes["sub"],
            codes["segment"], codes["state"], codes["product"], codes["customer"],
            codes["order"], df["Sales"], df["Profit"], df["Quantity"],
            df["Discount"], df["Returned"].astype(int), codes["ship"])
    ]
    return {
        "fields": ["month", "region", "category", "sub", "segment", "state",
                   "product", "customer", "order", "sales", "profit", "qty",
                   "discount", "returned", "ship"],
        "dicts": dicts, "subOfProduct": sub_of_product,
        "startMonth": "2015-01", "rows": rows,
    }


def build():
    df = pd.read_csv(CLEAN, parse_dates=["Order Date", "Ship Date"])
    data = json.dumps(encode(df), separators=(",", ":"))
    page = TEMPLATE.read_text().replace("/*__DATA__*/null", data)
    out = ROOT / "dashboard"
    (out / "fragment.html").write_text(page)
    (out / "index.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "</head>\n<body>\n" + page + "\n</body>\n</html>\n"
    )
    print(f"Dashboard written ({len(page) / 1024:.0f} KB)")


if __name__ == "__main__":
    build()
