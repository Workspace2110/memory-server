# MCP Memory Server

跨 AI 工具的持久記憶 MCP Server，支援語意搜尋。讓 Claude Code、Cursor、VS Code Copilot、Codex CLI 等工具共用同一份記憶。

---

## 架構

```
Local agent  ────── stdio ───────┐
Remote agent ─── HTTP + API key ─┼──► FastMCP Server ──► Qdrant (語意向量搜尋)
Remote agent ─── HTTP + API key ─┘
```

- **Embedding：** `BAAI/bge-large-en-v1.5`（1024 維，via fastembed，首次啟動自動下載 ~550MB，cache 在 `~/.cache/fastembed`）
- **Storage：** Qdrant（Docker，資料存在 `./data/qdrant/`，git ignored）

---

## 目錄結構

```
memory-server/
├── mcp-server/
│   ├── main.py        # FastMCP server（6 tools，stdio / HTTP 切換）
│   ├── db.py          # Qdrant CRUD + 語意搜尋
│   ├── models.py      # Memory model
│   ├── pyproject.toml
│   └── Dockerfile
├── data/qdrant/       # Qdrant 資料（git ignored）
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 前置需求

| | macOS / WSL | Windows 原生 |
|---|---|---|
| **uv** | `brew install uv` | [官網安裝](https://docs.astral.sh/uv/) |
| **Docker Desktop** | [官網下載](https://www.docker.com/products/docker-desktop/) | 同左 |

---

## Setup

### 情境 A：本機（stdio）

AI 工具透過 stdio 直接啟動 MCP server。Qdrant 跑在 Docker，**memory-server 本身不用跑在 Docker**。

**步驟：**

```bash
# 1. 啟動 Qdrant
docker compose up qdrant -d

# 2. 安裝依賴
cd mcp-server && uv sync
```

然後依照使用的工具設定 MCP：

#### Claude Code（Desktop App）

設定 → **Edit Config**，在 `mcpServers` 加入：

```json
{
  "preferences": { "...": "..." },
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["--directory", "<PROJECT_ROOT>/mcp-server", "run", "python", "main.py"],
      "env": { "QDRANT_URL": "http://localhost:6333", "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

> Windows native 路徑用反斜線，例如 `D:\\Projects\\tools\\memory-server\\mcp-server`

#### Cursor

`~/.cursor/mcp.json`（全域）或 `.cursor/mcp.json`（專案）：

```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["--directory", "<PROJECT_ROOT>/mcp-server", "run", "python", "main.py"],
      "env": { "QDRANT_URL": "http://localhost:6333", "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

#### VS Code（GitHub Copilot Agent mode）

`.vscode/mcp.json`（專案）：

```json
{
  "servers": {
    "memory": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "<PROJECT_ROOT>/mcp-server", "run", "python", "main.py"],
      "env": { "QDRANT_URL": "http://localhost:6333", "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

> MCP 只在 **Agent mode** 下有效，Ask / Edit mode 不支援。

#### OpenAI Codex CLI

`~/.codex/config.toml`（全域）或 `.codex/config.toml`（專案）：

```toml
[mcp_servers.memory]
command = "uv"
args = ["--directory", "<PROJECT_ROOT>/mcp-server", "run", "python", "main.py"]
enabled = true

[mcp_servers.memory.env]
QDRANT_URL = "http://localhost:6333"
MCP_TRANSPORT = "stdio"
```

---

### 情境 B：遠端（HTTP）

將 server 暴露到網路，供 Claude Chat 或其他遠端工具連線。

**步驟：**

```bash
# 1. 建立 .env
cp .env.example .env
# 填入 MCP_API_KEY（自訂 secret）

# 2. 啟動所有服務
docker compose up -d
# Qdrant + memory-server 同時啟動，port 8000
```

**開放遠端存取（擇一）：**

```bash
# Cloudflare Tunnel（推薦，免費）
cloudflared tunnel --url http://localhost:8000

# 或直接開防火牆 port 8000
```

**依照使用的工具設定 MCP：**

#### Claude Code（Desktop App）

設定 → **Edit Config**，在 `mcpServers` 加入：

```json
{
  "mcpServers": {
    "memory": {
      "url": "https://<YOUR_HOST>/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MCP_API_KEY>"
      }
    }
  }
}
```

#### Claude Desktop App（claude.ai）

**Settings → Integrations → Add Integration**，填入：

- **URL：** `https://<YOUR_HOST>/mcp`
- **Header：** `Authorization: Bearer <YOUR_MCP_API_KEY>`

#### Cursor

`~/.cursor/mcp.json`（全域）或 `.cursor/mcp.json`（專案）：

```json
{
  "mcpServers": {
    "memory": {
      "url": "https://<YOUR_HOST>/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MCP_API_KEY>"
      }
    }
  }
}
```

#### VS Code（GitHub Copilot Agent mode）

`.vscode/mcp.json`（專案）：

```json
{
  "servers": {
    "memory": {
      "type": "http",
      "url": "https://<YOUR_HOST>/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_MCP_API_KEY>"
      }
    }
  }
}
```

#### OpenAI Codex CLI

`~/.codex/config.toml`（全域）或 `.codex/config.toml`（專案）：

```toml
[mcp_servers.memory]
url = "https://<YOUR_HOST>/mcp"
enabled = true

[mcp_servers.memory.headers]
Authorization = "Bearer <YOUR_MCP_API_KEY>"
```

---

## MCP Tools

| Tool | 參數 | 說明 |
|---|---|---|
| `save_memory` | `content, type, tags[]` | 儲存記憶 |
| `search_memories` | `query, type?, limit?` | 語意搜尋 |
| `get_memory` | `memory_id` | 用 ID 取得單筆 |
| `update_memory` | `memory_id, content` | 更新內容（自動重新 embed） |
| `delete_memory` | `memory_id` | 刪除 |
| `list_memory_types` | — | 列出目前有哪些 type |

**Memory types：** `user` / `feedback` / `project` / `reference` / `general`

---

## 讓 AI 主動使用 Memory

MCP server 只提供工具，**AI 不會自動存取記憶**，需要透過 instruction 告知。

### 加入以下指令到對應工具的 instruction 檔

```markdown
你有 memory MCP server 可用，請主動使用：
- 對話開始時，用 search_memories 查詢與當前任務相關的背景記憶
- 學到關於使用者偏好、專案決策、重要 feedback 時，主動呼叫 save_memory
- 記憶類型：user（使用者資訊）、feedback（偏好與糾正）、project（專案脈絡）、reference（外部資源）、general（其他）
```

### Instruction 檔位置

| 工具 | 檔案 | 範圍 |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | 全域 |
| Claude Code | `CLAUDE.md`（專案根目錄） | 專案 |
| Claude Chat | Projects → System prompt | 全域 |
| Cursor | `~/.cursor/rules/memory.md` | 全域 |
| Cursor | `.cursor/rules/memory.md` | 專案 |
| VS Code Copilot | `.github/copilot-instructions.md` | 專案 |
| OpenAI Codex CLI | `~/.codex/instructions.md` | 全域 |
| OpenAI Codex CLI | `AGENTS.md`（專案根目錄） | 專案 |

### 已知限制

CLAUDE.md 的指令會被注入為 context，但 Claude 不保證每次對話開頭都會主動執行 `search_memories`。若發現 Claude 沒有自動查詢記憶，手動提示即可：

> 「請先用 search_memories 查詢相關背景記憶」

### 確認記憶有沒有存進去

- **Qdrant dashboard：** `http://localhost:6333/dashboard` → `memories` collection
- **直接問 AI：** 「請用 `list_memory_types` 看目前有哪些記憶類型」

---

## 環境變數

| 變數 | 預設值 | 說明 |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant 連線位址 |
| `MCP_TRANSPORT` | `stdio` | `stdio`（本機）或 `http`（遠端） |
| `MCP_API_KEY` | —（無驗證）| HTTP mode 驗證 key |
| `HOST` | `0.0.0.0` | HTTP mode 監聽 host |
| `PORT` | `8000` | HTTP mode 監聽 port |
| `FASTEMBED_CACHE_PATH` | `~/.cache/fastembed` | fastembed 模型快取路徑（伺服器啟動時自動設定） |

---

## Troubleshooting

### fastembed 模型快取

伺服器啟動時會自動將 `FASTEMBED_CACHE_PATH` 設為 `~/.cache/fastembed`（除非已手動指定）。
啟動時會驗證模型可用性，若快取被清除會自動重新下載。

如果啟動失敗並顯示 embedding model validation 錯誤，請確認：
- 有網路連線（首次下載需 ~550MB）
- 磁碟空間足夠
- 快取路徑有寫入權限

---

## 環境轉移

```bash
# 備份（在 memory-server/ 根目錄）
tar -czf memory-backup-$(date +%Y%m%d).tar.gz data/qdrant/

# 還原
tar -xzf memory-backup-YYYYMMDD.tar.gz
```

**搬到新機器：**

```bash
# 舊機器
tar -czf memory-backup.tar.gz data/qdrant/

# 新機器
git clone <this-repo> && cd memory-server
tar -xzf memory-backup.tar.gz
docker compose up qdrant -d
cd mcp-server && uv sync
```

> fastembed 模型（`~/.cache/fastembed`）可一起搬，省去重新下載。

---

## Maintenance

### 執行測試

需先啟動 Qdrant：

```bash
docker compose up qdrant -d
cd mcp-server
uv sync --extra dev
QDRANT_URL=http://localhost:6333 uv run python -m pytest tests/ -v
```

CI（GitHub Actions）會在每次 push / PR 自動執行。

### 更新套件

```bash
cd mcp-server
uv tree --outdated      # 查看有新版的套件
uv sync --upgrade       # 升級全部並更新 uv.lock
```

Dependabot 每週自動開 PR 更新套件（Python、Docker image、GitHub Actions），合併前 CI 會跑測試驗證。

### 更新 Python 版本

1. `mcp-server/pyproject.toml` → 修改 `requires-python`
2. `mcp-server/Dockerfile` → 修改 `FROM python:3.x-slim`
3. 重建：`uv sync && docker compose build memory-server`

### 更新 Qdrant image

```bash
tar -czf memory-backup-$(date +%Y%m%d).tar.gz data/qdrant/  # 先備份
docker compose pull qdrant
docker compose up qdrant -d
```

### 更新 uv

```bash
brew upgrade uv      # macOS / WSL
uv self update       # Windows 原生
```
