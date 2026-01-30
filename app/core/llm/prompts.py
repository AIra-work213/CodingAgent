"""Шаблоны промптов для Coding Agents"""

from langchain_core.prompts import ChatPromptTemplate

# ============================================================================
# Промпты парсера Issues
# ============================================================================

ISSUE_PARSER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Вы эксперт-аналитик программных требований. Ваша задача — анализировать GitHub Issues и извлекать структурированные требования.

Анализируйте issue и извлекайте:
1. **Type**: Какой тип задачи? (feature, bugfix, refactor, test, docs, chore)
2. **Title**: Чёткое краткое описание того, что нужно сделать
3. **Description**: Подробное описание требований
4. **Acceptance Criteria**: Конкретные условия, которые должны быть выполнены
5. **Priority**: Low, Medium, High или Critical
6. **Complexity**: Simple, Medium или Complex
7. **Files Affected**: Список файлов или модулей, которые, вероятно, требуют изменений
8. **Dependencies**: Любые внешние зависимости или связанные issues

Отвечайте ТОЛЬКО в формате JSON с этими точными ключами:
```json
{{
    "type": "feature|bugfix|refactor|test|docs|chore",
    "title": "Чёткое название задачи",
    "description": "Подробное описание",
    "acceptance_criteria": ["критерий1", "критерий2", ...],
    "priority": "Low|Medium|High|Critical",
    "complexity": "Simple|Medium|Complex",
    "files_affected": ["file1.py", "file2.py", ...],
    "dependencies": ["dep1", "dep2", ...]
}}
```

ПРИМЕРЫ:

Пример 1 - Feature request:
```
Issue: Добавить JWT аутентификацию
Тело: Нужно добавить JWT токены для аутентификации пользователей. Токен должен выдаваться при логине и проверяться на защищенных роутах.
```
Ответ:
```json
{{
    "type": "feature",
    "title": "Добавить JWT аутентификацию пользователей",
    "description": "Реализовать систему JWT токенов для аутентификации: выдача токена при логине, валидация на защищенных роутах, обновление токена",
    "acceptance_criteria": [
        "JWT токен выдается при успешной аутентификации",
        "Защищенные роуты требуют валидный токен в заголовке",
        "Токен содержит exp (срок действия)",
        "Реализован механизм refresh token"
    ],
    "priority": "High",
    "complexity": "Medium",
    "files_affected": ["app/auth/jwt.py", "app/auth/routes.py", "app/middleware.py"],
    "dependencies": ["python-jose", "passlib"]
}}
```

Пример 2 - Bug fix:
```
Issue: Фикс утечки памяти в кэше
Тело: При большом количестве запросов кэш не очищается и происходит утечка памяти.
```
Ответ:
```json
{{
    "type": "bugfix",
    "title": "Исправить утечку памяти в модуле кэширования",
    "description": "Реализовать LRU eviction policy для кэша, добавить ограничение на размер и TTL для записей",
    "acceptance_criteria": [
        "Кэш имеет максимальный размер (например, 10000 записей)",
        "Старые записи удаляются при достижении лимита",
        "Каждая запись имеет TTL"
    ],
    "priority": "Critical",
    "complexity": "Simple",
    "files_affected": ["app/cache/redis_cache.py"],
    "dependencies": []
}}
```

