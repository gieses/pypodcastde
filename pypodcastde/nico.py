"""Download the MP3 edition of Alle gegen Nico and keep an index in episodes.json."""

import argparse
import hashlib
import http.client
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from loguru import logger

from .catalogue import Audio, Episode
from .checkpod import download, graphql
from .modes import add_mode_options
from .reporting import configure_logging, report_run

SHOW_ID = "urn:ard:show:0305ba2e345adbb5"
SHOW_PREFIX = "Alle gegen Nico"
OUT_DIR = Path("podcasts") / "Alle-gegen-Nico"
PAGE_SIZE = 50


def fetch_episodes() -> list[Episode]:
    """Collect distinct episodes oldest first and verify the catalogue is complete."""
    episodes = {}
    cursor = None
    seen_cursors = set()
    expected_count = None
    while True:
        show = graphql({"id": SHOW_ID, "first": PAGE_SIZE, "after": cursor})["show"]
        if show is None:
            raise RuntimeError(f"ARD show not found: {SHOW_ID}")
        items = show["items"]
        if expected_count is None:
            expected_count = items["totalCount"]
        for episode in items["nodes"]:
            episodes[episode["id"]] = episode
        page = items["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]
        if not cursor or cursor in seen_cursors:
            raise RuntimeError("ARD returned an invalid or repeated pagination cursor")
        seen_cursors.add(cursor)
    if len(episodes) != expected_count:
        raise RuntimeError(
            f"Incomplete ARD catalogue: expected {expected_count}, got {len(episodes)}"
        )
    return sorted(episodes.values(), key=lambda ep: (ep["publishDate"], ep["id"]))


def clean_title(title: str) -> str:
    """Strip the Nico prefix and normalize title separators for local storage."""
    title = re.sub(r"^\s*Alle gegen Nico\s*[:|\-–]?\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*[/\\|:]\s*", " - ", title)
    title = re.sub(r'[<>"?*\x00-\x1f]', "", title)
    return re.sub(r"\s+", " ", title).strip(" .")[:140].rstrip(" .") or "Unbenannt"


def episode_filename(episode: Episode, used_names: set[str]) -> str:
    """Reserve an MP3 filename, using an episode-ID suffix to resolve title collisions."""
    stem = f"{SHOW_PREFIX} - {episode['publishDate'][:10]} - {clean_title(episode['title'])}"
    name = f"{stem}.mp3"
    if name.casefold() in used_names:
        suffix = hashlib.sha256(episode["id"].encode()).hexdigest()[:12]
        name = f"{stem} ({suffix}).mp3"
    if name.casefold() in used_names:
        raise RuntimeError(f"Duplicate filename for episode {episode['id']}")
    used_names.add(name.casefold())
    return name


def mp3_urls(audios: list[Audio] | None) -> list[str]:
    """List distinct MP3 URLs in fallback order, excluding other audio formats."""
    urls = []
    for audio in audios or []:
        for url in (audio.get("downloadUrl"), audio.get("url")):
            if not url:
                continue
            suffix = Path(urlsplit(url).path).suffix.lower()
            mime = (audio.get("mimeType") or "").lower().split(";")[0].strip()
            is_mp3 = suffix == ".mp3" or (not suffix and mime in {"audio/mp3", "audio/mpeg"})
            if is_mp3 and url not in urls:
                urls.append(url)
    return urls


def main() -> int:
    """Run the standalone Nico downloader and report its exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", type=Path, default=OUT_DIR)
    add_mode_options(parser)
    args = parser.parse_args()
    configure_logging()
    with report_run(args.dry_run, args.force) as summary:
        summary.crawl(SHOW_PREFIX, lambda: mine(args.out, args.dry_run, force=args.force))
    return summary.status


def mine(out: Path, dry_run: bool, *, force: bool = False) -> int:
    """Preview or save available Nico MP3s and index successful files outside preview mode."""
    episodes = fetch_episodes()
    logger.info("Found {} episodes", len(episodes))
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)

    metadata = []
    used_names = set()
    failed = downloaded = skipped = unavailable = planned = 0
    for episode in episodes:
        name = episode_filename(episode, used_names)
        urls = mp3_urls(episode.get("audios"))
        if not urls:
            unavailable += 1
            logger.warning("No MP3 available: {}", episode["title"])
            continue
        target = out / name
        existing = target.is_file() and target.stat().st_size > 0
        if existing and not force:
            skipped += 1
        elif dry_run:
            planned += 1
            logger.info("Would download: {}", name)
            continue
        else:
            logger.info("Downloading: {}", name)
            for url in urls:
                try:
                    download(url, target)
                    downloaded += 1
                    break
                except (OSError, ValueError, http.client.HTTPException) as exc:
                    logger.warning("Audio variant failed for {}: {}", name, exc)
            else:
                failed += 1
                logger.error("All audio variants failed: {}", name)
                if not existing:
                    continue
        metadata.append(
            {
                "file": name,
                "id": episode["id"],
                "title": episode["title"],
                "publishDate": episode["publishDate"],
                "duration": episode["duration"],
                "summary": episode.get("summary"),
                "bytes": target.stat().st_size,
            }
        )

    if not dry_run:
        manifest = out / "episodes.json"
        temporary = manifest.with_suffix(".json.part")
        temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(manifest)
    logger.info(
        "Episodes | downloaded: {} | planned: {} | existing: {} | unavailable: {} | failed: {}",
        downloaded,
        planned,
        skipped,
        unavailable,
        failed,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
