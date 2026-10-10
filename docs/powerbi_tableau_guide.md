# Building the dashboard in Power BI or Tableau

The interactive dashboard in `dashboard/index.html` runs in any browser. If your submission needs a
`.pbix` (Power BI) or a Tableau Public workbook, follow one of the guides below. Both use the cleaned file
`data/processed/superstore_clean.csv`, so no cleaning is needed in the BI tool. Expect 30 to 45 minutes.

After you build it, save a screenshot as `images/powerbi_dashboard.png` (or `tableau_dashboard.png`)
and put the `.pbix` file in `powerbi/`, or the Tableau Public link in the README.

---

## Option A: Power BI Desktop (Windows, free)

### 1. Load the data
1. **Home > Get data > Text/CSV**, choose `data/processed/superstore_clean.csv`, then **Transform Data**.
2. In Power Query check the types: `Order Date`, `Ship Date`, `Order Month` = Date; `Sales`, `Profit`,
   `Discount`, `Profit Margin`, `Unit Price` = Decimal; `Quantity`, `Year`, `Month`, `Days to Ship` = Whole
   number; `Postal Code` = Text; `Returned`, `Loss Making` = True/False. **Close & Apply**.
3. Rename the table to `Sales`.

### 2. Add a date table (Modeling > New table)
```DAX
Calendar =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2015, 1, 1 ), DATE ( 2018, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month No", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "Year-Month", FORMAT ( [Date], "YYYY-MM" ),
    "Quarter", "Q" & QUARTER ( [Date] )
)
```
Mark it as a date table (**Table tools > Mark as date table**, column `Date`), sort `Month` by `Month No`,
and create a relationship `Calendar[Date]` 1 to * `Sales[Order Date]`.

### 3. Measures (Modeling > New measure)
```DAX
Total Revenue = SUM ( Sales[Sales] )
Total Profit = SUM ( Sales[Profit] )
Profit Margin = DIVIDE ( [Total Profit], [Total Revenue] )
Total Orders = DISTINCTCOUNT ( Sales[Order ID] )
Total Customers = DISTINCTCOUNT ( Sales[Customer ID] )
Units Sold = SUM ( Sales[Quantity] )
Avg Order Value = DIVIDE ( [Total Revenue], [Total Orders] )
Return Rate =
DIVIDE (
    CALCULATE ( DISTINCTCOUNT ( Sales[Order ID] ), Sales[Returned] = TRUE () ),
    [Total Orders]
)
Revenue PY = CALCULATE ( [Total Revenue], SAMEPERIODLASTYEAR ( 'Calendar'[Date] ) )
Revenue YoY % = DIVIDE ( [Total Revenue] - [Revenue PY], [Revenue PY] )
Profit PY = CALCULATE ( [Total Profit], SAMEPERIODLASTYEAR ( 'Calendar'[Date] ) )
Profit YoY % = DIVIDE ( [Total Profit] - [Profit PY], [Profit PY] )
Revenue Running Total =
CALCULATE ( [Total Revenue], DATESYTD ( 'Calendar'[Date] ) )
```
Format `Profit Margin`, `Return Rate` and the YoY measures as percentages; revenue and profit as currency
with 0 decimals.

### 4. Build the report page (16:9 canvas)

| Visual | Fields | Notes |
|---|---|---|
| 4 slicers, top row | `Calendar[Year]`, `Sales[Region]`, `Sales[Category]`, `Sales[Segment]` | Style: Dropdown |
| 6 Card visuals | Total Revenue, Total Profit, Profit Margin, Total Orders, Avg Order Value, Return Rate | Add Revenue YoY % as a reference label on the revenue card |
| Line chart | X `Calendar[Year-Month]`, Y Total Revenue and Total Profit | Revenue blue `#2A78D6`, profit orange `#EB6834` |
| Clustered bar chart | Y `Region`, X Total Revenue and Total Profit | Add Profit Margin to tooltips |
| Matrix | Rows `Region`, Columns `Category`, Values Profit Margin | **Conditional formatting > Background color**, diverging: red `#E34948` (min), grey (0), blue `#2A78D6` (max) |
| Bar chart | Y `Sub-Category`, X Total Profit, sorted ascending | Conditional color by rule: < 0 red, >= 0 blue |
| Bar chart | Y `State`, X Total Revenue | **Filters > Top N = 10** by Total Revenue |
| Filled map (optional) | Location `State`, Color saturation Total Profit | Diverging red/blue |
| Table | `Product Name`, Total Revenue, Total Profit, Profit Margin | Top N = 10 by revenue |
| Column chart | X `Discount Band`, Y Profit Margin | Sort: No discount, 1-20%, 21-40%, 41-80% |
| Column chart | X `Calendar[Month]`, Y Total Revenue | Seasonality |
| Donut or bar | `Segment`, Total Revenue | |

