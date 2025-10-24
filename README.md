# Bot Constructor - Система управления Telegram ботами

Система для создания, управления и запуска множества Telegram ботов с интеграцией ChatGPT/Deepseek/Openrouter, с веб-интерфейсом и API.

## Возможности

- **Управление множеством ботов** - запуск, остановка, мониторинг
- **REST API** - полное API для интеграции
- **Панель управления** - веб-интерфейс для администрирования
- **Асинхронная обработка** - Celery для фоновых задач
- **Масштабируемость** - Docker контейнеризация

## Архитектура

```
Django + DRF (Web Interface) → Celery (Task Queue) → python-telegram-bot (Bot Runtime)
       ↓                              ↓
 PostgreSQL (Data)           Redis (Broker)
```

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/Wiltort/bot-constructor.git
cd bot-constructor
cp .env.example .env
```

### 2. Настройка переменных окружения (.env)

```env
# Django settings
FIELD_ENCRYPTION_KEY=generated-key
SECRET_KEY=your-secret-django-key
DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL Settings
DB_NAME=telegram_bots
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis Settings
REDIS_URL=redis://localhost:6379/0
```
Для генерации правильного FIELD_ENCRYPTION_KEY используйте keygen
```bash
python keygen.py
```
Полученную строку без кавычек вставляем в .env
### 3. Запуск через Docker

```bash
docker compose up --build
```

Сервисы будут доступны:
- **API Documentation**: http://localhost:8000/api/swagger/
- **Admin Panel**: http://localhost:8000/admin/

### 4. Создание суперпользователя

```bash
docker-compose exec uv run manage.py createsuperuser
```

## API Endpoints

### Аутентификация
- `POST /api/token-auth/` - получение токена аутентификации DRF

### Боты
- `GET /api/v1/bots/` - список ботов
- `POST /api/v1/bots/{id}/start/` - запуск бота
- `POST /api/v1/bots/{id}/stop/` - остановка бота
- `GET /api/v1/bots/{id}/status/` - статус бота

### Сценарии
- `GET /api/v1/scenarios/` - список сценариев
- `POST /api/v1/scenarios/{id}/steps/` - создание шага
- `GET /api/v1/scenarios/{id}/steps/` - шаги сценария

Полный список ендпойнтов находится в документации http://localhost:8000/api/swagger/
Для всех запросов изменения/добавления/удаления требуется авторизация, токен аутентификации
 можно получить в админке или по эндпойнту api/token-auth/ 

### Примеры ботов:
[Консультант по услугам](./examples/consultant.md)

## 🔧 Управление ботами

### Через веб-интерфейс
1. Откройте http://localhost:8000/admin/
2. Авторизуйтесь как суперпользователь
3. Перейдите в раздел "Bots"
4. Создайте бота с токеном

### Через API
```python
import requests

API_URL = "http://localhost:8000/api/v1"
TOKEN = "your-api-token"

# Запуск бота
response = requests.post(
    f"{API_URL}/bots/1/start/",
    headers={"Authorization": f"Token {TOKEN}"}
)
```

```bash
curl -X POST http://localhost:8000/api/v1/bots/1/start/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json"
```

## Docker Команды

```bash
# Запуск всех сервисов
docker compose up --build

# Остановка
docker compose down

# Выполнение команд в контейнере
docker-compose exec web uv run src/manage.py migrate
docker-compose exec web uv run src/manage.py createsuperuser
```

## Разработка

### Установка для разработки
```bash
pip install uv
uv sync
# Зависимости проекта находятся в pyproject.toml в разделе dependencies
```
## Демонстрация
Развернуто на http://89.104.71.118/api/swagger/ 
