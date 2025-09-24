# Образ Debian bookworm с предустановленными python3.11 и uv (менеджер пакетов)
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app


ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Установка netcat для health checks
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Устанавливаем только зависимости
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Теперь копируем весь проект
COPY . /app

# Теперь доустановить project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# включаем venv в PATH
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []
EXPOSE 8000

COPY entrypoint.sh entrypoint-prod.sh /
RUN chmod +x /entrypoint.sh /entrypoint-prod.sh

# По умолчанию для разработки
CMD ["/entrypoint.sh"]

