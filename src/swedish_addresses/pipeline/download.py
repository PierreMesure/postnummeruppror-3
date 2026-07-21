"""Acquire municipal Belägenhetsadress GeoPackages with a local cache."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import re

from dotenv import load_dotenv
from geotorget import BelagenhetsadressNedladdningClient


ADDRESS_LAYER = "belagenhetsadress"
MUNICIPALITY_COUNT = 290
_CACHE_FILE = re.compile(r"^(?P<code>\d{4})\.gpkg$")


def configured_client() -> BelagenhetsadressNedladdningClient:
    """Create a Geotorget client after loading credentials from ``.env``."""
    load_dotenv()
    return BelagenhetsadressNedladdningClient()


def requested_datasets(
    client: BelagenhetsadressNedladdningClient,
    municipality_codes: Iterable[str] | None = None,
) -> list[object]:
    """Return all municipal datasets, or validate and select requested codes."""
    datasets = client.list_municipalities()
    requested_codes = set(municipality_codes or ())
    if not requested_codes:
        return datasets
    selected = [dataset for dataset in datasets if dataset.municipality_code in requested_codes]
    missing = requested_codes - {dataset.municipality_code for dataset in selected}
    if missing:
        raise ValueError(f"Unknown municipality code(s): {', '.join(sorted(missing))}")
    return selected


def cached_municipality_codes(cache_dir: Path) -> set[str]:
    """Return municipality codes represented by GeoPackages in ``cache_dir``."""
    if not cache_dir.is_dir():
        return set()
    return {
        match.group("code")
        for path in cache_dir.iterdir()
        if (match := _CACHE_FILE.match(path.name)) and path.is_file()
    }


def municipality_sources(
    client: BelagenhetsadressNedladdningClient,
    cache_dir: Path,
    municipality_codes: Iterable[str] | None = None,
) -> list[tuple[str, str]]:
    """Return municipal sources, avoiding the API when the cache is complete.

    An explicit set of cached municipalities is sufficient to run a partial
    pipeline offline.  For a nationwide run, all 290 cache files are required
    before the municipality listing can be skipped.
    """
    requested = list(municipality_codes or ())
    cached = cached_municipality_codes(cache_dir)
    if requested and set(requested).issubset(cached):
        return [(code, "cached GeoPackage") for code in requested]
    if not requested and len(cached) == MUNICIPALITY_COUNT:
        return [(code, "cached GeoPackage") for code in sorted(cached)]

    return [
        (dataset.municipality_code, dataset.title)
        for dataset in requested_datasets(client, requested)
    ]


def gpkg_for_dataset(
    client: BelagenhetsadressNedladdningClient,
    municipality_code: str,
    cache_dir: Path,
) -> tuple[bytes, bool]:
    """Return a municipality GeoPackage and whether it was read from cache."""
    cache_path = cache_dir / f"{municipality_code}.gpkg"
    if cache_path.is_file():
        return cache_path.read_bytes(), True

    gpkg_bytes = client.get_municipality_gpkg(municipality_code)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(gpkg_bytes)
    return gpkg_bytes, False
