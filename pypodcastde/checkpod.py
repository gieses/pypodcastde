"""Download audio from ARD Sounds. When run directly, download CheckPod."""

import argparse
import hashlib
import http.client
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from loguru import logger

from .catalogue import Audio, CatalogueData, Episode
from .modes import add_mode_options
from .reporting import configure_logging, report_run

API_URL = "https://api.ardaudiothek.de/graphql"
SHOW_ID = "urn:ard:show:2af809299201a921"
SHOW_PREFIX = "CheckPod"
OUT_DIR = Path("podcasts") / "Checker_Tobi"
USER_AGENT = "Mozilla/5.0 (CheckPod crawler)"
PAGE_SIZE = 50

QUERY = """
query($id: ID!, $first: Int!, $after: Cursor) {
  show(id: $id) {
    title
    items(first: $first, after: $after, orderBy: PUBLISH_DATE_DESC) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        id title publishDate duration summary
        audios { url downloadUrl mimeType }
      }
    }
  }
}
"""


def graphql(variables: dict[str, str | int | None]) -> CatalogueData:
    """Fetch one catalogue page, raising RuntimeError on GraphQL errors."""
    body = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_episodes(show_id: str = SHOW_ID) -> list[Episode]:
    """Collect all pages newest first, rejecting unknown shows and repeated cursors."""
    episodes, cursor = [], None
    cursors = set()
    while True:
        show = graphql({"id": show_id, "first": PAGE_SIZE, "after": cursor})["show"]
        if not show:
            raise ValueError(f"ARD show not found: {show_id}")
        items = show["items"]
        episodes.extend(items["nodes"])
        if not items["pageInfo"]["hasNextPage"]:
            return episodes
        cursor = items["pageInfo"]["endCursor"]
        if not cursor or cursor in cursors:
            raise ValueError("ARD returned a missing or repeated pagination cursor")
        cursors.add(cursor)


def clean_title(title: str, prefix: str = SHOW_PREFIX) -> str:
    """Remove the show prefix and characters unsuitable for an episode filename."""
    title = re.sub(rf"^\s*{re.escape(prefix)}\s*[:\-–]?\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s*\|\s*", " - ", title)
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title)
    title = re.sub(r"\s+", " ", title).strip(" .")
    return title[:150] or "Unbenannt"


def audio_candidates(audios: list[Audio] | None) -> list[Audio]:
    """All audio variants, MP3 first; later ones are fallbacks if a URL is dead."""
    return sorted(audios or [], key=lambda a: "mp3" not in (a.get("mimeType") or ""))


def extension(audio: Audio) -> str:
    """Choose a filename suffix from the advertised media type and URL."""
    url = (audio.get("downloadUrl") or audio["url"]).split("?")[0]
    suffix = Path(url).suffix.lower()
    if "mp3" in (audio.get("mimeType") or ""):
        return ".mp3"
    return ".m4a" if suffix in (".mp4", ".m4a", "") else suffix


def download(url: str, target: Path, retries: int = 3) -> None:
    """Stream audio to a temporary file and replace the target after size verification."""
    tmp = target.with_suffix(target.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
                expected_size = resp.headers.get("Content-Length")
                received = 0
                while chunk := resp.read(1 << 16):
                    f.write(chunk)
                    received += len(chunk)
                if received == 0:
                    raise OSError("Empty audio response")
                if expected_size is not None and received != int(expected_size):
                    raise OSError(
                        f"Incomplete audio response: expected {expected_size} bytes, got {received}"
                    )
            tmp.replace(target)
            return
        except (OSError, ValueError, http.client.HTTPException) as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError as cleanup_exc:
                logger.warning("Could not remove {}: {}", tmp, cleanup_exc)
            if attempt == retries or getattr(exc, "code", None) in (403, 404, 410):
                raise
            logger.warning("Retry {}/{} for {}: {}", attempt, retries - 1, target.name, exc)
            time.sleep(2 * attempt)


def main() -> int:
    """Run the standalone CheckPod crawler with optional episode and output limits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", type=Path, default=OUT_DIR, help="output directory")
    parser.add_argument("-n", "--limit", type=int, help="only the N newest episodes")
    add_mode_options(parser)
    args = parser.parse_args()
    configure_logging()
    with report_run(args.dry_run, args.force) as summary:
        summary.crawl(
            SHOW_PREFIX,
            lambda: mine(
                SHOW_ID, SHOW_PREFIX, args.out, args.dry_run, args.limit, force=args.force
            ),
        )
    return summary.status


def mine(
    show_id: str,
    prefix: str,
    out: Path,
    dry_run: bool,
    limit: int | None = None,
    *,
    force: bool = False,
) -> int:
    """Preview or download the selected episodes; return nonzero for failed downloads."""
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)
    episodes = fetch_episodes(show_id)
    logger.info("Found {} episodes", len(episodes))
    if limit:
        episodes = episodes[:limit]

    used_names: set[str] = set()
    metadata, failed = [], 0
    downloaded = planned = skipped = unavailable = 0
    for ep in sorted(episodes, key=lambda e: e["publishDate"]):
        candidates = audio_candidates(ep["audios"])
        if not candidates:
            unavailable += 1
            logger.warning("No audio available: {}", ep["title"])
            continue
        name = f"{prefix} - {ep['publishDate'][:10]} - {clean_title(ep['title'], prefix)}"
        if name.lower() in used_names:
            name += f" ({hashlib.sha256(ep['id'].encode()).hexdigest()[:12]})"
        used_names.add(name.lower())

        entry = {
            "file": None,
            "id": ep["id"],
            "title": ep["title"],
            "publishDate": ep["publishDate"],
            "duration": ep["duration"],
            "summary": ep.get("summary"),
        }
        existing = [out / (name + ext) for ext in {extension(a) for a in candidates}]
        existing = [p for p in existing if p.is_file() and p.stat().st_size]
        if existing and not force:
            skipped += 1
            entry["file"] = existing[0].name
            metadata.append(entry)
            continue

        logger.info("{}: {}", "Would download" if dry_run else "Downloading", name)
        if dry_run:
            planned += 1
            continue
        last_exc = None
        for audio in candidates:
            target = out / (name + extension(audio))
            try:
                download(audio.get("downloadUrl") or audio["url"], target)
                entry["file"] = target.name
                break
            except (OSError, ValueError, http.client.HTTPException) as exc:
                last_exc = exc
        if entry["file"]:
            downloaded += 1
            metadata.append(entry)
        else:
            failed += 1
            if existing:
                entry["file"] = existing[0].name
                metadata.append(entry)
            logger.error("Could not download {}: {}", name, last_exc)

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
