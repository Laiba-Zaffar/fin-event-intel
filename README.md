# Financial News Event Intelligence Engine

Real-time pipeline that ingests financial news, extracts companies/tickers,
classifies market-moving event types, and serves predictions with
production-grade latency.

## Roadmap

- [x] M0 — repo scaffold
- [x] M1 — RSS news ingestion → SQLite
- [x] M2 — NER (companies/tickers)
- [x] M3 — event classification (zero-shot baseline)
- [ ] M4 — FastAPI serving + latency optimization
- [ ] M3b — fine-tune on labeled data (if zero-shot proves insufficient)
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
pip install torch --index-url https://download.pytorch.org/whl/cpu  # CPU-only build; skip default index or it pulls the CUDA build (multi-GB)
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

```bash
python -m src.nlp.classify_events
```

Zero-shot classifies each unclassified article into one of the labels in
`src/nlp/event_labels.py`, using `valhalla/distilbart-mnli-12-3`. Stores
label + confidence directly on the `articles` row.

## Known limitations (M3)

- CPU latency is currently ~5s mean per article (up to 14s) — nowhere near
  production real-time requirements. This is the explicit target for M4
  (batching, ONNX export, a smaller/distilled model, or GPU).
- ~40% of articles land in "other" — a lot of feed content (general macro
  explainers, policy news unrelated to a specific company) doesn't fit the
  event taxonomy at all, which is expected, not a bug.
- Confidence scores look informative on a quick eyeball (high-confidence
  picks are qualitatively correct, e.g. leadership changes; low-confidence
  picks are genuinely ambiguous headlines) but haven't been validated
  against real labels yet — that's what a hand-labeled eval set would give
  us, which ties into Project 2's calibration work later.
