# Полное техническое задание: Coding Agents SDLC Pipeline с CLI

## 1. Общая информация

**Название проекта:** Autonomous Coding Agent SDLC  
**Роль разработчика:** ML Engineer (1 человек)  
**Срок реализации:** 4 недели  
**Тип развертывания:** Локальный сервер + CLI + опционально GitHub Actions  
**Цель:** Создать полностью автономную систему автоматизации разработки ПО

```
Issue → CLI Command → Live Dashboard → Code Changes → PR → Review → Merge
```

## 2. Функциональная архитектура

### 2.1 Основной workflow
```
docker-compose up -d
coding-agent run --repo <url> --issue <num> --token <ghp>
↓ Live dashboard с real-time обновлениями
✅ PR создан → CI/CD → Auto-review → Merge/Итерация
```

### 2.2 CLI Dashboard (Rich Live)
```
┌─ Task #7b4f2d1 ─ Fix User Authentication ───────────────┐
│ Status: [Iteration 2/5] Reviewing PR... ████████░░ 75% │
├────────────────────────────────────────────────────────┤
│ Progress:    ██████████░░░░░░░░░░ 45%                   │
│ Time:        00:08:23                    PR: #23 [OPEN] │
│ Files:       3 modified (auth.py +18-5, tests +12)      │
│ Feedback:    "Add JWT expiry validation" [reviewer]     │
└── [R]etry [S]top [D]iff [L]ogs [Q]uit ──────────────────┘
```

## 3. Технический стек (ОБЯЗАТЕЛЬНЫЙ)

```
Core Framework:   LangChain + LangGraph
API Server:       FastAPI + WebSocket (SSE)
CLI Interface:    Click + Rich + asyncio
LLM:              OpenRouter API (gpt-4o-mini, qwen2.5-coder)
GitHub:           PyGithub
Persistence:      Redis (LangGraph checkpointer)
Code Quality:     ruff, black, mypy, pytest
Containerization: Docker + docker-compose
Monitoring:       Prometheus metrics
```

## 4. Детальная структура проекта

```
coding-agents-sdlc/
├── app/                          # FastAPI + LangGraph core
│   ├── __init__.py
│   ├── main.py                   # FastAPI app
│   ├── core/
│   │   ├── agents/               # LangGraph workflows
│   │   │   ├── code_agent.py
│   │   │   ├── reviewer_agent.py
│   │   │   └── types.py
│   │   ├── tools/                # LangChain tools
│   │   │   ├── github.py
│   │   │   ├── code_analysis.py
│   │   │   └── llm.py
│   │   └── llm/                  # OpenRouter client
│   ├── api/                      # FastAPI routers
│   │   ├── tasks.py
│   │   └── websocket.py
│   └── cli/                      # CLI entrypoint
│       ├── __main__.py
│       └── dashboard.py
├── static/                       # Demo issues/templates
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 5. Детальные спецификации компонентов

### 5.1 FastAPI Server

**Эндпоинты:**
```python
# Tasks
POST  /tasks/           # Создать задачу {repo, issue, token}
GET   /tasks/{task_id}  # Статус задачи
GET   /tasks/{task_id}/diff  # Diff изменений
GET   /tasks            # Список активных задач

# Streaming
GET   /tasks/{task_id}/logs/stream  # SSE logs
WS    /ws/tasks/{task_id}           # WebSocket updates

# Agents (internal)
POST  /agents/code-agent/run
POST  /agents/reviewer/analyze
```

**Docker Compose:**
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"    # REST API
      - "8001:8001"    # WebSocket
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis_data:/data
```

### 5.2 LangGraph Workflows

**CodeAgent Graph:**
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List

class CodeAgentState(TypedDict):
    task_id: str
    repo_url: str
    issue_number: int
    issue_content: str
    requirements: dict
    current_code: dict[str, str]  # file -> content
    generated_code: dict[str, str]
    pr_url: str
    feedback: Annotated[List[str], "append"]
    iteration: int
    max_iterations: int = 5
    status: str

graph = StateGraph(CodeAgentState)
graph.add_node("parse_issue", parse_issue)
graph.add_node("analyze_requirements", analyze_requirements)
graph.add_node("generate_code", generate_code)
graph.add_node("validate_code", validate_code)
graph.add_node("create_pr", create_pr)
graph.add_node("process_feedback", process_feedback)

# Edges with conditions
graph.add_conditional_edges(
    "create_pr",
    should_review_pr,
    {"review": "reviewer_agent", END: END}
)
```

**ReviewerAgent Graph:**
```python
class ReviewerState(TypedDict):
    pr_diff: str
    ci_results: dict
    issue_requirements: dict
    review_comments: List[str]
    code_score: float  # 0-1
    approval_decision: Literal["APPROVE", "REQUEST_CHANGES", "REJECT"]
```

### 5.3 CLI Client (Rich + Click)

**Команды:**
```bash
# Основные
coding-agent run --repo <url> --issue <num> --token <ghp>  # Запуск с dashboard
coding-agent status --task-id <id>                         # Краткий статус
coding-agent diff --task-id <id>                          # Diff до/после
coding-agent logs --task-id <id>                          # Поток логов
coding-agent stop --task-id <id>                          # Остановить задачу

