# FastAPI/Django Dockerfile using uv
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Явно явно использовать локальный venv в директории проекта (.venv)
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Устанавливаем только зависимости
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Теперь копируем весь проект
COPY . /app

# Теперь доустановить project dependencies (если депсы внутри проекта)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Только теперь включаем venv в PATH (чтобы всё работало в интерактиве и docker exec)
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []
EXPOSE 8000

# Django
CMD ["python", "src/manage.py", "runserver", "0.0.0.0:8000"]
# или FastAPI
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Для celery сервисов в docker-compose:
# command: ["celery", "-A", "your_app", "worker", "-l", "info"]