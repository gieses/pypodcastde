FROM python:3.14-alpine AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md locations_example.txt ./
COPY pypodcastde/ pypodcastde/
RUN uv sync --locked --no-dev --no-editable --no-cache --no-python-downloads

FROM python:3.14-alpine
ENV PYTHONUNBUFFERED=1 PYPODCASTDE_OUTPUT_ROOT=/data
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN apk add --no-cache cmd:ffmpeg cmd:ffprobe \
    && ffmpeg -version >/dev/null \
    && ffprobe -version >/dev/null
COPY --from=builder /app/.venv /app/.venv
ENTRYPOINT ["pypodcastde"]
CMD ["mine"]
