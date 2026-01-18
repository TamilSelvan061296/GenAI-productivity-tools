from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .routers import summaries, chat

app = FastAPI(
    title="GenAI Productivity Tools Dashboard",
    description="Web interface for YouTube summarization and chat",
    version="1.0.0",
)

# CORS middleware (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(summaries.router)
app.include_router(chat.router)


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


# Serve static frontend files (mount after API routes)
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