Optional second page "Customers": a table of `Customer Name`, Total Orders, Total Revenue, Total Profit
(Top N 10), and a column chart of orders per customer. You can also import
`data/processed/customer_rfm.csv` and show revenue by `RFM segment`.

### 5. Polish and save
* **View > Themes**: pick a light theme, then set the page background to `#F4F5F7`.
* Turn on **Edit interactions** so clicking a region filters every visual (this is the default).
* Add a text box with the 3 to 4 headline insights from the report.
* **File > Save as** `powerbi/Superstore_Sales_Dashboard.pbix`. To share online, **Publish** to the
  Power BI service (needs a work or school account) or export to PDF (**File > Export > PDF**).

---

## Option B: Tableau Public (Windows or Mac, free)

1. Download Tableau Public Desktop and **Connect > Text file >** `data/processed/superstore_clean.csv`.
2. On the data source page check that `Order Date` is a Date, `Postal Code` is a String and `State` has the
   geographic role **State/Province** (click the type icon to change it).
3. Create calculated fields (**Analysis > Create Calculated Field**):
   ```
   Profit Margin      SUM([Profit]) / SUM([Sales])
   Orders             COUNTD([Order ID])
   Customers          COUNTD([Customer ID])
   Avg Order Value    SUM([Sales]) / COUNTD([Order ID])
   Return Rate        COUNTD(IF [Returned] THEN [Order ID] END) / COUNTD([Order ID])
   Revenue YoY %      (ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)) / ABS(LOOKUP(ZN(SUM([Sales])), -1))
   ```
4. Build one worksheet per chart:
   * **KPI**: text table with SUM(Sales), SUM(Profit), Profit Margin, Orders, Avg Order Value, Return Rate.
   * **Trend**: Columns `MONTH(Order Date)` (continuous), Rows SUM(Sales) and SUM(Profit), dual lines on one
     shared axis (use Measure Values, not a dual axis).
   * **Region**: Rows Region, Columns SUM(Sales), Color by Profit Margin (diverging red-blue, centre 0).
   * **Map**: double-click State, Color SUM(Profit), diverging red-blue palette.
   * **Sub-category**: Rows Sub-Category, Columns SUM(Profit), sort ascending, Color SUM(Profit) diverging.
   * **Top products**: Rows Product Name, Columns SUM(Sales), Top 10 filter by SUM(Sales).
   * **Discount**: Columns Discount Band, Rows Profit Margin.
   * **Segment**: Columns Segment, Rows SUM(Sales), Label Profit Margin.
5. **Dashboard > New Dashboard** (size: Automatic or 1400 x 1000). Drag the sheets in, add Region,
   Category, Segment and Year filters and set each to **Apply to Worksheets > All using this data source**.
   Use **Dashboard > Actions > Add Action > Filter** so clicking a region or state filters the rest.
6. **File > Save to Tableau Public**. Copy the public URL into the README under "Live dashboard".

---

## Expected numbers (to check your build)

| Metric | All years |
|---|---|
| Revenue | $2,296,919 |
| Profit | $286,409 |
| Profit margin | 12.5% |
| Orders | 5,009 |
| Customers | 793 |
| Average order value | $459 |
| Return rate (orders) | 5.9% |
| 2018 revenue | $733,215 (+20.4% vs 2017) |
