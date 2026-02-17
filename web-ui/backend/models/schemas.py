from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SummaryMetadata(BaseModel):
    """Metadata extracted from a summary file"""
    filename: str
    title: str
    file_path: str
    modified_date: datetime
    preview: str  # First 200 chars of content
    category: Optional[str] = None  # Folder category (tech, science, business, culture, general)


class SummaryDetail(BaseModel):
    """Full summary content"""
    filename: str
    title: str
    content: str  # Full markdown content
    modified_date: datetime
    category: Optional[str] = None  # Folder category (tech, science, business, culture, general)


class SummaryListResponse(BaseModel):
    """Response for listing summaries"""
    summaries: List[SummaryMetadata]
    total: int


class ChatMessage(BaseModel):
    """A single chat message"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request for chat endpoint"""
    message: str
    conversation_id: Optional[str] = None


class SummarizeRequest(BaseModel):
    """Request for summarization endpoint"""
    youtube_url: str


class SummarizeResponse(BaseModel):
    """Response from summarization endpoint"""
    status: str
    message: str
    summary_path: Optional[str] = None
    category: Optional[str] = None
