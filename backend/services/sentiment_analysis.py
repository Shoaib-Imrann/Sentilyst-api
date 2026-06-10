import os
import requests
import logging

logger = logging.getLogger("sentilyst.sentiment")

MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
HF_TOKEN = os.getenv("HF_TOKEN")
_PLACEHOLDER_TOKENS = {"", "your_huggingface_token_here"}

tokenizer = None
model = None
USE_API = bool((HF_TOKEN or "").strip() not in _PLACEHOLDER_TOKENS)


def _model_cache_dir():
    return os.getenv("HF_HOME")


def _load_kwargs():
    cache_dir = _model_cache_dir()
    return {"cache_dir": cache_dir} if cache_dir else {}


def _clear_model_cache() -> None:
    import shutil

    cache_dir = _model_cache_dir()
    if not cache_dir:
        return

    cache_path = os.path.join(cache_dir, f"models--{MODEL_NAME.replace('/', '--')}")
    if os.path.isdir(cache_path):
        shutil.rmtree(cache_path)
        logger.warning("Removed incomplete model cache at %s", cache_path)


def _load_local_model():
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    load_kwargs = _load_kwargs()
    if load_kwargs:
        os.makedirs(load_kwargs["cache_dir"], exist_ok=True)

    logger.info("Loading local DistilBERT model (downloads on first run if not cached)...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, **load_kwargs)

    try:
        local_model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME, **load_kwargs
        )
    except OSError as exc:
        if "pytorch_model.bin" not in str(exc) and "TensorFlow" not in str(exc):
            raise
        logger.warning("Incomplete model cache detected, re-downloading PyTorch weights...")
        _clear_model_cache()
        local_model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME, force_download=True, **load_kwargs
        )

    local_model.eval()
    return tokenizer, local_model


if USE_API:
    logger.info("HF_TOKEN found. Attempting to use HuggingFace API for sentiment inference (will fallback to local if unreachable).")
else:
    import torch

    tokenizer, model = _load_local_model()
    logger.info("Local DistilBERT model ready.")


def _load_local_model_lazy():
    global tokenizer, model
    if tokenizer is None or model is None:
        import torch
        tokenizer, model = _load_local_model()
        logger.info("Local DistilBERT model loaded dynamically on fallback/demand.")


def _hf_api_query(payload, retries=3):
    headers = {"Authorization": f"Bearer {HF_TOKEN.strip()}"}
    for attempt in range(retries):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            if attempt == retries - 1:
                logger.error("HF API failed after %s attempts: %s", retries, exc)
                raise
            logger.warning("HF API attempt %s failed, retrying...", attempt + 1)
    return None


def warmup_model():
    if USE_API:
        logger.info("API mode: no warmup needed")
    else:
        analyze_batch(["test"])
        logger.info("Local model warmed up")


def analyze_text(text):
    global USE_API
    if USE_API:
        try:
            result = _hf_api_query({"inputs": text})
            if not result or not isinstance(result, list):
                raise ValueError("Invalid API response")
            top = max(result[0], key=lambda x: x["score"])
            return top["label"], top["score"]
        except Exception as exc:
            logger.warning("HF API call failed. Falling back to local model: %s", exc)
            USE_API = False
            _load_local_model_lazy()

    import torch
    _load_local_model_lazy()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        scores = torch.softmax(outputs.logits[0], dim=-1)
        label = model.config.id2label[scores.argmax().item()]
        confidence = scores.max().item()
    return label, confidence


def analyze_batch(texts, batch_size=32):
    global USE_API
    if USE_API:
        try:
            results = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                raw = _hf_api_query({"inputs": batch})
                if not raw:
                    raise ValueError("API batch analysis failed")
                for item in raw:
                    top = max(item, key=lambda x: x["score"])
                    results.append((top["label"], top["score"]))
            return results
        except Exception as exc:
            logger.warning("HF API call failed. Falling back to local model: %s", exc)
            USE_API = False
            _load_local_model_lazy()

    import torch
    _load_local_model_lazy()
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        inputs = tokenizer(
            batch, return_tensors="pt", truncation=True, padding=True, max_length=512
        )
        with torch.no_grad():
            outputs = model(**inputs)
            scores = torch.softmax(outputs.logits, dim=-1)
            for j in range(len(batch)):
                label = model.config.id2label[scores[j].argmax().item()]
                confidence = scores[j].max().item()
                results.append((label, confidence))
    return results

