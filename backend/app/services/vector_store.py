"""Shared Qdrant connection and query embedding model."""
import logging
import time
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from ..core.config import settings

logger = logging.getLogger(__name__)


class FacultyVectorStore:
    def __init__(self) -> None:
        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            raise RuntimeError(
                "Qdrant is not configured. Set QDRANT_URL and QDRANT_API_KEY in .env."
            )
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        self.model = SentenceTransformer(settings.NAME_EMBEDDING_MODEL, local_files_only=True)

    def search(self, query: str, top_k: Optional[int] = None, query_filter: Any = None) -> List[Dict[str, Any]]:
        try:
            vector = self.model.encode([query], convert_to_numpy=True)[0].tolist()
            for attempt in range(3):
                try:
                    response = self.client.query_points(
                        collection_name=settings.QDRANT_COLLECTION,
                        query=vector,
                        query_filter=query_filter,
                        limit=top_k or settings.FACULTY_SEARCH_TOP_K,
                        with_payload=True,
                    )
                    points = response.points
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(0.5 * (2 ** attempt))
        except Exception as exc:
            message = str(exc).lower()
            if "not found" in message or "doesn't exist" in message:
                raise RuntimeError(
                    f"Qdrant collection '{settings.QDRANT_COLLECTION}' is unavailable; run scripts/ingest_faculty.py."
                ) from exc
            raise RuntimeError(f"Faculty search through Qdrant failed: {exc}") from exc

        if not points:
            raise RuntimeError(
                f"Qdrant collection '{settings.QDRANT_COLLECTION}' is empty; run scripts/ingest_faculty.py."
            )
        return [{"score": point.score, "payload": point.payload or {}, "id": point.id} for point in points]


vector_store = FacultyVectorStore()
