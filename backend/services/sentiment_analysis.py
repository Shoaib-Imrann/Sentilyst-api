import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

# Cache model locally to speed up deployments
MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
CACHE_DIR = os.getenv("HF_HOME", "./model_cache")

# Load tokenizer and model at module level (once)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
model.eval()

def warmup_model():
    """Warm up model with dummy inference to avoid cold start"""
    analyze_batch(["test"])

def analyze_text(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        scores = torch.softmax(outputs.logits[0], dim=-1)
        label = model.config.id2label[scores.argmax().item()]
        confidence = scores.max().item()
    return label, confidence

def analyze_batch(texts, batch_size=32):
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        inputs = tokenizer(batch, return_tensors="pt", truncation=True, padding=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
            scores = torch.softmax(outputs.logits, dim=-1)
            for j in range(len(batch)):
                label = model.config.id2label[scores[j].argmax().item()]
                confidence = scores[j].max().item()
                results.append((label, confidence))
    return results

def calculate_risk(sentiment_percentages, sentiment_confidences=None):
    negative_percent = sentiment_percentages['negative']
    risk_level = negative_percent * 0.8
    
    if sentiment_confidences and 'negative' in sentiment_confidences and len(sentiment_confidences['negative']) > 0:
        avg_negative_confidence = sum(sentiment_confidences['negative']) / len(sentiment_confidences['negative'])
        risk_level += avg_negative_confidence * 0.2

    return round(risk_level, 2)
