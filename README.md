# Financial News Event Intelligence Engine

Real-time pipeline that ingests financial news, extracts companies/tickers,
classifies market-moving event types, and serves predictions with
production-grade latency.

## Roadmap

- [x] M0 — repo scaffold
- [x] M1 — RSS news ingestion → SQLite
- [x] M2 — NER (companies/tickers)
- [x] M3 — event classification (zero-shot baseline)
- [x] M4a — latency optimization (quantization + batching)
- [ ] M4b — FastAPI serving layer + request-level p50/p99 benchmarks
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

- ~40% of articles land in "other" — a lot of feed content (general macro
  explainers, policy news unrelated to a specific company) doesn't fit the
  event taxonomy at all, which is expected, not a bug.
- Confidence scores look informative on a quick eyeball (high-confidence
  picks are qualitatively correct, e.g. leadership changes; low-confidence
  picks are genuinely ambiguous headlines) but haven't been validated
  against real labels yet — that's what a hand-labeled eval set would give
  us, which ties into Project 2's calibration work later.

## M4a — latency optimization

Diagnosis first: zero-shot NLI classification runs one forward pass *per
candidate label* (it's testing "does this text entail label X" for each
label separately), so cost scales with the number of labels, not O(1) per
article. With 10 labels that's a real multiplier, and it's the main reason
the M3 baseline was slow - not model size alone.

Benchmarked four configs on a fixed sample of real articles
(`python -m src.nlp.benchmark_classifier --mode <name>`):

| Config              | Per-article latency | vs. baseline |
|---------------------|---------------------|---------------|
| baseline (fp32)      | ~10.2s mean         | 1x            |
| batched only         | ~7.5s               | ~1.4x         |
| quantized only       | ~4.8s mean          | looked ~2.1x, see below |
| quantized + batched  | ~3.75s              | looked ~2.7x, see below |

**Quantization was reverted after a correctness check caught a real
regression.** `torch.quantization.quantize_dynamic` (INT8 on Linear
layers) looked like the bigger win on latency alone, but before shipping
it I ran a direct fp32-vs-quantized comparison on a known headline
("Warren Buffett steps down..."):

```
fp32:      leadership change            0.833
quantized: analyst rating or price target  0.137
```

Wrong label, confidence collapsed to near-random. Dynamic INT8
quantization apparently doesn't tolerate this BART-based encoder-decoder
model well (unlike plain BERT/DistilBERT encoders, where it's usually
safe) - likely the cross-attention layers are more precision-sensitive.
A batch of 48 articles classified with the quantized model before this
was caught confirmed it: average confidence 0.167 vs. 0.426 for
everything classified with fp32 - a clear sign of degenerate output, not
just "harder headlines." Those 48 rows were reset and reclassified with
fp32.

**Lesson kept for the interview, not just the README:** a latency win
that isn't checked against a correctness baseline isn't a win, it's a
liability, and this project is explicitly about a domain (financial
predictions) where that trade only goes one way. `classify_events.py`
now runs fp32 + batching only (`batch_size=8`), which is the safe,
verified part of the speedup.

On the full 48-article production batch, fp32 + batching landed at
**~1.1s/article** - notably better than the 4-article benchmark's 7.5s,
because batching benefits scale with batch size, and real pipelines
process articles in bulk anyway, not one at a time.

Caveats:
- Numbers were measured on a memory-constrained dev laptop under
  sustained load earlier in the session - some runs likely saw CPU
  thermal throttling. Production latency numbers need dedicated hardware.
- Still not real-time (sub-second per article in the worst case). Future
  options: fewer candidate labels, a smaller distilled model, ONNX
  export (which has more mature quantization support for seq2seq models
  than raw PyTorch dynamic quantization), or a fine-tuned single-pass
  classifier (M3b) that doesn't pay the per-label NLI cost at all.
