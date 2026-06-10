FROM python:3.11-slim

RUN groupadd -r appuser && useradd -r -g appuser -m appuser

WORKDIR /app
ENV HF_HOME=/home/appuser/.hf_cache

COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download model into appuser-owned cache (outside /app bind mount)
RUN mkdir -p /home/appuser/.hf_cache && python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english', cache_dir='/home/appuser/.hf_cache'); \
    AutoModelForSequenceClassification.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english', cache_dir='/home/appuser/.hf_cache')" \
    && chown -R appuser:appuser /home/appuser/.hf_cache

COPY . .
RUN chmod +x start.sh && chown -R appuser:appuser /app

USER appuser

CMD ["./start.sh"]
