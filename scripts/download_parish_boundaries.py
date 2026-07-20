#!/usr/bin/env python3
"""Download and safely extract Svenska kyrkan's parish-boundary shapefile."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


URL_TEMPLATE = "https://api.svenskakyrkan.se/kartor/forsamlingar_{effective_date}.zip"
REQUIRED_SUFFIXES = {".shp", ".shx", ".dbf", ".prj"}


def read_archive(url: str, source_archive: Path | None) -> bytes:
    if source_archive is not None:
        return source_archive.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "swedish-addresses/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def validate_archive(contents: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(contents)) as archive:
        files = [member.filename for member in archive.infolist() if not member.is_dir()]
    suffixes = {Path(filename).suffix.lower() for filename in files}
    missing = REQUIRED_SUFFIXES - suffixes
    if missing:
        raise ValueError(f"Archive is not a complete shapefile; missing {', '.join(sorted(missing))}")
    return files


def extract_safely(contents: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(contents)) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if destination.resolve() not in target.parents and target != destination.resolve():
                raise ValueError(f"Unsafe path in archive: {member.filename}")
        archive.extractall(destination)


def add_standard_encoding_sidecar(extract_dir: Path) -> None:
    """Translate Svenska kyrkan's ``.cst`` charset marker to standard ``.cpg``."""
    for charset_file in extract_dir.glob("*.cst"):
        encoding = charset_file.read_text(encoding="ascii").strip()
        if encoding:
            charset_file.with_suffix(".cpg").write_text(encoding + "\n", encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--effective-date",
        default="2026-01-01",
        help="Published parish-boundary version to download (default: 2026-01-01).",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/parish-boundaries"))
    parser.add_argument("--force", action="store_true", help="Re-download even when the ZIP is cached.")
    parser.add_argument("--no-extract", action="store_true", help="Keep only the ZIP archive.")
    parser.add_argument("--source-archive", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    url = URL_TEMPLATE.format(effective_date=args.effective_date)
    archive_path = args.output_dir / f"forsamlingar_{args.effective_date}.zip"
    if archive_path.exists() and not args.force and args.source_archive is None:
        contents = archive_path.read_bytes()
        origin = "cache"
    else:
        contents = read_archive(url, args.source_archive)
        origin = "download" if args.source_archive is None else "local source archive"
        validate_archive(contents)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=archive_path.parent, delete=False) as temporary:
            temporary.write(contents)
            temporary_path = Path(temporary.name)
        temporary_path.replace(archive_path)

    files = validate_archive(contents)
    extract_dir = args.output_dir / f"forsamlingar_{args.effective_date}"
    if not args.no_extract:
        extract_safely(contents, args.output_dir)
        add_standard_encoding_sidecar(extract_dir)

    metadata = {
        "source": "Svenska kyrkan Församlingskartor",
        "url": url,
        "effective_date": args.effective_date,
        "coordinate_reference_system": "EPSG:3006",
        "attributes": {"lkfkod": "parish code", "namn": "parish name"},
        "archive": archive_path.name,
        "files": files,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    (args.output_dir / f"forsamlingar_{args.effective_date}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    location = archive_path if args.no_extract else extract_dir
    print(f"{origin.capitalize()}: {location}")


if __name__ == "__main__":
    main()
