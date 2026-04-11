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

- [uv](https://docs.astral.sh/uv/)（macOS：`brew install uv`）
- Docker + Docker Compose（兩個平台都需要，Qdrant 跑在 Docker 裡）

### 1. 啟動 Qdrant（Windows / macOS 都需要）

```bash
docker compose up qdrant -d
```

Qdrant dashboard：http://localhost:6333/dashboard

### 2. 安裝依賴

```bash
cd mcp-server
uv sync
```

首次 `uv sync` 會根據 `pyproject.toml` 自動選 Python 版本。

### 3. 設定 Claude Code

編輯 `~/.claude/claude_desktop_config.json`，參考 `claude_mcp_config.json` 選對應平台的區塊貼入。

首次 Claude Code 啟動 MCP server 時會下載 fastembed 模型（約 130MB），之後 cache 在 `~/.cache/fastembed`。

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
| `MCP_TRANSPORT` | `stdio` | `stdio`（Claude Code）或 `http`（遠端） |
| `MCP_API_KEY` | —（無驗證）| HTTP mode 的 API key |
| `HOST` | `0.0.0.0` | HTTP mode 的監聽 host |
| `PORT` | `8000` | HTTP mode 的監聽 port |

---

## Maintenance

### 更新 Python 套件

```bash
cd mcp-server

# 檢查哪些套件有新版
uv tree --outdated

# 升級全部套件並更新 uv.lock
uv sync --upgrade

# 只升級特定套件
uv add "fastmcp>=x.y.z"
```

升級後務必跑一次功能測試確認正常：

```bash
QDRANT_URL=http://localhost:6333 uv run python -c "
import db; db.init_db()
m = db.save_memory('test', 'general', [])
assert db.get_memory(m.id)
db.delete_memory(m.id)
print('OK')
"
```

### 更新 Python 版本

1. 修改 `mcp-server/pyproject.toml`：
   ```toml
   requires-python = ">=3.13"  # 改成目標版本
   ```
2. 修改 `mcp-server/Dockerfile`：
   ```dockerfile
   FROM python:3.13-slim  # 對應版本
   ```
3. 重新 sync 並重建 Docker image：
   ```bash
   cd mcp-server && uv sync
   docker compose build memory-server
   ```

### 更新 Qdrant Docker image

```bash
# 拉最新 image
docker compose pull qdrant

# 重啟（資料不受影響，存在 ./data/qdrant/）
docker compose up qdrant -d
```

> 升級前建議先備份：`tar -czf memory-backup-$(date +%Y%m%d).tar.gz data/qdrant/`

### 更新 uv 本身

```bash
# macOS（brew 安裝）
brew upgrade uv

# Windows WSL（非 brew）
uv self update
```

---

## Phase 2：遠端存取（Claude Chat / Cowork）

### 1. 建立 `.env`

```bash
cp .env.example .env
# 編輯 .env，填入 MCP_API_KEY
```

### 2. 啟動完整服務

```bash
docker compose up -d
```

memory-server 會在 port 8000 以 HTTP Streamable transport 跑起來。

### 3. 開放遠端存取

選一種方式：

**Cloudflare Tunnel（推薦，免費）：**
```bash
cloudflared tunnel --url http://localhost:8000
```

**直接 expose port：** 確保防火牆開放 8000，或掛在 reverse proxy 後面。

### 4. 設定 Claude Chat / Cowork

在 MCP 設定介面填入：
- URL：`http://<YOUR_HOST>:8000/mcp`
- Header：`Authorization: Bearer <YOUR_MCP_API_KEY>`

參考 `claude_mcp_config.json` 的 `claude_chat_or_cowork_remote` 區塊。
