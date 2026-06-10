# Sentilyst API

FastAPI backend for M&A news sentiment. Fetches headlines from Google News RSS and NewsAPI, classifies them with a pre-trained DistilBERT model. 

## Quick Start

```bash
cd backend
cp .env.template .env
docker compose up --build
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

No `model_cache` folder in the repo. Model weights are downloaded automatically when needed.

## Sentiment model modes

### Option A: Local model (default)

Leave `HF_TOKEN` unset in `.env`. On first run, DistilBERT (~250MB) downloads automatically.

- RAM: ~400–500MB
- No HuggingFace account required
- In Docker, weights are baked into the image under `/home/appuser/.hf_cache` (non-root, not in your project folder)

### Option B: HuggingFace API

Add to `.env`:

```env
HF_TOKEN=hf_your_token_here
```

Get a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

- RAM: ~50MB (no local model loaded)

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `HF_TOKEN` | No | If set, uses HuggingFace API instead of local model |
| `NEWSAPI_KEY` | Recommended | NewsAPI key for sentiment search and `/api/news/fetch-ma-news` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |

## Local Development (without Docker)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
cp .env.template .env
uvicorn main:app --reload
```

Without `HF_TOKEN`, the model downloads to your user cache (`~/.cache/huggingface`), not into the project.

## API Endpoint

### `POST /api/analyze`

```json
{ "query": "Microsoft acquiring Activision Blizzard" }
```

## Notes

- Sentiment uses DistilBERT — narrow ML inference, not generative AI
- No database or user accounts
- Docker build pre-downloads the model so first startup is faster in local mode
