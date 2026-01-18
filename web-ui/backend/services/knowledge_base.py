import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..config import settings
from ..models.schemas import SummaryMetadata, SummaryDetail


class KnowledgeBaseService:
    """Service for reading and searching the knowledge base"""

    def __init__(self):
        self.base_path = Path(settings.KNOWLEDGE_BASE_PATH)

    async def list_all(self) -> list[SummaryMetadata]:
        """List all markdown files in knowledge base"""
        summaries = []
        for file_path in self.base_path.glob("*.md"):
            meta = await self._extract_metadata(file_path)
            summaries.append(meta)
        # Sort by modified date, newest first
        return sorted(summaries, key=lambda x: x.modified_date, reverse=True)

    async def search(self, query: str) -> list[SummaryMetadata]:
        """Search summaries by title or content"""
        query_lower = query.lower()
        results = []
        for file_path in self.base_path.glob("*.md"):
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            # Search in filename and content
            if query_lower in file_path.stem.lower() or query_lower in content.lower():
                meta = await self._extract_metadata(file_path, content)
                results.append(meta)
        return sorted(results, key=lambda x: x.modified_date, reverse=True)

    async def get_by_filename(self, filename: str) -> Optional[SummaryDetail]:
        """Get full summary by filename"""
        # Security: prevent path traversal
        safe_filename = Path(filename).name
        file_path = self.base_path / safe_filename

        if not file_path.exists() or file_path.suffix != ".md":
            return None

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

        return SummaryDetail(
            filename=safe_filename,
            title=self._extract_title(content),
            content=content,
            modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
        )

    async def _extract_metadata(
        self, file_path: Path, content: Optional[str] = None
    ) -> SummaryMetadata:
        """Extract metadata from a summary file"""
        if content is None:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

        # Create preview from content
        preview_text = content[:200].replace("\n", " ").strip()
        if len(content) > 200:
            preview_text += "..."

        return SummaryMetadata(
            filename=file_path.name,
            title=self._extract_title(content),
            file_path=str(file_path),
            modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
            preview=preview_text,
        )

    def _extract_title(self, content: str) -> str:
        """Extract title from H1 heading"""
        lines = content.strip().split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled"


# Singleton instance
kb_service = KnowledgeBaseService()
