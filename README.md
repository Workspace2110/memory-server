# MCP Memory Server

跨 Claude 客戶端的持久記憶 MCP Server。支援語意搜尋，讓 Claude Code、Claude Chat、Claude Cowork 共用同一份記憶。

## 架構

```
Claude Code ─────┐
Claude Chat ─────┼──► stdio / HTTP+SSE ──► FastMCP Server ──► Qdrant
Claude Cowork ───┘                                           (向量搜尋)
```

**Embedding model：** `BAAI/bge-small-en-v1.5`（via fastembed，首次啟動自動下載 ~130MB）

---

## 目錄結構

```
memory-server/
├── mcp-server/
│   ├── main.py          # FastMCP entrypoint（6 個 tools）
│   ├── db.py            # Qdrant CRUD + 語意搜尋
│   ├── models.py        # Pydantic Memory model
│   ├── pyproject.toml
│   └── Dockerfile
├── data/
│   └── qdrant/          # Qdrant 資料 volume（git ignored）
├── docker-compose.yml
├── claude_mcp_config.json
├── PLAN.md
└── README.md
```

---

## 快速 Setup

### 前置需求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker + Docker Compose

### 1. 啟動 Qdrant

```bash
docker compose up qdrant -d
```

Qdrant dashboard：http://localhost:6333/dashboard

### 2. 安裝依賴

```bash
cd mcp-server
uv sync
```

### 3. 啟動 MCP Server（stdio mode）

```bash
uv run python main.py
```

首次啟動會下載 fastembed 模型（約 130MB），之後會 cache 在 `~/.cache/fastembed`。

### 4. 設定 Claude Code

編輯 `~/.claude/claude_desktop_config.json`，參考 `claude_mcp_config.json` 選對應平台的區塊貼入。

**Windows（WSL）：**
```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/workspace-linux/_project/personal/memory-server/mcp-server",
        "run", "python", "main.py"
      ],
      "env": { "QDRANT_URL": "http://localhost:6333" }
    }
  }
}
```

**macOS：**（將 `<PROJECT_ROOT>` 換成實際路徑）
```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": [
        "--directory", "<PROJECT_ROOT>/mcp-server",
        "run", "python", "main.py"
      ],
      "env": { "QDRANT_URL": "http://localhost:6333" }
    }
  }
}
```

---

## MCP Tools

| Tool | 說明 |
|---|---|
| `save_memory` | 儲存一筆記憶（content, type, tags） |
| `search_memories` | 語意搜尋（可篩選 type） |
| `get_memory` | 用 ID 取得單筆記憶 |
| `update_memory` | 更新記憶內容（會重新 embed） |
| `delete_memory` | 刪除記憶 |
| `list_memory_types` | 列出目前使用中的 type |

**Memory types：** `user` / `feedback` / `project` / `reference` / `general`

---

## 環境轉移

### 備份資料

Qdrant 資料全在 `./data/qdrant/`，直接打包即可：

```bash
# 備份
tar -czf memory-backup-$(date +%Y%m%d).tar.gz data/qdrant/

# 還原
tar -xzf memory-backup-YYYYMMDD.tar.gz
```

### 搬到新機器

```bash
# 舊機器
tar -czf memory-backup.tar.gz data/qdrant/
# 傳到新機器（scp / rsync / 隨身碟皆可）

# 新機器
git clone <this-repo>
tar -xzf memory-backup.tar.gz   # 解壓到 data/qdrant/
docker compose up qdrant -d
cd mcp-server && uv sync
```

fastembed 模型 cache 路徑：`~/.cache/fastembed`
（可選擇一起備份，省去重新下載時間）

### 環境變數

| 變數 | 預設值 | 說明 |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant 連線位址 |

---

## Phase 2：遠端存取（開發中）

Claude Chat / Cowork 需要 HTTP/SSE transport。完成後設定方式會補充在這裡。
