# pypodcastde

Save ARD podcasts to a folder on your computer or NAS. Audio shows keep their original format. For video shows, such as Checkerin Marina, the crawler saves the soundtrack as an MP3.

## TL;DR: download missing episodes

From the project folder, with [uv](https://docs.astral.sh/uv/) installed:

```bash
uv sync --locked
uv run pypodcastde init-config       # Once. Won't overwrite your settings.
# Edit locations_local.txt to pick shows and folders.
uv run pypodcastde mine --try        # See what would download.
uv run pypodcastde mine              # Download it.
```

Use Python 3.11 or newer. Video downloads also need `ffmpeg` and `ffprobe` on your PATH. The first run can download a show's entire back catalogue.

## Choose where episodes go

[`locations_example.txt`](locations_example.txt) lists eight shows. Edit your **private copy**, `locations_local.txt`. Keep the header and separate the show name, folder, and URL with semicolons. Delete rows for shows you don't want.

| Where you store episodes | Example folder for one show |
| --- | --- |
| Beside the settings file (Windows or Linux) | `podcasts/Lachlabor` |
| Windows drive or share | `D:\Podcasts\Lachlabor` or `\\server\share\Podcasts\Lachlabor` |
| Linux drive or mounted share | `/srv/podcasts/Lachlabor` |

The CLI looks for the private file in the current directory. Use `--config PATH` if you keep it elsewhere. To move the whole library without editing each row, use `--output-root DIR`: each show keeps its last folder name under `DIR`. Git ignores the private file and the default `podcasts/` folder.

## TL;DR: run daily on a Linux server

Install Docker with Compose. From the project folder:

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

## Repairs and updates

Use `mine --force --try` to preview a full re-download. Drop `--try` to replace existing episodes. Don't run two crawlers against the same folder at once.

```bash
git pull --ff-only
uv sync --locked                                  # For a local install
# Or, for Docker:
docker compose build --pull && docker compose up -d
```

For development, `make help` lists the commands. `make check` runs Ruff and the offline tests; `make hooks` installs the Git pre-commit hook.

GitHub Actions runs pytest on Linux and Windows with Python 3.11 and 3.14 for every push and pull request. To run the same tests locally: `uv run --locked pytest -q`.
