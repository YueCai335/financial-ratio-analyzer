# Financial Ratio Analyzer

Enter the key figures from a company's annual report and get eight core financial ratios, plotted as multi-year trends and side-by-side comparisons across companies.

FastAPI + SQLite backend, single-file Chart.js frontend. Built to practise the full loop — data in, calculation, presentation — on a domain I already know from the CFA Program.

*[中文说明见 README.zh.md](README.zh.md)*

## Running it

```bash
cd backend
.venv/bin/python seed.py                           # load sample data (drops and rebuilds)
.venv/bin/python -m uvicorn app.main:app --reload  # start
```

Open http://127.0.0.1:8000 — the backend serves the frontend, so there is no second server to start.
Auto-generated API docs are at http://127.0.0.1:8000/docs.

Tests:

```bash
cd backend && .venv/bin/python -m pytest test_ratios.py -v
```

## The eight ratios

| Ratio | Formula | What it tells you |
|---|---|---|
| Gross margin | (revenue − COGS) / revenue | Pricing power and cost structure |
| Net margin | net income / revenue | What actually reaches the bottom line |
| ROE | net income / total equity | Return on shareholders' capital |
| ROA | net income / total assets | Asset efficiency, ignoring leverage |
| Current ratio | current assets / current liabilities | Short-term solvency |
| Quick ratio | (current assets − inventory) / current liabilities | Short-term solvency once the least liquid asset is removed |
| Debt-to-assets | total liabilities / total assets | How much of the business is financed by debt |
| Equity multiplier | total assets / total equity | Leverage |

Two accounting identities are asserted in the test suite, so a mistyped formula fails the build rather than quietly returning a plausible number:

- `ROE = ROA × equity multiplier` (DuPont)
- `equity multiplier = 1 / (1 − debt-to-assets)`

## Layout

```
backend/
  app/
    database.py   SQLite connection, Session, Base
    models.py     two tables: Company / FinancialStatement
    schemas.py    Pydantic request and response shapes
    ratios.py     the eight ratios as pure functions (no database import)
    health.py     rule-based health thresholds (hard-coded and explainable)
    main.py       FastAPI routes, also serves the frontend
  seed.py         sample data
  test_ratios.py  tests for the calculations
frontend/
  index.html      single-file frontend, charts via Chart.js
```

## Design decisions

**Why SQLite instead of PostgreSQL.** One file, no Docker, no separate database service to run. This project holds a few dozen rows and has exactly one user, so none of PostgreSQL's strengths apply. The cost is weak concurrent writes and looser type checking — neither matters here.

**Why amounts are Float, not Numeric.** Floats carry rounding error (`0.1 + 0.2 != 0.3`), which disqualifies them for anything that books money. Here they are only divided into ratios and drawn on charts, so the error lands somewhere past the twelfth decimal place and changes no conclusion. The point is knowing the trap exists and judging that it is harmless in this context.

**Why `ratios.py` never imports the database.** Plain numbers in, plain numbers out. The calculation layer can therefore be tested without a database (the suite runs in about 0.02s) and would survive swapping the storage engine. All translation between ORM objects and plain dictionaries happens in one function, `_to_fields()` in `main.py`.

**Why an undefined ratio returns None, not 0.** "Cannot be computed" and "equals zero" are different facts. A company with zero equity has no ROE — it does not have an ROE of 0. Returning None, and rendering it as "—", avoids stating something false.

**Why the health check is rules, not a model.** Every warning traces back to a specific number crossing a specific documented threshold, so it can be explained and argued with. A model here would be less useful and less honest.

## Known limitations

- **Health thresholds ignore industry.** A current ratio below 1 is normal in retail — stretching supplier terms *is* the business model — and a warning sign in manufacturing. The rigorous version compares against an industry median, which is out of scope for this MVP.
- **Fiscal years are not aligned.** Apple's fiscal year ends in September, Microsoft's in June, Walmart's in January. The same `fiscal_year` value does not cover the same economic period, which matters when comparing across companies.
- **Sample data has not been line-by-line verified.** The figures in `seed.py` were taken from each company's 10-K but not individually reconciled. They exist to demonstrate the calculations and charts, not to support analysis.
- **Deliberately excluded:** live price APIs, any forecasting or investment advice, and user accounts.