# Сервис
coding-agent server start                                 # Запустить сервер
coding-agent server status                                # Статус сервера
```

**Dashboard features:**
- Live progress bars
- File change table с preview
- Real-time logs
- Keyboard shortcuts (R/S/D/L/Q)
- Auto-refresh каждые 2 сек
- WebSocket reconnect

### 5.4 GitHub Tools (LangChain)

```python
@github_tool
def get_issue_content(repo: str, issue_num: int) -> str:
    """Получить полное описание Issue"""
    # PyGithub API call

@github_tool  
def get_repo_file_content(repo: str, path: str, ref: str = "main") -> str:
    """Получить содержимое файла из репозитория"""

@github_tool
def create_pr(repo: str, branch: str, title: str, body: str) -> str:
    """Создать Pull Request"""

@github_tool
def post_review_comment(pr_url: str, comment: str) -> str:
    """Опубликовать review комментарий в PR"""
```

### 5.5 OpenRouter LLM Integration

```python
class OpenRouterLLM(ChatOpenAI):
    def __init__(self, model: str = "openai/gpt-4o-mini"):
        super().__init__(
            model=model,
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1,
        )
```

**Модели (приоритет):**
1. `openai/gpt-4o-mini` - основная
2. `qwen/qwen2.5-coder-7b-instruct` - кодинг
3. `deepseek/deepseek-coder-v2` - backup

## 6. Детальный план разработки (4 недели)

### Неделя 1: Infrastructure (40%)
```
[D1-2] FastAPI + Docker + Redis
[D3]   OpenRouter LLM + базовые промпты  
[D4]   PyGithub tools + auth
[D5]   CLI skeleton + Rich dashboard
```

### Неделя 2: Code Agent (60%)
```
[D6-7]  LangGraph CodeAgent workflow
[D8]    Issue parsing + requirements extraction
[D9]    Code generation + git operations
[D10]   PR creation + validation pipeline
```

### Неделя 3: Reviewer Agent (70%)
```
[D11-12] LangGraph Reviewer workflow
[D13]    PR diff analysis + CI results
[D14]    Multi-iteration feedback loop
[D15]    WebSocket + real-time CLI updates
```

### Неделя 4: Polish + Demo (90%)
```
[D16-17] Error handling + limits
[D18]    Monitoring + metrics
[D19]    Demo issues + documentation
[D20]    Performance optimization + testing
```

## 7. Критерии приемки (обязательные)

### ✅ Core Functionality
```
[ ] docker-compose up -d          → API+Redis ready (<30s)
[ ] coding-agent run --repo...    → Live dashboard + PR created
[ ] 3+ автоматические итерации    → Code улучшается по feedback
[ ] Auto-approve/merge valid PRs  → Zero manual intervention
[ ] coding-agent diff --task-id   → Colored file diffs + preview
```

### ✅ UX/Performance
```
[ ] Dashboard updates <2s latency
[ ] Cold start <10s
[ ] Agent iteration <90s
[ ] Graceful error recovery
[ ] Token/repo permission validation
```

### ✅ Production Ready
```
[ ] Dockerfile multi-stage <500MB
[ ] Healthchecks + auto-restart
[ ] Structured logging (JSON)
[ ] Rate limiting + retry logic
[ ] .env validation + secrets
```

## 8. Результат сдачи

```
1. ✅ GitHub репозиторий (public)
2. ✅ docker-compose up -d (1 команда)
3. ✅ 5+ demo Issues разной сложности  
4. ✅ 5-минутное демо видео
5. ✅ Метрики: success_rate >85%, avg_iterations <4
6. ✅ README с полными инструкциями
7. ✅ ngrok tunnel demo (remote access)
```

## 9. Запуск (1 команда)

```bash
# Пользователь:
git clone <repo>
cd coding-agents-sdlc
cp .env.example .env
# vim .env → OPENROUTER_API_KEY, GITHUB_TOKEN

docker-compose up -d
coding-agent run \
  --repo https://github.com/user/test-repo \
  --issue 42 \
  --token ghp_xxxxxxxxxxxxxxxxxxxx
```

**Ожидаемый результат:** Полностью автономная, production-ready система автоматизации разработки ПО с CLI интерфейсом, готовная к использованию любым разработчиком без дополнительной настройки.

# Дополнение: Подключение к удаленному серверу

## 3.5. Remote Server Connectivity (ОБНОВЛЕНО)

### Подключение к удаленному серверу

**Сценарии развертывания:**

```
1. LOCAL:      docker-compose up → localhost:8000
2. REMOTE:     ngrok/server → https://abc123.ngrok.io
3. CLOUD:      Yandex Cloud / cloud.ru → https://api.example.com
```

### CLI Remote Configuration

**Автоматическое определение сервера:**

```bash
# 1. Локальный (по умолчанию)
coding-agent run --repo ... --issue ...

# 2. Remote по URL
coding-agent run --server https://abc123.ngrok.io --repo ...

