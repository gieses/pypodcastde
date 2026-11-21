"""Read UTF-8 locations tables and resolve per-show storage directories."""

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Podcast:
    """A resolved crawl target; a missing show ID selects the video downloader."""

    name: str
    destination: Path
    url: str
    show_id: str | None


def default_config() -> Path:
    """Look for the private locations file in the current directory."""
    return Path.cwd() / "locations_local.txt"


def example_config() -> Path:
    """Find the public template in an installed wheel or a source checkout."""
    bundled = Path(__file__).with_name("locations_example.txt")
    return bundled if bundled.is_file() else bundled.parent.parent / bundled.name


def load(path: Path, output_root: Path | None) -> list[Podcast]:
    """Read the show list and check that each show has its own folder."""
    podcasts = []
    destinations = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.reader(stream, delimiter=";", strict=True)
        if next(rows, []) != ["Podcast Name", "Location", "URL"]:
            raise ValueError(f"{path}: expected header Podcast Name;Location;URL")
        for row in rows:
            if not row:
                continue
            where = f"{path}:{rows.line_num}"
            if len(row) != 3 or not all(cell.strip() for cell in row):
                raise ValueError(f"{where}: expected a name, location and URL")
            name, location, url = (cell.strip() for cell in row)
            if re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
                raise ValueError(f"{where}: name contains invalid filename characters")
            parts = urlsplit(url)
            if parts.scheme not in {"http", "https"} or not parts.hostname:
                raise ValueError(f"{where}: expected an HTTP(S) URL")
            show_id = None
            if parts.hostname.removeprefix("www.") in {"ardsounds.de", "ardaudiothek.de"}:
                ident = parts.path.rstrip("/").split("/")[-1]
                if not re.fullmatch(r"urn:ard:show:[0-9a-f]{16}", ident):
                    raise ValueError(f"{where}: use a show URL ending in urn:ard:show:<id>")
                show_id = ident
            windows_path = PureWindowsPath(location)
            if output_root is not None:
                if windows_path.name in {"", ".", ".."}:
                    raise ValueError(f"{where}: location needs a directory name")
                dest = output_root / windows_path.name
            else:
                if os.name != "nt" and windows_path.drive:
                    raise ValueError(f"{where}: mount this share and supply --output-root")
                dest = path.parent / Path(location).expanduser()
            if dest.absolute() in destinations:
                raise ValueError(f"{where}: duplicate destination {dest}")
            destinations.add(dest.absolute())
            podcasts.append(Podcast(name, dest, url, show_id))
    if not podcasts:
        raise ValueError(f"{path}: empty locations table")
    return podcasts
