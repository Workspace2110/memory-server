import os
import pytest

os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ["QDRANT_COLLECTION"] = "memories_test"

import db
from qdrant_client.models import Filter, FilterSelector


@pytest.fixture(autouse=True)
def clean_collection():
    """每個測試前確保 collection 存在且是空的。"""
    db.init_db()
    if db.client.collection_exists(db.COLLECTION):
        db.client.delete(
            collection_name=db.COLLECTION,
            points_selector=FilterSelector(filter=Filter()),
        )
    yield
