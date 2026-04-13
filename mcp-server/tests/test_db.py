import threading

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


# --- Concurrency tests ---

def test_concurrent_updates_same_memory():
    """兩個 thread 同時 update 同一筆 memory，最終內容必須是其中一個，不能資料損毀。"""
    m = db.save_memory("initial content", "general", [])
    results = []
    errors = []

    def do_update(content):
        try:
            updated = db.update_memory(m.id, content)
            if updated:
                results.append(updated.content)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=do_update, args=("content from thread 1",))
    t2 = threading.Thread(target=do_update, args=("content from thread 2",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Exceptions during concurrent update: {errors}"
    assert len(results) == 2

    final = db.get_memory(m.id)
    assert final is not None
    assert final.content in ("content from thread 1", "content from thread 2")
    db.delete_memory(m.id)


def test_concurrent_update_and_delete():
    """一個 thread update、另一個 thread delete 同一筆 memory，不應出現例外或損毀狀態。"""
    m = db.save_memory("to be contested", "general", [])
    errors = []

    def do_update():
        try:
            db.update_memory(m.id, "updated by thread")
        except Exception as e:
            errors.append(e)

    def do_delete():
        try:
            db.delete_memory(m.id)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=do_update)
    t2 = threading.Thread(target=do_delete)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Exceptions during concurrent update+delete: {errors}"
    # 最終狀態：記憶存在或不存在都合法，但不能拋例外


def test_concurrent_saves_are_independent():
    """多個 thread 同時 save 不同 memory，全部應成功且互不影響。"""
    saved_ids = []
    errors = []
    lock = threading.Lock()

    def do_save(i):
        try:
            m = db.save_memory(f"concurrent save {i}", "general", [])
            with lock:
                saved_ids.append(m.id)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=do_save, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Exceptions during concurrent saves: {errors}"
    assert len(saved_ids) == 10
    assert len(set(saved_ids)) == 10  # 所有 ID 都不同

    for mid in saved_ids:
        db.delete_memory(mid)
