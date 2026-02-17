from fastapi import APIRouter, HTTPException, Query, Body

from ..services.knowledge_base import kb_service
from ..models.schemas import SummaryListResponse, SummaryDetail

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.get("", response_model=SummaryListResponse)
async def list_summaries():
    """List all summaries in the knowledge base"""
    summaries = await kb_service.list_all()
    return SummaryListResponse(summaries=summaries, total=len(summaries))


@router.get("/search", response_model=SummaryListResponse)
async def search_summaries(q: str = Query(..., min_length=2)):
    """Search summaries by title or content"""
    results = await kb_service.search(q)
    return SummaryListResponse(summaries=results, total=len(results))


@router.get("/{filename}/highlights")
async def get_highlights(filename: str):
    """Get saved highlights for a summary"""
    highlights = await kb_service.get_highlights(filename)
    return {"highlights": highlights}


@router.put("/{filename}/highlights")
async def save_highlights(filename: str, highlights: list = Body(..., embed=True)):
    """Save highlights for a summary"""
    success = await kb_service.save_highlights(filename, highlights)
    if not success:
        raise HTTPException(status_code=404, detail="Summary not found")
    return {"status": "saved", "count": len(highlights)}


@router.get("/{filename}", response_model=SummaryDetail)
async def get_summary(filename: str):
    """Get full content of a specific summary"""
    summary = await kb_service.get_by_filename(filename)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary
