# MCP Memory Server

跨 Claude 客戶端的持久記憶 MCP Server。讓 Claude Code、Claude Chat、Claude Cowork 共用同一份記憶，支援語意搜尋。

## 架構

```
Claude Code ────── stdio ──────┐
Claude Chat ─── HTTP + API key ─┼──► FastMCP Server ──► Qdrant
Claude Cowork ── HTTP + API key ┘                    (語意向量搜尋)
```

- **Embedding：** `BAAI/bge-small-en-v1.5`（fastembed，首次啟動自動下載 ~130MB）
- **Storage：** Qdrant（Docker 容器，資料存在 `./data/qdrant/`）

---

## 目錄結構

```
memory-server/
├── mcp-server/
│   ├── main.py          # FastMCP server（6 個 tools，支援 stdio / HTTP）
│   ├── db.py            # Qdrant CRUD + 語意搜尋
│   ├── models.py        # Memory model
│   ├── pyproject.toml
│   └── Dockerfile
├── data/
│   └── qdrant/          # Qdrant 資料（git ignored）
├── .env.example
├── docker-compose.yml
├── claude_mcp_config.json   # 各平台 MCP 設定範例
└── README.md
```

---

## MCP Tools

Claude 透過以下工具操作記憶：

| Tool | 參數 | 說明 |
|---|---|---|
| `save_memory` | `content, type, tags[]` | 儲存一筆記憶 |
| `search_memories` | `query, type?, limit?` | 語意搜尋（自動 embed query） |
| `get_memory` | `memory_id` | 用 ID 取得單筆 |
| `update_memory` | `memory_id, content` | 更新內容（自動重新 embed） |
| `delete_memory` | `memory_id` | 刪除 |
| `list_memory_types` | — | 列出目前使用中的 type |

**Memory types：** `user` / `feedback` / `project` / `reference` / `general`

---

## 前置需求

