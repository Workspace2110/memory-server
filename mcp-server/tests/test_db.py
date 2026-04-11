import pytest
import db


def test_save_and_get():
    m = db.save_memory("Tom uses uv for Python", "user", ["python", "tooling"])
    assert m.id
    assert m.content == "Tom uses uv for Python"
    assert m.type == "user"
    assert m.tags == ["python", "tooling"]

    fetched = db.get_memory(m.id)
    assert fetched is not None
    assert fetched.id == m.id
    assert fetched.content == m.content


def test_get_nonexistent():
    result = db.get_memory("00000000-0000-0000-0000-000000000000")
    assert result is None


def test_search_memories():
    db.save_memory("prefers dark mode UI", "feedback", ["ui"])
    db.save_memory("uses Docker for local dev", "project", ["docker"])

    results = db.search_memories("dark mode interface preference")
    assert len(results) >= 1
    assert any("dark mode" in r.content for r in results)


def test_search_with_type_filter():
    db.save_memory("likes uv over pip", "feedback", [])
    db.save_memory("project uses FastAPI", "project", [])

    results = db.search_memories("python tooling", type="feedback")
    assert all(r.type == "feedback" for r in results)


def test_update_memory():
    m = db.save_memory("original content", "general", [])
    updated = db.update_memory(m.id, "updated content")

    assert updated is not None
    assert updated.content == "updated content"
    assert updated.id == m.id
    assert updated.updated_at > m.updated_at


def test_update_nonexistent():
    result = db.update_memory("00000000-0000-0000-0000-000000000000", "x")
    assert result is None


def test_delete_memory():
    m = db.save_memory("to be deleted", "general", [])
    assert db.delete_memory(m.id) is True
    assert db.get_memory(m.id) is None


def test_delete_nonexistent():
    # 刪不存在的 ID 不應該 raise，回傳 False 或 True 均可（Qdrant 行為）
    result = db.delete_memory("00000000-0000-0000-0000-000000000000")
    assert isinstance(result, bool)


def test_list_memory_types():
    db.save_memory("user info", "user", [])
    db.save_memory("project context", "project", [])
    db.save_memory("some feedback", "feedback", [])

    types = db.list_memory_types()
    assert "user" in types
    assert "project" in types
    assert "feedback" in types
    assert types == sorted(types)  # 確認有排序


def test_list_memory_types_empty():
    types = db.list_memory_types()
    assert types == []
