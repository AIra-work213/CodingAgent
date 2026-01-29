# Coding Agents SDLC Pipeline

Полностью автономная система автоматизации разработки ПО на основе агентов для GitHub, созданная с помощью LangGraph, LangChain и OpenRouter.

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange.svg)](https://langchain.com/)

## 🚀 Быстрый старт

### Сценарий 1: Удалённый сервер + новый ПК (самый частый)

> **У вас есть:** VPS/облачный сервер + совершенно новый ПК
> **Хотите:** Работать с агентом удалённо, устанавливая минимум на ПК

#### Шаг 1: Настройка сервера (один раз)

```bash
# Подключиться к серверу по SSH
ssh user@your-server.com

# Установить Docker (если не установлен)
curl -fsSL https://get.docker.com | sh

# Клонировать репозиторий
git clone https://github.com/AIra-work213/CodingAgent
cd CodingAgent

# Создать .env файл
cp .env.example .env
nano .env
```

Отредактируйте `.env` на сервере:

```bash
# Обязательно заполнить:
OPENROUTER_API_KEY=sk-or-v1-...          # Ваш ключ OpenRouter
GITHUB_REPO=owner/repo                   # Любой репозиторий (для работы)

# Остальное можно оставить по умолчанию
REDIS_URL=redis://redis:6379/0
API_PORT=8000
```

```bash
# Запустить сервер
docker-compose up -d

# Проверить, что работает
curl http://localhost:8000/health
```

**Для доступа извне (опционально):**

```bash
# Вариант A: localtunnel (бесплатно, без регистрации, рекомендуется)
npm install -g localtunnel
lt --port 8000
# Получите URL вида: https://random-name.loca.lt

# Вариант B: ngrok (альтернатива, требует регистрацию)
apt install ngrok  # или скачать с ngrok.com
ngrok http 8000
# Получите URL вида: https://abc123.ngrok.io

# Вариант C: свой домен (для production)
# Настроить Nginx reverse proxy с SSL
```

#### Шаг 2: Настройка нового ПК (клиента)

**Linux/Mac:**

```bash
# Установить Python 3.12+
python3 --version  # должно быть 3.12 или выше

# Установить зависимости CLI
pip3 install click rich httpx websockets

# Или установить CLI как пакет (если доступно)
pip3 install coding-agents-cli
```

**Windows:**

```powershell
# Установить Python с python.org
# Затем в PowerShell:
pip install click rich httpx websockets
```

#### Шаг 3: Проверка подключения

```bash
# С нового ПК - проверить, что сервер доступен
curl https://cold-words-rescue.loca.lt/health

# Или через CLI (если установлен как пакет)
coding-agent server status --server https://cold-words-rescue.loca.lt
```

#### Шаг 4: Создание GitHub токена на новом ПК

```bash
# Создать Personal Access Token на GitHub:
# https://github.com/settings/tokens
# Права: repo (full control)

# Сохранить токен в переменной окружения
export GITHUB_TOKEN=ghp_your_token_here

# Или использовать --token в каждом вызове
```

#### Шаг 5: Запуск агента с нового ПК

```bash
# Указать сервер при запуске
coding-agent run \
  --server https://your-server.com \
  --repo owner/repo \
  --issue 123 \
  --token ghp_your_token_here

# Или настроить сервер по умолчанию
coding-agent config add-server mycloud https://your-server.com --set-default

# Теперь можно запускать короче
coding-agent run --repo owner/repo --issue 123 --token ghp_your_token_here
```

**Готово!** Агент работает на сервере, а вы управляете им с нового ПК.

---

### Сценарий 2: Локальный запуск (на своём ПК)

#### Требования

- Docker и Docker Compose
- GitHub Personal Access Token
- OpenRouter API Key

#### 1. Клонирование и настройка

```bash
git clone <repo-url>
cd CodingAgent

# Создать файл конфигурации
cp .env.example .env

# Отредактировать .env
nano .env
```

#### 2. Настройка переменных окружения

Обязательные переменные в `.env`:

```bash
# API OpenRouter (получить на https://openrouter.ai/)
OPENROUTER_API_KEY=sk-or-v1-...

# GitHub
GITHUB_TOKEN=ghp_...                  # GitHub Personal Access Token
GITHUB_REPO=owner/repo                # Ваш репозиторий
```

#### 3. Запуск с Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f api
```

#### 4. Использование CLI

```bash
# Запуск Code Agent для Issue
docker-compose exec api python -m app.cli code-agent 123

# Запуск Reviewer Agent для PR
docker-compose exec api python -m app.cli reviewer 456

# Просмотр деталей Issue
docker-compose exec api python -m app.cli show-issue 123
```

## 📋 Функциональность

### Code Agent

Автоматически обрабатывает GitHub Issues и создаёт Pull Requests:

```
Issue → Парсинг → Анализ → Генерация кода → Валидация → PR → Обработка feedback
```

**Возможности:**
- Извлечение структурированных требований из Issue
- Анализ текущей кодовой базы
- Генерация кода с помощью LLM
- Создание branch и PR
- Многоитерационная обработка feedback

### Reviewer Agent

Автоматически анализирует Pull Requests:

```
PR → Анализ diff → Проверка CI → Code Review → Approval/Request Changes
```

**Возможности:**
- Анализ code diff
- Проверка CI/CD результатов
- Сравнение с требованиями Issue
- Генерация комментариев review
- Авто-approve при успехе

## 🏗 Архитектура

```
app/
├── core/                      # Основные модули
│   ├── agents/                # LangGraph workflows
│   │   ├── code_agent.py      # Code Agent workflow
│   │   └── reviewer_agent.py  # Reviewer Agent workflow
│   ├── tools/                 # LangChain tools
│   │   └── github_tools.py    # GitHub API инструменты
│   ├── llm/                   # OpenRouter integration
│   │   ├── openrouter.py      # LLM клиент
│   │   └── prompts.py         # Шаблоны промптов
│   ├── models/                # Pydantic модели
│   │   └── task.py            # Модели задач
│   ├── config.py              # Конфигурация
│   └── task_manager.py        # Менеджер задач (Redis)
├── api/                       # FastAPI endpoints
│   ├── main.py                # Приложение FastAPI
│   ├── tasks.py               # Эндпоинты задач
│   ├── websocket.py           # WebSocket handler
│   └── streaming.py           # SSE streaming
├── cli/                       # CLI интерфейс
│   ├── main.py                # Click команды
│   ├── dashboard.py           # Rich Live Dashboard
│   ├── config.py              # Управление конфигурацией
│   └── utils.py               # Вспомогательные функции
└── workflows/                 # Дополнительные workflows
```

## 🔧 API Endpoints

Запустите сервис и откройте http://localhost:8000/docs для интерактивной документации Swagger.

### Создание задачи

```bash
POST /tasks
Content-Type: application/json

{
    "type": "code-agent",
    "issue_number": 123,
    "branch_name": "agent/issue-123",
    "max_iterations": 5
}
```

### Получение задачи

```bash
GET /tasks/{task_id}
```

### Потоковая передача логов (SSE)

```bash
GET /tasks/{task_id}/logs/stream
```

### WebSocket подключение

```bash
WS /ws/tasks/{task_id}
```

## 💻 CLI Команды

### Основные команды

```bash
# Локальный запуск (токен используется из .env на сервере)
coding-agent run --repo owner/repo --issue 123

# Удалённый запуск с указанием GitHub токена
# Токен передаётся на сервер и используется только для этой задачи
coding-agent run \
  --server https://my-agent.example.com \
  --repo owner/repo \
  --issue 123 \
  --token ghp_xxx

# Короткая форма
coding-agent run -s https://my-agent.com -r owner/repo -i 123 -t ghp_xxx

# Использование переменной окружения для токена
export GITHUB_TOKEN=ghp_xxx
coding-agent run --server https://my-agent.com --repo owner/repo --issue 123

# Использование сохранённого сервера из конфигурации
coding-agent config add-server mycloud https://my-agent.example.com
coding-agent config set-default mycloud
coding-agent run --repo owner/repo --issue 123 --token ghp_xxx
```

### Команды конфигурации

```bash
# Добавить remote server
coding-agent config add-server mycloud https://api.example.com --set-default

# Установить сервер по умолчанию
coding-agent config set-default mycloud

# Добавить GitHub токен для сервера
coding-agent config add-token https://api.example.com ghp_xxx

# Показать все конфигурации
coding-agent config list --show-tokens
```

### Команды сервера

```bash
# Запустить сервер
coding-agent server start

# Проверить статус сервера
coding-agent server status

# Проверить health endpoint
coding-agent server health
```

## 🔄 GitHub Actions (опционально)

### Автоматический запуск

**Code Agent** запускается при создании Issue с лейблом `agent-task`.

**Reviewer Agent** запускается при создании или обновлении Pull Request.

### Workflows

- `.github/workflows/code-agent.yml` - Запуск Code Agent
- `.github/workflows/reviewer-agent.yml` - Запуск Reviewer Agent

## 🧪 Локальная разработка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Установить зависимости
pip install -e ".[dev]"

# Запуск линтинга
ruff check app/
ruff format app/

# Запуск type checking
mypy app/

# Запуск тестов
pytest tests/ -v --cov=app
```

## 🌐 Удалённое использование

### Развертывание сервера в облаке

```bash
# На VPS или в облаке
git clone <repo>
cd CodingAgent
cp .env.example .env
# Настроить .env с вашими ключами

docker-compose up -d
```

### Подключение с любого компьютера

```bash
# Настройка удалённого сервера (один раз)
coding-agent config add-server mycloud https://my-agent.example.com --set-default

# Теперь можно запускать агента из любого места!
# GitHub токен передаётся при каждом вызове (безопасно)
coding-agent run --repo owner/repo --issue 123 --token ghp_xxx

# Или использовать переменную окружения
export GITHUB_TOKEN=ghp_xxx
coding-agent run --repo owner/repo --issue 123
```

### 🔐 Безопасность GitHub токенов

**Рекомендуемый подход для удалённых серверов:**

1. **Не хранить** GitHub токены на сервере в `.env`
2. **Передавать токен** при каждом вызове через `--token`
3. **Использовать переменную окружения** `GITHUB_TOKEN` локально

Токен передаётся на сервер по HTTPS и используется только для конкретной задачи.

### Через переменную окружения

```bash
# Указать сервер напрямую
export CODING_AGENT_SERVER=https://my-agent.example.com
coding-agent run --repo owner/repo --issue 123 --token ghp_xxx
```

### Использование с localtunnel (для тестирования)

**Localtunnel - это бесплатный сервис туннелирования без регистрации:**

```bash
# На сервере - установка localtunnel (один раз)
npm install -g localtunnel

# Запуск tunnel
lt --port 8000
# Получите URL: https://random-name.loca.lt

# На клиенте
export CODING_AGENT_SERVER=https://random-name.loca.lt
coding-agent run --repo owner/repo --issue 123 --token ghp_xxx
```

**Преимущества localtunnel:**
- ✅ Полностью бесплатный
- ✅ Не требует регистрации
- ✅ Мгновенный старт
- ✅ Поддержка WebSocket
- ✅ Автоматический HTTPS

### Использование с ngrok (альтернатива)

```bash
# На сервере
ngrok http 8000
# Получите URL: https://abc123.ngrok.io

# На клиенте
coding-agent run --server https://abc123.ngrok.io --repo owner/repo --issue 123
```

## 📊 Мониторинг

### Health Check

```bash
curl http://localhost:8000/health
```

### Статистика задач

```bash
curl http://localhost:8000/tasks/stats/summary
```

### Статус сервисов

```bash
docker-compose ps
docker-compose logs -f
```

## 🔐 Безопасность

### GitHub токены

**Для локального использования:**
- Токен хранится в `.env` на сервере
- Подходит для личного использования

**Для удалённого/командного использования:**
- Передавайте токен через `--token` при каждом вызове
- Или используйте переменную окружения `GITHUB_TOKEN`
- **Не храните** персональные токены на общем сервере

```bash
# Безопасно - токен передаётся только для этой задачи
coding-agent run --server https://agent.example.com --repo owner/repo --issue 123 --token ghp_xxx
```

### Рекомендации

- ✅ Используйте GitHub App вместо Personal Token для production
- ✅ Храните секреты в GitHub Secrets или vault
- ✅ Включите HTTPS для webhook endpoints
- ✅ Настройте rate limiting для API
- ⚠️ Не передавайте токены через небезопасные каналы
- ⚠️ Используйте минимальные права токена (scope)

## ⚙️ Конфигурация
docker-compose ps
docker-compose logs -f
```

## 🔐 Безопасность

- Используйте GitHub App вместо Personal Token для production
- Храните секреты в GitHub Secrets или vault
- Включите rate limiting для API
- Используйте HTTPS для webhook endpoints

## ⚙️ Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OPENROUTER_API_KEY` | API ключ OpenRouter | - |
| `GITHUB_TOKEN` | GitHub токен | - |
| `GITHUB_REPO` | Репозиторий (owner/repo) | - |
| `REDIS_URL` | URL Redis | redis://redis:6379/0 |
| `MAX_ITERATIONS` | Макс. итераций | 5 |
| `DEFAULT_MODEL` | Модель LLM | gpt-4o-mini |

## 📝 Поддерживаемые модели

- `gpt-4o-mini` - Основная модель (баланс)
- `qwen-2.5-coder` - Для генерации кода
- `deepseek-coder` - Альтернатива для кода

## 🤝 Участие в разработке

1. Fork репозитория
2. Создайте feature branch
3. Commit изменения
4. Push в branch
5. Создайте Pull Request

## 📄 Лицензия

MIT License

## 🔗 Полезные ссылки

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenRouter](https://openrouter.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Rich CLI](https://rich.readthedocs.io/)
