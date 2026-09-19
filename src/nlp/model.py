import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

MODEL_NAME = "valhalla/distilbart-mnli-12-3"


def build_classifier(quantized: bool = True):
    if not quantized:
        return pipeline("zero-shot-classification", model=MODEL_NAME)

    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    quantized_model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
    return pipeline("zero-shot-classification", model=quantized_model, tokenizer=tokenizer)