# 3. Remote по env
export CODING_AGENT_SERVER=https://api.example.com
coding-agent run --repo ...

# 4. Config file (~/.coding-agent/config.json)
{
  "server_url": "https://api.example.com",
  "default_token": "ghp_xxx"
}
```

### Server Discovery & Healthcheck

**CLI auto-detection алгоритм:**
```python
def detect_server() -> str:
    # 1. Check CODING_AGENT_SERVER env
    # 2. Check ~/.coding-agent/config.json  
    # 3. Check localhost:8000 health
    # 4. Prompt user for URL
    pass

async def healthcheck(server_url: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{server_url}/health")
        return resp.status_code == 200
```

**Health endpoint (FastAPI):**
```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "redis_connected": redis.ping(),
        "llm_ready": True
    }
```

## Обновленный docker-compose.yml (Remote Ready)

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"           # Local
      - "127.0.0.1:8001:8001" # WebSocket local-only
    environment:
      - SERVER_URL=http://localhost:8000  # Auto-config
      - PUBLIC_URL=${PUBLIC_URL:-}        # Cloud/ngrok
    volumes:
      - ./static:/app/static:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Remote Deployment Guides

### 1. Ngrok (5 минут)
```bash
# Сервер
docker-compose up -d
ngrok http 8000

# CLI (авто)
export CODING_AGENT_SERVER=https://abc123.ngrok.io
coding-agent run --repo ...
```

### 2. Yandex Cloud / cloud.ru
```bash
# Docker push + Cloud Run/Functions
docker tag app:latest cr.yandex/ycr/<project>/coding-agent:latest
ycr push ...

# Cloud Load Balancer → HTTPS endpoint
export CODING_AGENT_SERVER=https://api.<project>.cloud.yandex.net
```

### 3. VPS (Ubuntu/Debian)
```bash
# Install
curl -fsSL https://get.docker.com | sh
docker-compose up -d

# HTTPS reverse proxy (nginx + certbot)
export CODING_AGENT_SERVER=https://coding-agent.yourdomain.com
```

## CLI Remote Features

### Real-time Remote Dashboard
```
┌─ Remote: https://abc123.ngrok.io ─ Task #7b4f ───────┐
│ 🔴 Server: https://abc123.ngrok.io [✓ Healthy]      │
│ Latency: 45ms | Region: EU                           │
├──────────────────────────────────────────────────────┤
│ Status: [Iteration 3/5] Code Review... 92%           │
│ PR: https://github.com/.../pull/15 [OPEN]            │
└── [R]etry [S]top [D]iff [L]ogs [Q]uit ───────────────┘
```

### Connection Status Indicators
```
🟢 LOCAL   - localhost:8000 (0ms)
🟡 REMOTE  - https://abc123.ngrok.io (45ms)  
🔴 OFFLINE - No server connection
```

### Token Management (Secure)
```bash
# Store token remotely (encrypted)
coding-agent config token add --server https://... --token ghp_xxx

# List servers/tokens
coding-agent config list

# Remove
coding-agent config token remove --server https://...
```

## Обновленные CLI команды

```bash
# Полная remote поддержка
coding-agent run \
  --server https://abc123.ngrok.io \
  --repo https://github.com/user/repo \
  --issue 42 \
  --token ghp_xxx

# Quick connect (saved config)
coding-agent run --server mycloud --repo ... --issue ...

# Server management
coding-agent server status --server https://...
coding-agent server health --server https://...
```

## Config File (~/.coding-agent/config.json)
```json
{
  "servers": {
    "local": {
      "url": "http://localhost:8000"
    },
    "ngrok": {
      "url": "https://abc123.ngrok.io",
      "tokens": ["ghp_xxx"]
    },
    "mycloud": {
      "url": "https://api.mycloud.example.com"
    }
  },
  "default_server": "local",
  "auto_connect": true
}
```

## Production Remote Checklist

### ✅ Remote Server Requirements
```
[ ] /health endpoint → 200 OK
[ ] HTTPS termination (ngrok/cloud)
[ ] CORS headers для CLI domains
[ ] Rate limiting (100 req/min per IP)
[ ] Token validation middleware
[ ] Redis persistence (cloud Redis)
```

### ✅ CLI Remote Testing
```
[ ] Auto server discovery
[ ] WebSocket reconnect (3 attempts)
[ ] Token encryption in config
[ ] Offline mode (queue tasks)
[ ] Latency monitoring (<500ms)
```

## Демо Remote Workflow

```bash
# 1. Развернуть сервер (любой VPS/ngrok)
$ docker-compose up -d
$ ngrok http 8000  # https://abc123.ngrok.io

# 2. На любом ПК (даже без Docker)
$ pipx install coding-agents-cli
$ export CODING_AGENT_SERVER=https://abc123.ngrok.io
$ coding-agent run --repo myrepo --issue 1 --token ghp_...

# 3. Live dashboard работает remotely!
```

**Теперь CLI полностью поддерживает remote servers** с автоматическим обнаружением, безопасным хранением токенов, real-time dashboard и graceful reconnection.