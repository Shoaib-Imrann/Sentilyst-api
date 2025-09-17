from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import email_routes
from routes import sentiment_routes
from routes import news_routes
from routes import company_routes
from middleware.auth_middleware import AuthMiddleware
import os
# import psutil
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CLIENT_URL = os.getenv("CLIENT_URL")

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:5173"],
    allow_origins=[CLIENT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)

app.include_router(email_routes.router, prefix="/api")
app.include_router(sentiment_routes.router, prefix="/api")
app.include_router(news_routes.router, prefix="/api")
app.include_router(company_routes.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Backend up and ready"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