| 工具 | macOS / WSL | Windows 原生 |
|---|---|---|
| uv | `brew install uv` | [官網安裝](https://docs.astral.sh/uv/) |
| Docker Desktop | [官網下載](https://www.docker.com/products/docker-desktop/) | 同左 |

---

## 情境 A：Claude Code（本機 stdio）

Claude Code 直接透過 stdio 啟動 MCP server，**不需要** memory-server 跑在 Docker 裡，但 **Qdrant 需要跑著**。

### 1. 啟動 Qdrant

```bash
docker compose up qdrant -d
```

### 2. 安裝依賴

```bash
cd mcp-server
uv sync
```

### 3. 設定 Claude Code MCP

開啟 Claude Code 設定 → **Edit Config**，在 `mcpServers` 區塊加入 memory server。完整 config 結構如下（`preferences` 內容依個人設定而異）：

**Windows native：**
```json
{
  "preferences": { "...": "..." },
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["--directory", "D:\\Projects\\tools\\memory-server\\mcp-server", "run", "python", "main.py"],
      "env": { "QDRANT_URL": "http://localhost:6333", "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

**WSL / macOS：**（`<PROJECT_ROOT>` 換成實際路徑，使用正斜線）
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

存檔後 Claude Code 自動重載。首次會下載 fastembed 模型（~130MB），之後 cache 在 `~/.cache/fastembed`。

---

## 其他 AI 工具（本機 stdio）

所有工具都需要先啟動 Qdrant：

```bash
docker compose up qdrant -d
```

### Cursor

編輯 `~/.cursor/mcp.json`（全域）或 `.cursor/mcp.json`（專案）：

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

### VS Code（GitHub Copilot Agent mode）

編輯 `.vscode/mcp.json`（專案）：

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

> 注意：VS Code MCP 只在 **GitHub Copilot Agent mode** 下有效，Ask / Edit mode 看不到 tools。

### OpenAI Codex CLI

編輯 `~/.codex/config.toml`（全域）或 `.codex/config.toml`（專案）：

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

## 情境 B：Claude Chat / Cowork（遠端 HTTP）

需要將 server 暴露到網路上。

### 1. 建立 `.env`

```bash
cp .env.example .env
# 編輯 .env，設定 MCP_API_KEY（自訂一組 secret）
```

### 2. 啟動服務

```bash
docker compose up -d
```

Qdrant + memory-server 都會啟動，memory-server 監聽 port `8000`。

### 3. 開放遠端存取（擇一）

**Cloudflare Tunnel（推薦，免費）：**
```bash
cloudflared tunnel --url http://localhost:8000
# 會產生一個公開 URL，例如 https://xxx.trycloudflare.com
```

**直接 expose port：** 確保防火牆/路由器開放 port 8000。

### 4. 設定 Claude Chat / Cowork

在 MCP 設定介面填入：
- **URL：** `https://<YOUR_HOST>/mcp`
- **Header：** `Authorization: Bearer <YOUR_MCP_API_KEY>`

---

## 讓 AI 主動使用 Memory

MCP server 只提供工具，**AI 不會自動存取記憶**，除非有明確指示。

### 方法 A：手動叫它記（隨時可用）

在對話中直接要求：
```
請把剛才這件事存到 memory
幫我搜尋 memory 裡關於 X 的內容
列出所有 memory
```

### 方法 B：CLAUDE.md 自動化（推薦）

在專案根目錄建立 `CLAUDE.md`，加入以下指令讓 Claude 自動觸發：

```markdown
## Memory

你有 memory MCP server 可用，請主動使用：
- 對話開始時，用 search_memories 查詢與當前任務相關的背景記憶
- 學到關於使用者偏好、專案決策、重要 feedback 時，主動呼叫 save_memory
- 記憶類型：user（使用者資訊）、feedback（偏好與糾正）、project（專案脈絡）、reference（外部資源）、general（其他）
```

### 確認記憶有存進去

**方法 1：Qdrant dashboard**
開啟 `http://localhost:6333/dashboard`，點選 `memories` collection 查看所有資料。

**方法 2：直接問 AI**
```
請用 search_memories 搜尋所有記憶
請用 list_memory_types 看目前有哪些類型
```

---

## 環境變數

| 變數 | 預設值 | 說明 |
|---|---|---|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant 連線位址 |
| `MCP_TRANSPORT` | `stdio` | `stdio`（Claude Code）或 `http`（遠端） |
| `MCP_API_KEY` | —（無驗證）| HTTP mode 的驗證 key |
| `HOST` | `0.0.0.0` | HTTP mode 監聽 host |
| `PORT` | `8000` | HTTP mode 監聽 port |

---

## 環境轉移

### 備份 / 還原資料

```bash
# 備份（在 memory-server/ 根目錄執行）
tar -czf memory-backup-$(date +%Y%m%d).tar.gz data/qdrant/

# 還原
tar -xzf memory-backup-YYYYMMDD.tar.gz
```

### 搬到新機器

```bash
# 舊機器：備份後傳輸（scp / rsync / 隨身碟）
tar -czf memory-backup.tar.gz data/qdrant/

# 新機器
git clone <this-repo>
cd memory-server
tar -xzf memory-backup.tar.gz
docker compose up qdrant -d
cd mcp-server && uv sync
```

fastembed 模型（`~/.cache/fastembed`）可選擇一起搬，省去重新下載。

---

## Maintenance

### 更新 Python 套件

```bash
cd mcp-server

# 查看有新版的套件
uv tree --outdated

# 升級全部並更新 uv.lock
uv sync --upgrade
```

升級後跑一次快速測試：

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

1. `mcp-server/pyproject.toml`：修改 `requires-python`
2. `mcp-server/Dockerfile`：修改 `FROM python:3.x-slim`
3. 重建：
   ```bash
   cd mcp-server && uv sync
   docker compose build memory-server
   ```

### 更新 Qdrant image

```bash
# 備份再升級
tar -czf memory-backup-$(date +%Y%m%d).tar.gz data/qdrant/
docker compose pull qdrant
docker compose up qdrant -d
```

### 更新 uv

```bash
# macOS / WSL（brew）
brew upgrade uv

# Windows 原生
uv self update
```
