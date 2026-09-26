# Backend image for Render (free web service) or any container host.
# The server never executes user or model code (that happens in the browser), so it needs
# no sandboxing and runs fine on the smallest instance.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/uv
RUN useradd -m -u 1000 user
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY cotutor ./cotutor
RUN uv sync --frozen --no-dev

USER user
ENV PATH="/app/.venv/bin:$PATH" \
    COTUTOR_CACHE_DIR=/tmp/cotutor-cache \
    PYTHONUNBUFFERED=1
EXPOSE 7860
# Hosts like Render pass the port in $PORT; default to 7860 elsewhere.
CMD ["sh", "-c", "exec uvicorn cotutor.server.app:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips '*'"]
