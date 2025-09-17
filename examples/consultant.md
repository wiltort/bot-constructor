# Пример "Консультант"
## Описание бота
Телеграм бот "Консультант предоставляющий информацию по услугам компании".
Анализирует предоставленные данные по услугам компании и на основе анализа и истории сообщений отвечает на вопросы.

## Создание через API
### 1. Создание бота:
```bash
curl -X POST http://localhost:8000/api/v1/bots/ \
  -H "Authorization: Token your-drf-token" \
  -H "Content-Type: application/json"
  -d '{
    "name": "Консультант",
    "description": "Консультант предоставляющий информацию по услугам компании",
    "gpt_api_key": "API-ключ-для-соответсвующей-платформы",
    "gpt_api_url": "openrouter",
    "ai_model": "tngtech/deepseek-r1t2-chimera:free",
    "telegram_token": "Токен-полученный-от-BotFather"
  }'
```
В этом примере используется AI платформа [openrouter](https://openrouter.ai/).
Список доступных платформ хранится в переменной AVAILABLE_GPT_API_URLS в [settings](../src/bot_constructor/settings.py)
### Процесс получения API ключа на OpenRouter.ai
- Регистрация на платформе
    - Перейдите на сайт: https://openrouter.ai/
    - Нажмите "Sign Up" в правом верхнем углу
    - Выберите способ регистрации:
        - Через Google аккаунт
        - Через GitHub аккаунт
        - Через email (нужно подтвердить email адрес)
- Получение API ключа
    - После входа в аккаунт перейдите в раздел "Keys" в верхнем меню
    - Нажмите "Create a key"
    - Введите название ключа (например, "My Bot Project")
    - Выберите разрешения (обычно оставляйте по умолчанию)
    - Нажмите "Create" - ключ будет сгенерирован
- Для интеграции с вашим ботом изучите:
    - API документацию: https://openrouter.ai/docsd
    - Доступные модели: https://openrouter.ai/models

### 2. Создание сценария
```bash
curl -X POST http://localhost:8000/api/v1/scenarios/ \
  -H "Authorization: Token your-drf-token" \
  -H "Content-Type: application/json"
  -d '{
    "title": "Консультация",
    "scenario_type": "CS"
  }'
```
### 3. Создание шагов сценария

```bash
curl -X POST http://localhost:8000/api/v1/scenarios/{scenario_id}/steps/ \
  -H "Authorization: Token your-drf-token" \
  -H "Content-Type: application/json"
  -d '{
    "title": "Приветствие",
    "is_active": true,
    "is_using_ai": false,
    "is_entry_point": true,
    "is_fallback": false,
    "is_end": false,
    "result_state": "CATEGORY",
    "template": "ST",
    "priority": 1,
    "message": "Вас приветствует ИИ консультант компании 'МегаЗвон'",
    "handler_data": {"keyboard": [["Помощь", "Контакты", "О компании"]]}
  }'
```

```bash
curl -X POST http://localhost:8000/api/v1/scenarios/{scenario_id}/steps/ \
  -H "Authorization: Token your-drf-token" \
  -H "Content-Type: application/json"
  -d '{
    "title": "Помощь",
    "is_active": true,
    "is_using_ai": false,
    "is_entry_point": false,
    "is_fallback": false,
    "is_end": false,
    "on_state": "CATEGORY"
    "result_state": "HELP",
    "template": "QU",
    "priority": 2,
    "message": "Готов вам помочь, опишите свою проблему или задайте вопрос о наши продуктах или услугах",
    "handler_data": {
        "keyboard": [["Помощь", "Контакты", "О компании"]],
        "filter_regex": "Помощь"
    }
  }'
```

```bash
curl -X POST http://localhost:8000/api/v1/scenarios/{scenario_id}/steps/ \
  -H "Authorization: Token your-drf-token" \
  -H "Content-Type: application/json"
  -d '{
    "title": "Решение",
    "is_active": true,
    "is_using_ai": true,
    "is_entry_point": false,
    "is_fallback": false,
    "is_end": false,
    "on_state": "HELP"
    "result_state": "HELP",
    "template": "QU",
    "priority": 2,
    "message": "Готов вам помочь, опишите свою проблему или задайте вопрос о наши продуктах или услугах",
    "handler_data": {
        "keyboard": [["Помощь", "Контакты", "О компании"]],
        "filter_regex": "Помощь"
    }
  }'
```
