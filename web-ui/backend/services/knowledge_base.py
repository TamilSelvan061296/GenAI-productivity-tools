import json
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..config import settings
from ..models.schemas import SummaryMetadata, SummaryDetail

VALID_CATEGORIES = {"tech", "science", "business", "culture", "general"}


class KnowledgeBaseService:
    """Service for reading and searching the knowledge base"""

    def __init__(self):
        self.base_path = Path(settings.KNOWLEDGE_BASE_PATH)

    async def list_all(self) -> list[SummaryMetadata]:
        """List all markdown files in knowledge base (including subfolders)"""
        summaries = []
        for file_path in self.base_path.glob("**/*.md"):
            meta = await self._extract_metadata(file_path)
            summaries.append(meta)
        # Sort by modified date, newest first
        return sorted(summaries, key=lambda x: x.modified_date, reverse=True)

    async def search(self, query: str) -> list[SummaryMetadata]:
        """Search summaries by title or content"""
        query_lower = query.lower()
        results = []
        for file_path in self.base_path.glob("**/*.md"):
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            # Search in filename and content
            if query_lower in file_path.stem.lower() or query_lower in content.lower():
                meta = await self._extract_metadata(file_path, content)
                results.append(meta)
        return sorted(results, key=lambda x: x.modified_date, reverse=True)

    async def get_by_filename(self, filename: str) -> Optional[SummaryDetail]:
        """Get full summary by filename (searches across all category subfolders)"""
        file_path = self._find_md_file(filename)
        if not file_path:
            return None

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

        category = self._get_category(file_path)
        return SummaryDetail(
            filename=file_path.name,
            title=self._extract_title(content),
            content=content,
            modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
            category=category,
        )

    def list_categories(self) -> list[str]:
        """Return available category folders"""
        categories = []
        for d in self.base_path.iterdir():
            if d.is_dir() and d.name in VALID_CATEGORIES:
                categories.append(d.name)
        return sorted(categories)

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

        category = self._get_category(file_path)

        return SummaryMetadata(
            filename=file_path.name,
            title=self._extract_title(content),
            file_path=str(file_path),
            modified_date=datetime.fromtimestamp(file_path.stat().st_mtime),
            preview=preview_text,
            category=category,
        )

    def _get_category(self, file_path: Path) -> Optional[str]:
        """Derive category from the file's parent folder name"""
        parent = file_path.parent.name
        if parent in VALID_CATEGORIES:
            return parent
        return None

    def _find_md_file(self, filename: str) -> Optional[Path]:
        """Find a markdown file by filename across root and category subfolders"""
        safe_filename = Path(filename).name
        candidates = [self.base_path / safe_filename]
        for category in VALID_CATEGORIES:
            candidates.append(self.base_path / category / safe_filename)
        for file_path in candidates:
            if file_path.exists() and file_path.suffix == ".md":
                return file_path
        return None

    def _highlights_path(self, md_path: Path) -> Path:
        """Get the highlights JSON path for a given markdown file"""
        return md_path.with_suffix(".highlights.json")

    async def get_highlights(self, filename: str) -> list[dict]:
        """Load highlights for a summary file"""
        md_path = self._find_md_file(filename)
        if not md_path:
            return []
        hl_path = self._highlights_path(md_path)
        if not hl_path.exists():
            return []
        async with aiofiles.open(hl_path, "r", encoding="utf-8") as f:
            data = await f.read()
        return json.loads(data)

    async def save_highlights(self, filename: str, highlights: list[dict]) -> bool:
        """Save highlights for a summary file"""
        md_path = self._find_md_file(filename)
        if not md_path:
            return False
        hl_path = self._highlights_path(md_path)
        if not highlights:
            # Remove file if no highlights
            if hl_path.exists():
                hl_path.unlink()
            return True
        async with aiofiles.open(hl_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(highlights, indent=2))
        return True

    def _extract_title(self, content: str) -> str:
        """Extract title from H1 heading"""
        lines = content.strip().split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled"


# Singleton instance
kb_service = KnowledgeBaseService()
