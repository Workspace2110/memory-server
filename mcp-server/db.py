import os
import threading
import uuid
from datetime import datetime, timezone

from qdrant_client import QdrantClient, models

from models import Memory, MemoryType

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "memories")
EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
VECTOR_SIZE = 1024

# Ensure fastembed uses a persistent cache directory, not /tmp.
# Respect explicit override via env var; otherwise default to ~/.cache/fastembed.
if "FASTEMBED_CACHE_PATH" not in os.environ:
    os.environ["FASTEMBED_CACHE_PATH"] = os.path.join(
        os.path.expanduser("~"), ".cache", "fastembed"
    )

client = QdrantClient(url=QDRANT_URL)

# Per-ID write locks: prevent concurrent update/delete race conditions on the same memory.
# _write_locks_mutex guards the dictionary itself.
_write_locks: dict[str, threading.Lock] = {}
_write_locks_mutex = threading.Lock()

# Global embed lock: fastembed model inference is not thread-safe;
# serialise all calls that embed text (upsert, query_points).
_embed_lock = threading.Lock()


def _get_write_lock(memory_id: str) -> threading.Lock:
    with _write_locks_mutex:
        if memory_id not in _write_locks:
            _write_locks[memory_id] = threading.Lock()
        return _write_locks[memory_id]


def _validate_embedding_model() -> None:
    """Run a test embedding to ensure the model is downloaded and functional.

    This catches the case where the cache was wiped (e.g., /tmp cleared on reboot)
    and forces a re-download at startup rather than failing on the first real request.
    """
    try:
        client.query_points(
            collection_name=COLLECTION,
            query=models.Document(text="startup validation probe", model=EMBEDDING_MODEL),
            limit=1,
        )
    except Exception as e:
        raise RuntimeError(
            f"Embedding model validation failed. Model: {EMBEDDING_MODEL}, "
            f"Cache path: {os.environ.get('FASTEMBED_CACHE_PATH', '(default)')}. "
            f"Original error: {e}"
        ) from e


def init_db() -> None:
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )
    _validate_embedding_model()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _point_to_memory(point) -> Memory:
    p = point.payload
    return Memory(
        id=str(point.id),
        content=p.get("content", ""),
        type=p.get("type", "general"),
        tags=p.get("tags", []),
        created_at=datetime.fromisoformat(p["created_at"]),
        updated_at=datetime.fromisoformat(p["updated_at"]),
    )


# --- CRUD ---

def save_memory(content: str, type: MemoryType, tags: list[str]) -> Memory:
    memory_id = str(uuid.uuid4())
    now = _now()
    with _embed_lock:
        client.upsert(
            collection_name=COLLECTION,
            points=[
                models.PointStruct(
                    id=memory_id,
                    vector=models.Document(text=content, model=EMBEDDING_MODEL),
                    payload={"content": content, "type": type, "tags": tags,
                             "created_at": now, "updated_at": now},
                )
            ],
        )
    return Memory(
        id=memory_id, content=content, type=type, tags=tags,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


def get_memory(memory_id: str) -> Memory | None:
    results = client.retrieve(
        collection_name=COLLECTION,
        ids=[memory_id],
        with_payload=True,
    )
    return _point_to_memory(results[0]) if results else None


def search_memories(query: str, type: MemoryType | None = None, limit: int = 20) -> list[Memory]:
    query_filter = None
    if type:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="type", match=models.MatchValue(value=type))]
        )
    with _embed_lock:
        results = client.query_points(
            collection_name=COLLECTION,
            query=models.Document(text=query, model=EMBEDDING_MODEL),
            query_filter=query_filter,
            limit=limit,
        )
    return [_point_to_memory(p) for p in results.points]


def update_memory(memory_id: str, content: str) -> Memory | None:
    with _get_write_lock(memory_id):
        existing = get_memory(memory_id)
        if not existing:
            return None
        now = _now()
        with _embed_lock:
            client.upsert(
                collection_name=COLLECTION,
                points=[
                    models.PointStruct(
                        id=memory_id,
                        vector=models.Document(text=content, model=EMBEDDING_MODEL),
                        payload={"content": content, "type": existing.type, "tags": existing.tags,
                                 "created_at": existing.created_at.isoformat(), "updated_at": now},
                    )
                ],
            )
        return Memory(
            id=memory_id, content=content, type=existing.type, tags=existing.tags,
            created_at=existing.created_at,
            updated_at=datetime.fromisoformat(now),
        )


def delete_memory(memory_id: str) -> bool:
    with _get_write_lock(memory_id):
        result = client.delete(
            collection_name=COLLECTION,
            points_selector=models.PointIdsList(points=[memory_id]),
        )
        return result.status.value == "completed"


def list_memory_types() -> list[str]:
    types: set[str] = set()
    offset = None
    while True:
        records, offset = client.scroll(
            collection_name=COLLECTION,
            with_payload=["type"],
            limit=100,
            offset=offset,
        )
        for r in records:
            if r.payload and "type" in r.payload:
                types.add(r.payload["type"])
        if offset is None:
            break
    return sorted(types)
