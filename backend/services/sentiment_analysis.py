import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")
model = AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased-finetuned-sst-2-english")

def analyze_text(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        scores = torch.softmax(outputs.logits[0], dim=-1)
        label = model.config.id2label[scores.argmax().item()]
        confidence = scores.max().item()
    return label, confidence

def calculate_risk(sentiment_percentages, sentiment_confidences=None):
    negative_percent = sentiment_percentages['negative']
    risk_level = negative_percent * 0.8
    
    if sentiment_confidences and 'negative' in sentiment_confidences:
        avg_negative_confidence = sum(sentiment_confidences['negative']) / len(sentiment_confidences['negative'])
        risk_level += avg_negative_confidence * 0.2

    return round(risk_level, 2)
