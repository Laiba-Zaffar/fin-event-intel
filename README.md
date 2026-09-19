# Financial News Event Intelligence Engine

Real-time pipeline that ingests financial news, extracts companies/tickers,
classifies market-moving event types, and serves predictions with
production-grade latency.

## Roadmap

- [x] M0 — repo scaffold
- [x] M1 — RSS news ingestion → SQLite
- [ ] M2 — NER (companies/tickers)
- [ ] M3 — event classification (zero-shot → fine-tuned FinBERT)
- [ ] M4 — FastAPI serving + latency benchmarks
- [ ] M5 — streaming layer (Redis Streams)
- [ ] M6 — portfolio polish

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
