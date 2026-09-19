import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.nlp.event_labels import EVENT_LABELS
from src.nlp.model import build_classifier

ml_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loaded once here, not per-request - reloading a ~1.3GB model on every
    # call is the single most common way to accidentally 100x your latency.
    ml_state["classifier"] = build_classifier(quantized=False)
    yield
    ml_state.clear()


app = FastAPI(title="Financial Event Classifier", lifespan=lifespan)


class ClassifyRequest(BaseModel):
    title: str
    summary: str | None = None


class ClassifyResult(BaseModel):
    label: str
    confidence: float
    latency_ms: float


class BatchClassifyRequest(BaseModel):
    articles: list[ClassifyRequest]


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": "classifier" in ml_state}


@app.post("/classify", response_model=ClassifyResult)
def classify(req: ClassifyRequest):
    text = f"{req.title} {req.summary or ''}".strip()
    start = time.perf_counter()
    result = ml_state["classifier"](text, candidate_labels=EVENT_LABELS)
    latency_ms = (time.perf_counter() - start) * 1000
    return ClassifyResult(label=result["labels"][0], confidence=result["scores"][0], latency_ms=latency_ms)


@app.post("/classify_batch", response_model=list[ClassifyResult])
def classify_batch(req: BatchClassifyRequest):
    texts = [f"{a.title} {a.summary or ''}".strip() for a in req.articles]
    start = time.perf_counter()
    results = ml_state["classifier"](texts, candidate_labels=EVENT_LABELS, batch_size=8)
    total_ms = (time.perf_counter() - start) * 1000
    if isinstance(results, dict):
        results = [results]
    per_item_ms = total_ms / len(texts)
    return [
        ClassifyResult(label=r["labels"][0], confidence=r["scores"][0], latency_ms=per_item_ms)
        for r in results
    ]
