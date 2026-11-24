"""Create/update the faculty Qdrant collection from faculty.json."""
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.config import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("faculty_ingestion")
BATCH_SIZE = 48
NAMESPACE = uuid.UUID("cc86d47c-20dd-5da3-8c1a-e9a4db605c43")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key}: {as_text(item)}" for key, item in value.items() if item is not None)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(as_text(item) for item in value if item is not None)
    return str(value).strip()


def faculty_text(record: dict) -> str:
    fields = (
        "standard_name", "name", "department", "designation", "research_areas",
        "expertise", "publications", "bio", "biography", "keywords", "aliases",
    )
    return "\n".join(f"{field.replace('_', ' ').title()}: {as_text(record.get(field))}"
                     for field in fields if as_text(record.get(field)))


def retry(operation, label: str):
    for attempt in range(4):
        try:
            return operation()
        except Exception:
            if attempt == 3:
                raise
            delay = 0.5 * (2 ** attempt)
            logger.warning("%s failed; retrying in %.1fs", label, delay)
            time.sleep(delay)


def main() -> None:
    if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
        raise SystemExit("Set QDRANT_URL and QDRANT_API_KEY in the root or backend .env file.")
    data = json.loads(settings.FACULTY_FILE.read_text(encoding="utf-8"))
    faculties = data.get("faculties", [])
    if not faculties:
        raise SystemExit(f"No faculty records found in {settings.FACULTY_FILE}.")

    model = SentenceTransformer(settings.NAME_EMBEDDING_MODEL)
    vector_size = model.get_sentence_embedding_dimension()
    if not vector_size:
        raise SystemExit(f"Could not determine vector size for {settings.NAME_EMBEDDING_MODEL}.")
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)

    try:
        exists = client.collection_exists(settings.QDRANT_COLLECTION)
    except Exception as exc:
        raise SystemExit(f"Could not reach Qdrant Cloud: {exc}") from exc
    if exists:
        info = client.get_collection(settings.QDRANT_COLLECTION)
        configured = info.config.params.vectors
        if isinstance(configured, dict):
            sizes = {item.size for item in configured.values()}
        else:
            sizes = {configured.size}
        if sizes != {vector_size}:
            raise SystemExit(
                f"Collection '{settings.QDRANT_COLLECTION}' has vector size {sorted(sizes)}; "
                f"model '{settings.NAME_EMBEDDING_MODEL}' requires {vector_size}. No data was changed."
            )
    else:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        logger.info("Created collection '%s' with %d-dimensional cosine vectors.", settings.QDRANT_COLLECTION, vector_size)

    indexed = set()
    for record in faculties:
        indexed.update(key for key in ("department", "designation") if record.get(key) is not None)
    for field in sorted(indexed):
        retry(lambda field=field: client.create_payload_index(
            collection_name=settings.QDRANT_COLLECTION,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        ), f"Creating {field} payload index")

    for start in range(0, len(faculties), BATCH_SIZE):
        batch = faculties[start:start + BATCH_SIZE]
        texts = [faculty_text(record) for record in batch]
        vectors = retry(lambda: model.encode(texts, convert_to_numpy=True, show_progress_bar=False), "Embedding batch")
        points = []
        for record, vector in zip(batch, vectors):
            stable_key = record.get("id") or record.get("email") or record.get("standard_name") or record.get("name")
            if not stable_key:
                raise SystemExit("A faculty record has no id, email, standard_name, or name for a stable point ID.")
            points.append(models.PointStruct(
                id=str(uuid.uuid5(NAMESPACE, str(stable_key).strip().casefold())),
                vector=vector.tolist(),
                payload=record,
            ))
        retry(lambda: client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points, wait=True), "Upserting batch")
        logger.info("Upserted %d/%d faculty records.", min(start + len(batch), len(faculties)), len(faculties))

    count = client.count(collection_name=settings.QDRANT_COLLECTION, exact=True).count
    logger.info("Faculty records in JSON: %d; points in Qdrant: %d.", len(faculties), count)
    if count != len(faculties):
        raise SystemExit("Point count does not match faculty.json; inspect the collection for stale records.")


if __name__ == "__main__":
    main()
