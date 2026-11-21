FROM python:3.14-alpine
ENV PYTHONUNBUFFERED=1 PYPODCASTDE_OUTPUT_ROOT=/data
WORKDIR /app
RUN apk add --no-cache ffmpeg
COPY pyproject.toml locations_example.txt ./
COPY pypodcastde/ pypodcastde/
RUN pip install --no-cache-dir .
ENTRYPOINT ["pypodcastde"]
CMD ["mine"]
