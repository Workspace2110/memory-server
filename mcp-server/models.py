from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

MemoryType = Literal["user", "feedback", "project", "reference", "general"]


class Memory(BaseModel):
    id: str
    content: str
    type: MemoryType
    tags: list[str]
    created_at: datetime
    updated_at: datetime
