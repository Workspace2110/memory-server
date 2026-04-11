# MCP Memory Server — 開發計畫

## 目標

建立一個 MCP Memory Server，讓以下三個 Claude 客戶端共用同一份持久記憶：

- **Claude Code** (CLI / IDE extension)
- **Claude Chat** (claude.ai)
- **Claude Cowork**

---

## 架構

```
Claude Chat ─────┐
Claude Cowork ───┼──► HTTP/SSE (MCP Protocol) ──► Memory Server ──► SQLite
Claude Code ─────┘                                      │
                                                   (Phase 3)
                                                      Qdrant
                                                  (語意搜尋)
```

**Transport：** HTTP Streamable（MCP 新標準，相容所有客戶端）
**認證：** API Key（header `Authorization: Bearer <key>`）
**部署：** Docker Compose

---

## 技術選型

| 層 | 選擇 |
|---|---|
| Runtime | Python 3.12 |
| MCP Framework | `fastmcp` |
| Storage | Qdrant（向量 + payload，取代 SQLite） |
| Embedding | fastembed（`BAAI/bge-small-en-v1.5`，內建於 qdrant-client） |
| 容器化 | Docker + Docker Compose |
| 遠端存取 | Cloudflare Tunnel 或直接 expose port |

---

## MCP Tools 規格

| Tool | 參數 | 回傳 |
|---|---|---|
| `save_memory` | `content: str, type: str, tags: list[str]` | `memory_id: str` |
| `search_memories` | `query: str, type?: str, limit?: int` | `Memory[]` |
| `get_memory` | `memory_id: str` | `Memory` |
| `update_memory` | `memory_id: str, content: str` | `ok` |
| `delete_memory` | `memory_id: str` | `ok` |
| `list_memory_types` | — | `string[]` |

**Memory 物件結構：**
```json
{
  "id": "uuid",
  "content": "記憶內容",
  "type": "user | feedback | project | reference",
  "tags": ["tag1", "tag2"],
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

---

## 開發階段

### Phase 1 — 基礎可運作版（Claude Code 用）

- [x] 建立 Python 專案結構（`mcp-server/`）
- [x] 用 Qdrant + fastembed 實作 CRUD 與語意搜尋
- [x] 用 `fastmcp` 實作 6 個 MCP tools（stdio transport）
- [x] docker-compose 加入 Qdrant service
- [ ] 測試：Claude Code 設定並呼叫 tools

### Phase 2 — 遠端服務（Chat + Cowork）

- [x] 加 HTTP Streamable transport（`MCP_TRANSPORT=http` 切換）
- [x] 加 API Key 驗證 middleware（`MCP_API_KEY` 環境變數）
- [x] 設定 Claude Chat / Cowork 的 MCP config（`claude_mcp_config.json`）
- [ ] 用 Cloudflare Tunnel 或 expose port 開放遠端存取（依部署環境決定）

---

## 專案目錄結構（目標）

```
memory-server/
├── mcp-server/
│   ├── main.py          # FastMCP server entrypoint
│   ├── db.py            # SQLite CRUD
│   ├── models.py        # Pydantic models
│   ├── tools/
│   │   ├── save.py
│   │   ├── search.py
│   │   └── ...
│   ├── requirements.txt
│   └── Dockerfile
├── data/                # SQLite DB volume mount
├── docker-compose.yml
├── claude_mcp_config.json   # 給各客戶端的 MCP 設定範例
└── PLAN.md
```

---

## 目前進度

- [x] 規劃架構與技術選型
- [ ] Phase 1 開發中
