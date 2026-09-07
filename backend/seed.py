"""Loads a few companies' financial statement data into the database for
demo purposes.

Data source: each company's 10-K filings (SEC EDGAR, sec.gov/edgar), taken
from "Consolidated Statements of Operations" and "Consolidated Balance
Sheets".

Warning: these figures have not been verified line-by-line. They are only
meant to demonstrate the charts and calculation logic — do not use them for
actual investment analysis.

Units: millions of USD.
Fiscal year-end dates differ by company: Apple ends in late September,
Microsoft in late June, Walmart in late January. So the same fiscal_year
value doesn't cover exactly the same calendar period across companies —
worth keeping in mind for cross-company comparisons.

These three companies were chosen as a deliberate contrast set:
  Microsoft — software, very high gross margin, cash-rich
  Apple     — hardware, moderate gross margin, but equity is compressed by
              years of large buybacks, making ROE look extremely high
  Walmart   — retail, low gross margin, inventory-heavy, current ratio
              regularly below 1
Three very different business models, more interesting side by side on
the same chart.
"""

from app.database import Base, SessionLocal, engine
from app.models import Company, FinancialStatement

# Field order: revenue, cost of goods sold, operating income, net income,
#              total assets, total liabilities, total equity,
#              current assets, current liabilities, inventory
FIELDS = [
    "revenue",
    "cost_of_goods_sold",
    "operating_income",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "inventory",
]

DATA = [
    {
        "name": "Apple",
        "ticker": "AAPL",
        "industry": "Consumer Electronics",
        "years": {
            2024: [391035, 210352, 123216, 93736, 364980, 308030, 56950, 152987, 176392, 7286],
            2023: [383285, 214137, 114301, 96995, 352583, 290437, 62146, 143566, 145308, 6331],
            2022: [394328, 223546, 119437, 99803, 352755, 302083, 50672, 135405, 153982, 4946],
            2021: [365817, 212981, 108949, 94680, 351002, 287912, 63090, 134836, 125481, 6580],
            2020: [274515, 169559, 66288, 57411, 323888, 258549, 65339, 143713, 105392, 4061],
        },
    },
    {
        "name": "Microsoft",
        "ticker": "MSFT",
        "industry": "Software",
        "years": {
            2024: [245122, 74114, 109433, 88136, 512163, 243686, 268477, 159734, 125286, 1246],
            2023: [211915, 65863, 88523, 72361, 411976, 205753, 206223, 184257, 104149, 2500],
            2022: [198270, 62650, 83383, 72738, 364840, 198298, 166542, 169684, 95082, 3742],
            2021: [168088, 52232, 69916, 61271, 333779, 191791, 141988, 184406, 88657, 2636],
            2020: [143015, 46078, 52959, 44281, 301311, 183007, 118304, 181915, 72310, 1895],
        },
    },
    {
        "name": "Walmart",
        "ticker": "WMT",
        "industry": "Retail",
        "years": {
            2024: [648125, 490142, 27012, 15511, 252399, 168455, 83944, 76877, 92415, 54892],
            2023: [611289, 463721, 20428, 11680, 243197, 160502, 82695, 75655, 92198, 56576],
            2022: [572754, 429000, 25942, 13673, 244860, 153943, 91891, 81070, 87379, 56511],
        },
    },
]


def main():
    # Drop and rebuild first, so this script can be run repeatedly without
    # hitting the unique constraint
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for entry in DATA:
            company = Company(
                name=entry["name"],
                ticker=entry["ticker"],
                industry=entry["industry"],
            )
            db.add(company)
            db.flush()  # flush assigns an id without committing, so company.id is available below

            for year, values in entry["years"].items():
                db.add(
                    FinancialStatement(
                        company_id=company.id,
                        fiscal_year=year,
                        **dict(zip(FIELDS, values)),
                    )
                )
            print(f"  {entry['name']:<12} {len(entry['years'])} years")

        db.commit()
        print("\nData written to backend/financials.db")
    finally:
        db.close()


if __name__ == "__main__":
    main()
