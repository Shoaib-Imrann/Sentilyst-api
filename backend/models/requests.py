from pydantic import BaseModel, Field, validator
from typing import Optional

class SentimentAnalysisRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="Search query for sentiment analysis")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        cleaned = v.strip()
        if len(cleaned) < 1:
            raise ValueError('Query must contain at least 1 character')
        return cleaned

class NewsRequest(BaseModel):
    query: Optional[str] = Field(None, max_length=200, description="Optional search query filter")
    
    @validator('query')
    def validate_query(cls, v):
        if v is not None:
            cleaned = v.strip()
            if len(cleaned) == 0:
                return None
            return cleaned
        return v
