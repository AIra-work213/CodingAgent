# Coding Agents SDLC Pipeline

> Полностью автономная система автоматизации разработки ПО на основе агентов для GitHub, созданная с помощью LangGraph, LangChain и OpenRouter.

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-orange.svg)](https://langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-workflow-purple.svg)](https://langchain-ai.github.io/langgraph/)

---

## Что это такое?

Coding Agent — это AI-система, которая автоматически:
- Читает GitHub Issues
- Анализирует требования
- Генерирует код
- Создаёт Pull Requests
- Проводит code review
- Обрабатывает feedback

**Демо-сервер:** https://slow-mammals-shout.loca.lt

---

## Возможности системы

### Code Agent
Автоматическая генерация кода из GitHub Issues:

```
Issue → Парсинг → Анализ требований → Генерация кода → Валидация → PR → Итерации по feedback
```

- Извлечение структурированных требований
- Анализ текущей кодовой базы
- Генерация кода с помощью LLM
- Создание branch и PR
- Многоитерационная обработка feedback (до 5 итераций)

### Reviewer Agent
Автоматический анализ Pull Requests:

```
PR → Анализ diff → Проверка CI → Code Review → Approval/Request Changes
```

- Анализ code diff
- Проверка CI/CD результатов
- Сравнение с требованиями Issue
- Генерация комментариев review
- Авто-approve при успехе

### Мониторинг репозиториев
Автоматическое отслеживание новых issues:

```bash
# Добавить репозиторий на мониторинг
coding-agent monitor add owner repo --token ghp_xxx

# Запустить мониторинг
coding-agent monitor start
```

- Отслеживание новых issues каждые N секунд
- Автоматический запуск Code Agent
- Создание PR без ручного вмешательства

### Live Dashboard
Real-time отображение прогресса:

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

---

## Быстрый старт

### Сценарий 1: Использование демо-сервера (самый быстрый)

> Вами нужен только Python и GitHub токен

```bash
# 1. Установить зависимости CLI
pip install click rich httpx websockets

# 2. Создать GitHub Personal Access Token
# https://github.com/settings/tokens
# Права: repo (full control)

# 3. Запустить агент на демо-сервере
coding-agent run \
  --server https://slow-mammals-shout.loca.lt \
  --repo owner/repo \
  --issue 123 \
  --token ghp_your_token_here
```

**Готово!** Агент работает на удалённом сервере, вы управляете им через CLI.

---

### Сценарий 2: Удалённый сервер + новый ПК

> У вас есть VPS/облачный сервер + совершенно новый ПК

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
```

**Windows:**

```powershell
# Установить Python с python.org
# Затем в PowerShell:
pip install click rich httpx websockets
```

#### Шаг 3: Создание GitHub токена на новом ПК

```bash
# Создать Personal Access Token на GitHub:
# https://github.com/settings/tokens
# Права: repo (full control)

# Сохранить токен в переменной окружения
export GITHUB_TOKEN=ghp_your_token_here
```

#### Шаг 4: Запуск агента с нового ПК

```bash
# Указать сервер при запуске
coding-agent run \
  --server https://your-server-url.loca.lt \
  --repo owner/repo \
  --issue 123 \
  --token ghp_your_token_here

# Или настроить сервер по умолчанию
coding-agent config add-server mycloud https://your-server-url.loca.lt --set-default

# Теперь можно запускать короче
coding-agent run --repo owner/repo --issue 123 --token ghp_your_token_here
```

---

### Сценарий 3: Локальный запуск

#### Требования

- Docker и Docker Compose
- GitHub Personal Access Token
- OpenRouter API Key

#### 1. Клонирование и настройка

```bash
git clone https://github.com/AIra-work213/CodingAgent
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

---

## CLI Команды

### Основные команды

```bash
# Запуск Code Agent для Issue с Live Dashboard
coding-agent run --repo owner/repo --issue 123

# С указанием сервера
coding-agent run --server https://slow-mammals-shout.loca.lt --repo owner/repo --issue 123

# С GitHub токеном
coding-agent run --repo owner/repo --issue 123 --token ghp_xxx

# Короткая форма
coding-agent run -s https://server.com -r owner/repo -i 123 -t ghp_xxx
```

### Управление задачами

```bash
# Список всех задач
coding-agent tasks

# Только активные
coding-agent tasks --active-only

# Статус конкретной задачи
coding-agent status abc123-def456

# Логи задачи
coding-agent logs abc123-def456

# Diff изменений
coding-agent diff abc123-def456

# Остановить задачу
coding-agent stop abc123-def456
```

### Команды сервера

```bash
# Запустить сервер
coding-agent server start

# Проверить статус сервера
coding-agent server status

# С другим портом
coding-agent server start -p 8080

# С auto-reload (для разработки)
coding-agent server start --reload
```

### Команды конфигурации

```bash
# Добавить remote server
coding-agent config add-server mycloud https://api.example.com --set-default

# Установить сервер по умолчанию
coding-agent config set-default mycloud

# Добавить GitHub токен для сервера
coding-agent config add-token https://slow-mammals-shout.loca.lt ghp_xxx

# Показать все конфигурации
coding-agent config list

# С отображением токенов
coding-agent config list --show-tokens

# Удалить сервер
coding-agent config remove-server mycloud

# Удалить токен
coding-agent config remove-token https://api.example.com
```

### Команды мониторинга

```bash
# Добавить репозиторий на мониторинг
coding-agent monitor add owner repo --token ghp_xxx

# С кастомным интервалом
coding-agent monitor add owner repo --token ghp_xxx --interval 120

# Запустить мониторинг
coding-agent monitor start

# Проверить статус
coding-agent monitor status

# Список отслеживаемых репозиториев
coding-agent monitor list

# Удалить репозиторий
coding-agent monitor remove owner repo

# Остановить мониторинг
coding-agent monitor stop
```

---

## API Endpoints

Запустите сервис и откройте http://localhost:8000/docs для интерактивной документации Swagger.

### Tasks

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/tasks` | Создать задачу |
| GET | `/tasks` | Список задач |
| GET | `/tasks/{task_id}` | Детали задачи |
| DELETE | `/tasks/{task_id}` | Отменить задачу |
| GET | `/tasks/{task_id}/logs` | Логи задачи |
| GET | `/tasks/{task_id}/diff` | Diff изменений |

### Monitoring

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/monitoring/repos` | Добавить репозиторий |
| GET | `/monitoring/repos` | Список репозиториев |
| DELETE | `/monitoring/repos/{owner}/{repo}` | Удалить репозиторий |
| GET | `/monitoring/status` | Статус мониторинга |
| POST | `/monitoring/start` | Запустить мониторинг |
| POST | `/monitoring/stop` | Остановить мониторинг |

### Streaming

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/tasks/{task_id}/logs/stream` | SSE логи |
| WS | `/ws/tasks/{task_id}` | WebSocket |

### Health

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/health` | Проверка работоспособности |
| GET | `/tasks/stats/summary` | Статистика задач |

---

## Удалённое использование

### Auto-discover сервера

CLI автоматически определяет сервер в следующем порядке:

1. `--server` опция
2. `CODING_AGENT_SERVER` переменная окружения
3. `~/.coding-agent/config.json` → `default_server`
4. `http://localhost:8000` (проверка health)

### Способы подключения

#### Через переменную окружения

```bash
export CODING_AGENT_SERVER=https://slow-mammals-shout.loca.lt
coding-agent run --repo owner/repo --issue 123
```

#### Через опцию --server

```bash
coding-agent run -s https://server.com --repo owner/repo --issue 123
```

#### Через config file

```bash
# Добавить сервер в конфигурацию
coding-agent config add-server production https://api.example.com --set-default

# Использовать (автоматически определится)
coding-agent run --repo owner/repo --issue 123
```

---

## Живой демо-сервер

**URL:** https://slow-mammals-shout.loca.lt

### Быстрое подключение

```bash
# Сохранить токен для демо-сервера
coding-agent config add-token https://slow-mammals-shout.loca.lt ghp_your_token

# Добавить сервер как default
coding-agent config add-server demo https://slow-mammals-shout.loca.lt --set-default

# Теперь можно запускать без указания сервера
coding-agent run --repo owner/repo --issue 123
```

### Health check

```bash
curl https://slow-mammals-shout.loca.lt/health
```

---

## Архитектура

```
app/
├── api/
│   ├── main.py              # FastAPI приложение
│   ├── tasks.py             # Эндпоинты задач
│   ├── monitoring.py        # Эндпоинты мониторинга
│   ├── websocket.py         # WebSocket обработчики
│   └── streaming.py         # SSE streaming
├── cli/
│   ├── main.py              # CLI команды
│   ├── dashboard.py         # Live dashboard
│   ├── config.py            # Управление конфигурацией
│   └── utils.py             # CLI утилиты
├── core/
│   ├── monitoring.py        # Модуль мониторинга
│   ├── agents/
│   │   ├── code_agent.py    # Code Agent workflow
│   │   └── reviewer_agent.py # Reviewer workflow
│   ├── llm/
│   │   ├── openrouter.py    # OpenRouter клиент
│   │   └── prompts.py       # Промпты
│   ├── tools/
│   │   └── github_tools.py  # LangChain инструменты
│   └── task_manager.py      # Управление задачами
```

---

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OPENROUTER_API_KEY` | API ключ OpenRouter | - |
| `GITHUB_TOKEN` | GitHub токен | - |
| `GITHUB_REPO` | Репозиторий (owner/repo) | - |
| `REDIS_URL` | URL Redis | redis://redis:6379/0 |
| `MAX_ITERATIONS` | Макс. итераций | 5 |
| `DEFAULT_MODEL` | Модель LLM | qwen/qwen-2.5-coder-32b-instruct |
| `CODING_AGENT_SERVER` | URL сервера по умолчанию | http://localhost:8000 |

---

## Поддерживаемые модели

| Модель | Использование | Статус |
|--------|---------------|--------|
| `qwen/qwen-2.5-coder-32b-instruct` | Coding, Planning | ✅ |
| `google/gemini-flash-1.5` | Review | ✅ |
| `deepseek/deepseek-coder` | Coding (backup) | ✅ |
| `meta-llama/llama-3-70b-instruct` | Качественные задачи | ✅ |

Все модели доступны **бесплатно** через OpenRouter.

---

## Локальная разработка

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

---

## Безопасность

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

- Используйте GitHub App вместо Personal Token для production
- Храните секреты в GitHub Secrets или vault
- Включите HTTPS для webhook endpoints
- Настройте rate limiting для API
- Используйте минимальные права токена (scope)

---

## Статус системы

**Версия:** v0.1.0 (2026-01-30)

### Протестированные компоненты

| Компонент | Статус |
|-----------|--------|
| CLI команды | ✅ |
| Code Agent | ✅ |
| Reviewer Agent | ✅ |
| Мониторинг | ✅ |
| API сервер | ✅ |
| WebSocket | ✅ |
| Remote сервер | ✅ |

---

## Лицензия

MIT License

---

## Полезные ссылки

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenRouter](https://openrouter.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Rich CLI](https://rich.readthedocs.io/)
- GitHub: https://github.com/AIra-work213/CodingAgent
