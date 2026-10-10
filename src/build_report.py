"""Generate the Business Insights Report (PDF) from the cleaned data and notebook charts."""
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "images"
OUT = ROOT / "reports" / "Business_Insights_Report.pdf"

INK, INK2, MUTED = colors.HexColor("#121417"), colors.HexColor("#4c5058"), colors.HexColor("#858a93")
BLUE, RED, GRID, WASH = (colors.HexColor("#1d5fb8"), colors.HexColor("#b42828"),
                         colors.HexColor("#e3e5e8"), colors.HexColor("#eef3fb"))

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27,
                    textColor=INK, alignment=TA_LEFT, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                    textColor=INK, spaceBefore=10, spaceAfter=5)
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.6, leading=13.8,
                      textColor=INK, spaceAfter=5)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.4, leading=11, textColor=MUTED)
EYEBROW = ParagraphStyle("Eyebrow", parent=SMALL, fontName="Courier", fontSize=8.5, textColor=MUTED)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=12, bulletIndent=2)

money = lambda v: f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"
pct = lambda v: f"{v:.1%}"


def table(rows, widths, num_cols_from=1, highlight_neg=True):
    t = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.6), ("FONT", (0, 1), (-1, -1), "Helvetica", 8.6),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK2), ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("ALIGN", (num_cols_from, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK2), ("LINEBELOW", (0, 1), (-1, -1), 0.4, GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if highlight_neg:
        for r, row in enumerate(rows[1:], start=1):
            for c, cell in enumerate(row):
                if isinstance(cell, str) and cell.startswith("-"):
                    style.append(("TEXTCOLOR", (c, r), (c, r), RED))
    t.setStyle(TableStyle(style))
    return t


def chart(name, width=160 * mm):
    path = IMG / name
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(str(path)).getSize()
    return Image(str(path), width=width, height=width * h / w)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, "Superstore Sales Performance · Business Insights Report")
    canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    df = pd.read_csv(ROOT / "data" / "processed" / "superstore_clean.csv", parse_dates=["Order Date"])
    S, P = df["Sales"].sum(), df["Profit"].sum()
    orders, customers = df["Order ID"].nunique(), df["Customer ID"].nunique()
    returned = df.loc[df["Returned"], "Order ID"].nunique()
    yr = df.groupby("Year").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                Orders=("Order ID", "nunique"), Customers=("Customer ID", "nunique"))
    yr["Margin"] = yr["Profit"] / yr["Revenue"]
    yr["Growth"] = yr["Revenue"].pct_change()
    cagr = (yr.loc[2018, "Revenue"] / yr.loc[2015, "Revenue"]) ** (1 / 3) - 1

    reg = df.groupby("Region").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                   Orders=("Order ID", "nunique")).sort_values("Revenue", ascending=False)
    reg["Margin"] = reg["Profit"] / reg["Revenue"]
    cat = df.groupby("Category").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                     Units=("Quantity", "sum")).sort_values("Revenue", ascending=False)
    cat["Margin"] = cat["Profit"] / cat["Revenue"]
    seg = df.groupby("Segment").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                    Customers=("Customer ID", "nunique"), Orders=("Order ID", "nunique"))
    seg["Margin"] = seg["Profit"] / seg["Revenue"]
    prod = df.groupby("Product Name").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
    disc = df.groupby("Discount Band", observed=True).agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                                                          Lines=("Sales", "size"))
    disc = disc.reindex(["No discount", "1-20%", "21-40%", "41-80%"])
    disc["Margin"] = disc["Profit"] / disc["Revenue"]
    deep = disc.loc[["21-40%", "41-80%"]].sum()
    cust = df.groupby("Customer ID").agg(Orders=("Order ID", "nunique"), Revenue=("Sales", "sum"))
    top20c = cust["Revenue"].nlargest(int(len(cust) * .2)).sum() / cust["Revenue"].sum()
    season = df.groupby("Month")["Sales"].sum() / S

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm,
                            title="Superstore Sales Performance: Business Insights Report",
                            author="Shivam")
    s = []
    s += [Paragraph("SAMPLE SUPERSTORE · US RETAIL · JAN 2015 TO DEC 2018", EYEBROW),
          Paragraph("Sales Performance: Business Insights Report", H1),
          Paragraph(f"Analysis of {len(df):,} order lines from {orders:,} orders placed by {customers} customers "
                    "across 49 US states. Covers revenue trends, product performance, customer behaviour and "
                    "regional results, with recommendations.", BODY),
          Spacer(1, 4)]

    kpi = [["Revenue", "Profit", "Margin", "Orders", "Customers", "Avg order", "Return rate"],
           [f"${S/1e6:.2f}M", f"${P/1e3:.0f}K", pct(P / S), f"{orders:,}", f"{customers}",
            money(S / orders), pct(returned / orders)]]
    kt = Table(kpi, colWidths=[24.3 * mm] * 7)
    kt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica", 7.8), ("TEXTCOLOR", (0, 0), (-1, 0), INK2),
        ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", 13), ("TEXTCOLOR", (0, 1), (-1, 1), INK),
        ("BACKGROUND", (0, 0), (-1, -1), WASH), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 7), ("LINEAFTER", (0, 0), (-2, -1), 1.5, colors.white),
    ]))
    s += [kt, Spacer(1, 8)]

    s.append(Paragraph("Executive summary", H2))
    summary = [
        f"<b>Growth is strong.</b> Revenue rose from {money(yr.loc[2015,'Revenue'])} in 2015 to "
        f"{money(yr.loc[2018,'Revenue'])} in 2018, a {cagr:.1%} compound annual growth rate. Profit grew faster, "
        f"from {money(yr.loc[2015,'Profit'])} to {money(yr.loc[2018,'Profit'])}.",
        f"<b>Discounting is the biggest profit leak.</b> Lines discounted more than 20% brought in "
        f"{money(deep['Revenue'])} of revenue and lost {money(-deep['Profit'])}. Undiscounted lines earn a "
        f"{pct(disc.loc['No discount','Margin'])} margin.",
        f"<b>Furniture is a volume trap.</b> It is {pct(cat.loc['Furniture','Revenue']/S)} of revenue but only "
        f"{pct(cat.loc['Furniture','Profit']/P)} of profit. Tables and Bookcases lose money outright.",
        f"<b>Central underperforms.</b> Central's margin is {pct(reg.loc['Central','Margin'])} against "
        f"{pct(reg.loc['West','Margin'])} in the West. Texas, Ohio, Pennsylvania and Illinois together lose $71K.",
        f"<b>Customers are loyal and concentrated.</b> {(cust['Orders']>1).mean():.0%} ordered more than once, "
        f"and the top 20% of customers produce {top20c:.0%} of revenue.",
        f"<b>Demand is seasonal.</b> September to December bring {season.loc[9:12].sum():.0%} of annual revenue.",
    ]
    s += [Paragraph(t, BULLET, bulletText="•") for t in summary]

    s.append(Paragraph("1. Revenue trends", H2))
    s.append(Paragraph(
        "Revenue dipped 2.8% in 2016, then grew 29.5% in 2017 and 20.4% in 2018. Margin improved from 10.2% "
        "in 2015 to about 13% in each later year. Orders rose every year, from 969 to 1,687, while the "
        "average order value fell from $499 to $435, so growth came from more orders rather than larger ones.", BODY))
    rows = [["Year", "Revenue", "Growth", "Profit", "Margin", "Orders", "Customers"]]
    for y, r in yr.iterrows():
        rows.append([str(y), money(r.Revenue), "–" if pd.isna(r.Growth) else f"{r.Growth:+.1%}",
                     money(r.Profit), pct(r.Margin), f"{int(r.Orders):,}", f"{int(r.Customers)}"])
    s += [table(rows, [20 * mm, 27 * mm, 22 * mm, 25 * mm, 22 * mm, 22 * mm, 22 * mm]), Spacer(1, 6),
          chart("monthly_trend.png"), chart("seasonality.png", 150 * mm)]

    s.append(PageBreak())
    s.append(Paragraph("2. Regional performance", H2))
    s.append(Paragraph(
        "The West and East generate 61% of revenue and 70% of profit. Central sells more than the South but "
        "earns less profit, because Central's Furniture loses money and its Binders and Appliances are sold at "
        "deep discounts. Texas is the third-largest state by revenue yet the largest loss-maker.", BODY))
    rows = [["Region", "Revenue", "Share", "Profit", "Margin", "Orders"]]
    for name, r in reg.iterrows():
        rows.append([name, money(r.Revenue), pct(r.Revenue / S), money(r.Profit), pct(r.Margin), f"{int(r.Orders):,}"])
    s += [table(rows, [30 * mm, 30 * mm, 22 * mm, 28 * mm, 22 * mm, 22 * mm]), Spacer(1, 6),
          chart("region.png", 150 * mm), chart("state_losses.png", 150 * mm)]

    s.append(PageBreak())
    s.append(Paragraph("3. Product performance", H2))
    s.append(Paragraph(
        "Technology is the largest and most profitable category. Office Supplies earns a similar margin on "
        "lower revenue. Furniture's 2.5% margin is the weak point. At sub-category level, Copiers, Phones and "
        "Accessories lead on profit; Tables, Bookcases and Supplies lose money. Revenue is concentrated: the "
        "top 20% of the 1,850 products generate 77% of revenue.", BODY))
    rows = [["Category", "Revenue", "Share", "Profit", "Profit share", "Margin"]]
    for name, r in cat.iterrows():
        rows.append([name, money(r.Revenue), pct(r.Revenue / S), money(r.Profit), pct(r.Profit / P), pct(r.Margin)])
    s += [table(rows, [34 * mm, 28 * mm, 22 * mm, 28 * mm, 26 * mm, 22 * mm]), Spacer(1, 6),
          chart("subcategory_profit.png", 150 * mm)]
    best = prod.nlargest(5, "Profit")
    worst = prod.nsmallest(5, "Profit")
    rows = [["Most profitable products", "Revenue", "Profit"]] + \
           [[n if len(n) <= 62 else n[:60] + "…", money(r.Revenue), money(r.Profit)] for n, r in best.iterrows()]
    rows2 = [["Biggest loss-making products", "Revenue", "Profit"]] + \
            [[n if len(n) <= 62 else n[:60] + "…", money(r.Revenue), money(r.Profit)] for n, r in worst.iterrows()]
    s += [KeepTogether([table(rows, [110 * mm, 30 * mm, 30 * mm]), Spacer(1, 6),
                        table(rows2, [110 * mm, 30 * mm, 30 * mm])])]

    s.append(PageBreak())
    s.append(Paragraph("4. Customer purchasing behaviour", H2))
    s.append(Paragraph(
        f"The {customers} customers placed a median of {cust['Orders'].median():.0f} orders each over four "
        "years. Consumers are half of revenue; Home Office customers are fewest but most profitable per "
        "dollar. An RFM (recency, frequency, monetary) segmentation in the notebook finds 176 Champions "
        "producing 35% of revenue, and 34 high-value customers who have not ordered in over a year.", BODY))
    rows = [["Segment", "Revenue", "Profit", "Margin", "Customers", "Avg order"]]
    for name, r in seg.iterrows():
        rows.append([name, money(r.Revenue), money(r.Profit), pct(r.Margin), f"{int(r.Customers)}",
                     money(r.Revenue / r.Orders)])
    s += [table(rows, [32 * mm, 28 * mm, 26 * mm, 22 * mm, 24 * mm, 24 * mm]), Spacer(1, 6),
          chart("order_frequency.png", 150 * mm)]

    s.append(Paragraph("5. Discounts and profitability", H2))
    s.append(Paragraph(
        "Discount level is the strongest single driver of profit in the data (correlation with line margin "
        "-0.86). Up to 20% off, lines stay profitable. Beyond that every band loses money, and at 41 to 80% "
        "off the business loses 77 cents for each dollar sold.", BODY))
    rows = [["Discount", "Order lines", "Revenue", "Profit", "Margin"]]
    for name, r in disc.iterrows():
        rows.append([name, f"{int(r.Lines):,}", money(r.Revenue), money(r.Profit), pct(r.Margin)])
    s += [table(rows, [34 * mm, 26 * mm, 32 * mm, 32 * mm, 24 * mm]), Spacer(1, 6),
          chart("discount_margin.png", 150 * mm)]

    s.append(PageBreak())
    s.append(Paragraph("6. Recommendations", H2))
    recs = [
        "<b>Cap discounts at 20%.</b> Require manager approval above it. Start with Binders, Machines, Tables "
        "and Appliances in Central and the East, where deep discounts lose the most. Bringing the deep-discount "
        f"lines to break-even alone would add about {money(-deep['Profit'])} of profit over four years.",
        "<b>Fix or prune Furniture.</b> Reprice Tables and Bookcases, bundle them with profitable accessories, "
        "or drop SKUs that lose money on every sale (for example the Cubify CubeX 3D printers and several "
        "conference tables).",
        "<b>Grow the profit engines.</b> Feature Copiers, Phones, Accessories, Paper and Labels in cross-sell "
        "and seasonal campaigns. They carry margins from 13% to 44%.",
        "<b>Turn around Central and the loss states.</b> Review pricing and promotion policy in Texas, Ohio, "
        "Pennsylvania and Illinois, and give Central's regional manager margin targets, not only revenue targets.",
        "<b>Protect the best customers.</b> Launch a loyalty tier for the top 20% of customers and a win-back "
        "offer for the 34 high-value customers who have lapsed.",
        "<b>Plan for the autumn peak.</b> Align inventory, staffing and marketing spend with September to "
        "December, which deliver over half of annual revenue.",
    ]
    s += [Paragraph(t, BULLET, bulletText=f"{i}.") for i, t in enumerate(recs, 1)]

    s.append(Paragraph("Method and data", H2))
    s.append(Paragraph(
        "Source: Tableau's public <i>Sample - Superstore</i> dataset (9,994 order lines, 21 columns). The raw "
        "CSV also contained the regional-manager and returns tables; these were split out. Cleaning removed one "
        "duplicate line, filled 11 missing postal codes (all Burlington, VT), parsed dates and added time, "
        "margin, discount-band and returned-order features. Analysis was done in Python (pandas) in "
        "<i>notebooks/sales_analysis.ipynb</i>; the interactive dashboard is in <i>dashboard/index.html</i>. "
        "Profit is as recorded in the dataset; returns are flagged but not netted out of revenue.", SMALL))

    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