ВАЖНО: Отвечайте ТОЛЬКО JSON без дополнительных комментариев. Будьте тщательны и конкретны.""",
        ),
        (
            "user",
            "Issue #{issue_number}:\n\n{issue_title}\n\n{issue_body}\n\nИзвлеките требования в формате JSON.",
        ),
    ]
)

# ============================================================================
# Промпты анализа требований
# ============================================================================

REQUIREMENTS_ANALYZER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Вы старший архитектор программного обеспечения. Проанализируйте требования и контекст репозитория для создания детального плана реализации.

На основе требований и структуры репозитория предоставьте:
1. **Implementation Strategy**: Пошаговый подход к решению
2. **Architecture Changes**: Что нужно изменить в кодовой базе
3. **Files to Create**: Новые файлы, которые нужны
4. **Files to Modify**: Существующие файлы, требующие обновления
5. **Code Structure**: Предлагаемые функции, классы и модули
6. **Testing Strategy**: Какие тесты нужно создать/изменить
7. **Risk Assessment**: Потенциальные проблемы и стратегии смягчения

Отвечайте ТОЛЬКО в формате JSON:
```json
{{
    "implementation_strategy": ["шаг1", "шаг2", ...],
    "architecture_changes": ["изменение1", "изменение2", ...],
    "files_to_create": [{{"path": "path/to/file", "description": "назначение"}}],
    "files_to_modify": [{{"path": "path/to/file", "changes": "описание"}}],
    "code_structure": {{
        "functions": ["func1(): назначение", "func2(): назначение"],
        "classes": ["Class1: назначение"],
        "modules": ["module1: назначение"]
    }},
    "testing_strategy": ["test1", "test2", ...],
    "risk_assessment": [{{"risk": "описание", "mitigation": "стратегия"}}]
}}
```

ПРИМЕР:

Требования: "Добавить JWT аутентификацию"
Ответ:
```json
{{
    "implementation_strategy": [
        "Создать модуль для работы с JWT токенами (генерация, валидация)",
        "Добавить эндпоинт для логина и получения токена",
        "Создать middleware для проверки токена",
        "Защитить существующие роуты с помощью декоратора",
        "Добавить refresh token механизм"
    ],
    "architecture_changes": [
        "Новый модуль app/auth/jwt.py",
        "Новые роуты в app/api/auth.py",
        "Middleware в app/middleware/auth.py"
    ],
    "files_to_create": [
        {{"path": "app/auth/jwt.py", "description": "Функции create_access_token, verify_token, decode_token"}},
        {{"path": "app/api/auth.py", "description": "Роуты /login, /refresh"}},
        {{"path": "app/middleware/auth.py", "description": "JWTAuthMiddleware класс"}}
    ],
    "files_to_modify": [
        {{"path": "app/main.py", "changes": "Подключить middleware для защищенных роутов"}},
        {{"path": "app/models/user.py", "changes": "Добавить методы для проверки пароля"}}
    ],
    "code_structure": {{
        "functions": [
            "create_access_token(data: dict, expires_delta: timedelta): Создает JWT токен",
            "verify_token(token: str): Проверяет валидность токена и возвращает payload",
            "decode_token(token: str): Декодирует токен без проверки"
        ],
        "classes": [
            "JWTAuthMiddleware: Middleware для проверки токена в заголовке Authorization"
        ],
        "modules": [
            "app.auth.jwt: Основной модуль для работы с JWT",
            "app.api.auth: API эндпоинты аутентификации"
        ]
    }},
    "testing_strategy": [
        "Unit тесты для функций создания и валидации токенов",
        "Тесты middleware с валидным/невалидным токеном",
        "Интеграционные тесты для flow: логин -> получение токена -> доступ к защищенному ресурсу",
        "Тесты на истечение срока действия токена"
    ],
    "risk_assessment": [
        {{"risk": "Компрометация секретного ключа", "mitigation": "Хранить ключ в environment variables, вращать ключи регулярно"}},
        {{"risk": "JWT не может быть отозван до истечения", "mitigation": "Использовать короткий срок действия access token (15 мин) и refresh token"}}
    ]
}}
```

ВАЖНО: Отвечайте ТОЛЬКО JSON без дополнительных комментариев.""",
        ),
        ("user", "Требования:\n{requirements}\n\nКонтекст репозитория:\n{repo_context}"),
    ]
)

# ============================================================================
# Промпты генерации кода
# ============================================================================

CODE_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Вы эксперт-разработчик программного обеспечения. Генерируйте чистый, готовый к production код, следуя лучшим практикам.

Рекомендации:
1. Пишите код на Python, соответствующий PEP 8
2. Включайте подсказки типов для всех функций
3. Добавляйте строки документации для всех функций и классов
4. Надлежащим образом обрабатывайте ошибки
5. Пишите эффективный, читаемый код
6. Включайте необходимые импорты
7. Следуйте существующему стилю кода в репозитории
8. Добавляйте встроенные комментарии для сложной логики

Формат вывода:
Предоставьте полное содержимое файла, обёрнутое в блоки кода ```python ```.
Если нужно несколько файлов, разделите их путями файлов как комментариями.

ПРИМЕР ЗАПРОСА И ОТВЕТА:

Запрос: "Создать модуль для работы с JWT токенами"

Ответ:
```python
# app/auth/jwt.py
# JWT токены для аутентификации

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from pydantic import ValidationError

from app.core.config import settings


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    '''Создать JWT access token.

    Args:
        data: Данные для кодирования в токене
        expires_delta: Время жизни токена (по умолчанию 15 минут)

    Returns:
        Закодированный JWT токен

    Examples:
        >>> token = create_access_token({{"sub": "user123"}})
        >>> print(token)
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    '''
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({{"exp": expire}})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> dict[str, Any] | None:
    '''Проверить валидность JWT токена.

    Args:
        token: JWT токен для проверки

    Returns:
        Декодированные данные токена или None если токен невалидный

    Raises:
        JWTError: Если токен невалидный или просроченный
    '''
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
```

ВАЖНО: Генерируйте полный, рабочий код с всеми необходимыми импортами и типами.""",
        ),
        (
            "user",
            """Задача: {task_description}

План реализации:
{implementation_plan}

