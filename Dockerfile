# FastAPI/Django Dockerfile using uv
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Явно явно использовать локальный venv в директории проекта (.venv)
ENV UV_VENV_IN_PLACE=1

# Не копируйте проект до установки зависимостей (для слоёв)
COPY pyproject.toml uv.lock ./

# Устанавливаем только зависимости
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Теперь копируем весь проект
COPY . /app

# Теперь доустановить project dependencies (если депсы внутри проекта)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Только теперь включаем venv в PATH (чтобы всё работало в интерактиве и docker exec)
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT []

# Django
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# или FastAPI
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Для celery сервисов в docker-compose:
# command: ["celery", "-A", "your_app", "worker", "-l", "info"]