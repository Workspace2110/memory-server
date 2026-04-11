from fastmcp import FastMCP
from typing import Annotated
from pydantic import Field

import db
from models import Memory, MemoryType

db.init_db()  # 建立 Qdrant collection（若不存在）

mcp = FastMCP(
    name="memory-server",
    instructions=(
        "A persistent memory store. Use this to save and retrieve memories across sessions. "
        "Memory types: 'user' (about the user), 'feedback' (preferences/corrections), "
        "'project' (ongoing work context), 'reference' (pointers to external resources), "
        "'general' (anything else)."
    ),
)


@mcp.tool()
def save_memory(
    content: Annotated[str, Field(description="The memory content to store")],
    type: Annotated[MemoryType, Field(description="Memory type: user | feedback | project | reference | general")] = "general",
    tags: Annotated[list[str], Field(description="Optional tags for categorisation")] = [],
) -> dict:
    """Save a new memory."""
    memory = db.save_memory(content, type, tags)
    return {"id": memory.id, "type": memory.type, "created_at": memory.created_at.isoformat()}


@mcp.tool()
def search_memories(
    query: Annotated[str, Field(description="Search query — matches content and tags")],
    type: Annotated[MemoryType | None, Field(description="Filter by memory type (optional)")] = None,
    limit: Annotated[int, Field(description="Max results to return", ge=1, le=100)] = 20,
) -> list[dict]:
    """Search memories by content or tags."""
    memories = db.search_memories(query, type, limit)
    return [_memory_to_dict(m) for m in memories]


@mcp.tool()
def get_memory(
    memory_id: Annotated[str, Field(description="The memory UUID to retrieve")],
) -> dict | None:
    """Get a single memory by ID."""
    memory = db.get_memory(memory_id)
    return _memory_to_dict(memory) if memory else None


@mcp.tool()
def update_memory(
    memory_id: Annotated[str, Field(description="The memory UUID to update")],
    content: Annotated[str, Field(description="New content to replace the existing memory")],
) -> dict | None:
    """Update the content of an existing memory."""
    memory = db.update_memory(memory_id, content)
    return _memory_to_dict(memory) if memory else None


@mcp.tool()
def delete_memory(
    memory_id: Annotated[str, Field(description="The memory UUID to delete")],
) -> dict:
    """Delete a memory by ID."""
    deleted = db.delete_memory(memory_id)
    return {"deleted": deleted, "id": memory_id}


@mcp.tool()
def list_memory_types() -> list[str]:
    """List all memory types currently in use."""
    return db.list_memory_types()


def _memory_to_dict(m: Memory) -> dict:
    return {
        "id": m.id,
        "content": m.content,
        "type": m.type,
        "tags": m.tags,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
    }


if __name__ == "__main__":
    mcp.run()