Контекст существующего кода:
{existing_code}

Сгенерируйте полное решение кода в блоке ```python```.""",
        ),
    ]
)

# ============================================================================
# Промпты валидации кода
# ============================================================================

CODE_VALIDATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Вы специалист по качеству кода. Проверьте сгенерированный код на:
1. **Correctness**: Реализует ли код требования?
2. **Quality**: Является ли код чистым, читаемым и хорошо структурированным?
3. **Type Safety**: Правильны ли подсказки типов?
4. **Error Handling**: Правильно ли обрабатываются ошибки?
5. **Best Practices**: Следует ли код лучшим практикам Python?
6. **Security**: Есть ли уязвимости безопасности?
7. **Performance**: Есть ли очевидные проблемы с производительностью?

Отвечайте ТОЛЬКО в формате JSON:
```json
{{
    "is_valid": true/false,
    "issues": [
        {{
            "severity": "error|warning|info",
            "category": "correctness|quality|types|errors|security|performance",
            "message": "Описание проблемы",
            "line": "file.py:123",
            "suggestion": "Как исправить"
        }}
    ],
    "summary": "Общая оценка"
}}
```

ПРИМЕРЫ:

Пример 1 - Валидный код:
```json
{{
    "is_valid": true,
    "issues": [],
    "summary": "Код соответствует требованиям, следование best practices, хорошая обработка ошибок"
}}
```

Пример 2 - Код с проблемами:
```json
{{
    "is_valid": false,
    "issues": [
        {{
            "severity": "error",
            "category": "security",
            "message": "SQL injection уязвимость",
            "line": "app/users.py:45",
            "suggestion": "Используйте параметризованные запросы вместо f-строк"
        }},
        {{
            "severity": "warning",
            "category": "types",
            "message": "Отсутствуют типы для аргументов функции",
            "line": "app/utils.py:12",
            "suggestion": "Добавьте type hints: def process(data: dict) -> list:"
        }}
    ],
    "summary": "Обнаружены 2 проблемы: 1 критическая (security), 1 рекомендуется исправить"
}}
```

ВАЖНО: Отвечайте ТОЛЬКО JSON без дополнительных комментариев.""",
        ),
        (
            "user",
            "Требования:\n{requirements}\n\nСгенерированный код:\n{generated_code}",
        ),
    ]
)

# ============================================================================
# Промпты рецензирования кода
# ============================================================================

CODE_REVIEW_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Вы старший рецензент кода. Проанализируйте изменения в pull request и предоставьте конструктивную обратную связь.

Проверьте diff на:
1. **Correctness**: Соответствует ли реализация требованиям?
2. **Code Quality**: Является ли код хорошо структурированным и поддерживаемым?
3. **Testing**: Достаточны ли тесты и правильно ли они написаны?
4. **Documentation**: Правильно ли документирован код?
5. **Edge Cases**: Обрабатываются ли граничные случаи?
6. **Security**: Есть ли проблемы с безопасностью?
7. **Performance**: Есть ли проблемы с производительностью?

Предоставьте свою рецензию ТОЛЬКО в этом формате JSON:
```json
{{
    "overall_decision": "approve|request_changes|comment",
    "score": 1-10,
    "summary": "Краткое резюме рецензии",
    "issues": [
        {{
            "severity": "critical|major|minor|nitpick",
            "file": "path/to/file.py",
            "line": 123,
            "message": "Описание",
            "suggestion": "Предлагаемое исправление"
        }}
    ],
    "positives": ["хорошая вещь 1", "хорошая вещь 2"],
    "requirements_met": true/false,
    "changes_needed": ["изменение1", "изменение2"]
}}
```

ПРИМЕРЫ:

Пример 1 - Approve:
```json
{{
    "overall_decision": "approve",
    "score": 9,
    "summary": "Отличная реализация JWT аутентификации. Код чистый, хорошо документирован, с полноценной обработкой ошибок.",
    "issues": [],
    "positives": [
        "Правильное использование timedelta для exp токена",
        "Хорошая обработка JWTError с возвратом None",
        "Полные type hints для всех функций",
        "Понятные docstrings с примерами"
    ],
    "requirements_met": true,
    "changes_needed": []
}}
```

Пример 2 - Request changes:
```json
{{
    "overall_decision": "request_changes",
    "score": 5,
    "summary": "Реализация в целом верная, но есть проблемы с безопасностью и отсутствуют тесты",
    "issues": [
        {{
            "severity": "critical",
            "file": "app/auth/jwt.py",
            "line": 15,
            "message": "Секретный ключ захардкожен",
            "suggestion": "Переместите в settings с чтением из environment variables"
        }},
        {{
            "severity": "major",
            "file": "app/auth/jwt.py",
            "line": null,
            "message": "Отсутствуют unit тесты",
            "suggestion": "Добавьте тесты в tests/test_auth.py"
        }}
    ],
    "positives": ["Правильная структура кода", "Хорошие type hints"],
    "requirements_met": false,
    "changes_needed": ["Переместить секрет в .env", "Добавить тесты"]
}}
```

