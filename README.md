<img src="assets/logo.svg" alt="A smiling cassette in teal headphones with floating musical notes" width="150" height="150">

# pypodcastde

[![CI tests](https://github.com/gieses/pypodcastde/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/gieses/pypodcastde/actions/workflows/ci.yml?query=branch%3Amain)
[![Minimum line coverage: 70%](https://img.shields.io/badge/coverage%20floor-70%25-39824a)](pyproject.toml)
[![Python 3.11 and newer](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](compose.example.yaml)

One of the best things about German public broadcasting is how seriously it takes kids’ questions. On [ARD Sounds](https://www.ardsounds.de/), *Lachlabor* tests them with real experiments, while *Ohrenbär* has stories for the quieter end of the day. Over in the [ARD Mediathek](https://www.ardmediathek.de/), Checkerin Marina solves puzzles on screen.

pypodcastde keeps those favourites in one folder, ready for a car ride or bedtime. Podcasts keep their original audio format; for video shows, it saves the soundtrack as an MP3. This is an independent tool, not an ARD app.

## Your first download

You'll need Python 3.11+ and [uv](https://docs.astral.sh/uv/). For video shows, install `ffmpeg` and `ffprobe` too. From the project folder:

```bash
uv sync --locked
uv run pypodcastde init-config       # Once. Won't overwrite your settings.
# Edit locations_local.txt to pick shows and folders.
uv run pypodcastde mine --try        # See what would download.
uv run pypodcastde mine              # Download it.
```

The first run can fetch a show's whole back catalogue. Later runs skip episodes you already have.

### Shows and folders

[`locations_example.txt`](locations_example.txt) lists eight shows. Edit your **private copy**, `locations_local.txt`. Keep the header and separate the show name, folder, and URL with semicolons. Delete rows for shows you don't want.

| Where you store episodes | Example folder for one show |
| --- | --- |
| Beside the settings file (Windows or Linux) | `podcasts/Lachlabor` |
| Windows drive or share | `D:\Podcasts\Lachlabor` or `\\server\share\Podcasts\Lachlabor` |
| Linux drive or mounted share | `/srv/podcasts/Lachlabor` |

The CLI looks for the private file in the current directory. Use `--config PATH` if you keep it elsewhere. To move the whole library without editing each row, use `--output-root DIR`: each show keeps its last folder name under `DIR`. Git ignores the private file and the default `podcasts/` folder.

## Daily downloads with Docker

On a Linux server with Docker Compose, the image handles FFmpeg for you:

```bash
mkdir -p config
cp -n locations_example.txt config/locations_local.txt
cp -n compose.example.yaml compose.yaml
# Edit compose.yaml: point /srv/podcasts at your writable library folder.
# If it's on a NAS, mount it before starting Docker.
docker compose up --build -d
docker compose logs -f crawler
```

The crawler runs immediately, then every 24 hours. It rereads `config/locations_local.txt` each time. Each run ends with a count of successful and failed shows. `Ctrl+C` leaves the log viewer; `docker compose stop` stops the crawler. Downloads stay on the host.

## Updating

Use `mine --force --try` to preview a full re-download. Drop `--try` to replace existing episodes. Don't run two crawlers against the same folder at once.

```bash
git pull --ff-only
uv sync --locked                                  # For a local install
# Or, for Docker:
docker compose build --pull && docker compose up -d
```

See the [changelog](CHANGELOG.md) for release notes. If you're working on the code, `make check` runs lint and tests; `make help` lists the other commands.

Run `make hooks` once to enable pre-commit checks, or `make pre-commit` to check the whole tree. Use `uv add` (or `uv add --dev`) for dependency changes and commit `uv.lock`. CI and Docker use the locked versions.
