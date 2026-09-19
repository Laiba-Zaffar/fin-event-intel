# Financial News Event Intelligence Engine

Real-time pipeline that ingests financial news, extracts companies/tickers,
classifies market-moving event types, and serves predictions with
production-grade latency.

## Roadmap

- [x] M0 — repo scaffold
- [x] M1 — RSS news ingestion → SQLite
- [x] M2 — NER (companies/tickers)
- [ ] M3 — event classification (zero-shot → fine-tuned FinBERT)
- [ ] M4 — FastAPI serving + latency benchmarks
- [ ] M5 — streaming layer (Redis Streams)
- [ ] M6 — portfolio polish

## Known limitations (M2)

- Ticker resolution is scoped to S&P 500 constituents only — foreign/small-cap
  names (e.g. BYD, CATL) correctly return no ticker rather than a wrong one.
- `en_core_web_sm` occasionally misdraws entity boundaries on headline-style
  text (e.g. absorbing trailing words like "Stock Underperforming"), and
  matching raw ticker symbols directly (e.g. "AMD") introduces rare false
  positives on short, word-like tickers (e.g. "COO" as the job title, not
  Cooper Companies). Acceptable for a v1 baseline; revisit if it affects M3
  classification quality.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python -m src.ingest.fetch_news
```

Pulls the configured RSS feeds once and stores new articles in
`data/raw/news.db` (deduped by link).

```bash
python -m spacy download en_core_web_sm   # one-time
python -m src.reference.fetch_sp500       # one-time, builds ticker lookup
python -m src.nlp.extract_entities
```

Runs NER over unprocessed articles, resolves company mentions to tickers
where possible, and stores results in the `entities` table.