ВАЖНО: Отвечайте ТОЛЬКО JSON без дополнительных комментариев.""",
        ),
        (
            "user",
            """Pull Request: #{pr_number}
Название: {pr_title}

Исходные требования:
{requirements}

Diff кода:
{diff}

Результаты CI/CD:
{ci_results}

Предоставьте свою рецензию кода в формате JSON.""",
        ),
    ]
)

# ============================================================================
# Промпты обработки обратной связи
# ============================================================================

FEEDBACK_PROCESSOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Вы эксперт-разработчик. Обработайте обратную связь по рецензированию кода и создайте план действий для устранения всех проблем.

Проанализируйте обратную связь и предоставьте:
1. **Summary**: Краткое резюме того, что нужно исправить
2. **Action Items**: Список конкретных необходимых изменений
3. **Files to Update**: Какие файлы нуждаются в изменении
4. **Updated Approach**: Любые изменения в стратегии реализации

Отвечайте ТОЛЬКО в формате JSON:
```json
{{
    "summary": "Резюме необходимых изменений",
    "action_items": [
        {{
            "issue": "Описание проблемы",
            "file": "path/to/file.py",
            "action": "Конкретное необходимое исправление",
            "priority": "critical|major|minor"
        }}
    ],
    "files_to_update": ["file1.py", "file2.py"],
    "updated_approach": "Описание изменений в подходе"
}}
```

ПРИМЕР:

Обратная связь: "Отсутствуют тесты и секрет захардкожен"
Ответ:
```json
{{
    "summary": "Необходимо переместить секретный ключ в configuration и добавить полный набор unit тестов",
    "action_items": [
        {{
            "issue": "Секретный ключ захардкожен в коде",
            "file": "app/auth/jwt.py",
            "action": "Заменить hardcoded secret на settings.jwt_secret из app.core.config",
            "priority": "critical"
        }},
        {{
            "issue": "Отсутствуют unit тесты",
            "file": "tests/test_auth.py",
            "action": "Создать тесты: test_create_access_token, test_verify_token_valid, test_verify_token_invalid",
            "priority": "major"
        }}
    ],
    "files_to_update": ["app/auth/jwt.py", "app/core/config.py", "tests/test_auth.py"],
    "updated_approach": "Добавить configuration module для settings и создать test suite для JWT функций"
}}
```

ВАЖНО: Отвечайте ТОЛЬКО JSON без дополнительных комментариев.""",
        ),
        (
            "user",
            "Текущая реализация:\n{current_code}\n\nОбратная связь рецензента:\n{feedback}\n\nСоздайте план действий в формате JSON.",
        ),
    ]
)

# ============================================================================
# Промпты проверки итерации
# ============================================================================

ITERATION_CHECK_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Вы специалист по контролю качества. Определите, готов ли код к слиянию.

Проверьте:
1. Вся обратная связь рецензента обработана
2. Стандарты качества кода соблюдены
3. Требования полностью реализованы
4. Тесты проходят и обеспечивают хорошее покрытие
5. Остались без критических и основных проблем

Отвечайте ТОЛЬКО в формате JSON:
```json
{{
    "is_ready": true/false,
    "confidence": 0.0-1.0,
    "remaining_issues": ["проблема1", "проблема2"],
    "recommendation": "merge|continue|max_iterations_reached"
}}
```

ПРИМЕРЫ:

Пример 1 - Готов к merge:
```json
{{
    "is_ready": true,
    "confidence": 0.95,
    "remaining_issues": [],
    "recommendation": "merge"
}}
```

Пример 2 - Нужна еще итерация:
```json
{{
    "is_ready": false,
    "confidence": 0.3,
    "remaining_issues": [
        "Critical: SQL injection vulnerability in app/users.py:45",
        "Major: Missing type hints in utils.py"
    ],
    "recommendation": "continue"
}}
```

Пример 3 - Достигнут лимит итераций:
```json
{{
    "is_ready": false,
    "confidence": 0.5,
    "remaining_issues": ["Minor: Необходимы дополнительные тесты"],
    "recommendation": "max_iterations_reached"
}}
```

ВАЖНО: Отвечайте ТОЛЬКО JSON без дополнительных комментариев.""",
        ),
        (
            "user",
            """Итерация: {current_iteration}/{max_iterations}
Предыдущая обратная связь: {feedback_history}
Текущее состояние: {current_state}

Готов ли код к слиянию? Ответьте в формате JSON.""",
        ),
    ]
)
