"""Build a parquet file from all Belägenhetsadress municipal GeoPackages."""

from __future__ import annotations

import argparse
import io
import warnings
from collections.abc import Iterable
from pathlib import Path

import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
from geotorget import BelagenhetsadressNedladdningClient

DEFAULT_OUTPUT = Path("data/swedish_addresses.parquet")
ADDRESS_LAYER = "belagenhetsadress"


def addresses_from_gpkg(gpkg_bytes: bytes, municipality_code: str) -> pd.DataFrame:
    """Extract postcode and EPSG:3006 point coordinates from one GeoPackage."""
    # pyogrio assigns byte streams a /vsimem path without a .gpkg extension.
    # GDAL correctly reads the GeoPackage but emits a harmless warning for it.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"File /vsimem/pyogrio_.* has GPKG application_id, but non conformant file extension",
            category=RuntimeWarning,
        )
        addresses = gpd.read_file(
            io.BytesIO(gpkg_bytes),
            layer=ADDRESS_LAYER,
            columns=["postnummer"],
            engine="pyogrio",
            use_arrow=True,
        )
    if "postnummer" not in addresses:
        raise ValueError(f"{municipality_code}: GeoPackage has no 'postnummer' column")

    geometry = addresses.geometry
    if not geometry.geom_type.eq("Point").all():
        raise ValueError(f"{municipality_code}: expected only Point geometries")

    result = pd.DataFrame(
        {
            "municipality_code": municipality_code,
            "postcode": pd.to_numeric(addresses["postnummer"], errors="coerce").astype("Int64"),
            "x": geometry.x,
            "y": geometry.y,
        }
    )
    return result.dropna(subset=["postcode", "x", "y"]).query("postcode != 0")


def gpkg_for_dataset(
    client: BelagenhetsadressNedladdningClient,
    municipality_code: str,
    cache_dir: Path | None,
) -> tuple[bytes, bool]:
    """Return a municipality GeoPackage and whether it came from the cache."""
    cache_path = cache_dir / f"{municipality_code}.gpkg" if cache_dir else None
    if cache_path and cache_path.is_file():
        return cache_path.read_bytes(), True

    gpkg_bytes = client.get_municipality_gpkg(municipality_code)
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(gpkg_bytes)
    return gpkg_bytes, False


def download_addresses(
    output: Path,
    municipality_codes: Iterable[str] | None = None,
    cache_dir: Path | None = None,
) -> int:
    """Download every requested municipality as bytes and write one parquet file."""
    load_dotenv()
    client = BelagenhetsadressNedladdningClient()
    datasets = client.list_municipalities()
    requested_codes = set(municipality_codes or ())
    if requested_codes:
        datasets = [item for item in datasets if item.municipality_code in requested_codes]
        missing = requested_codes - {item.municipality_code for item in datasets}
        if missing:
            raise ValueError(f"Unknown municipality code(s): {', '.join(sorted(missing))}")

    frames: list[pd.DataFrame] = []
    for index, dataset in enumerate(datasets, start=1):
        gpkg_bytes, cached = gpkg_for_dataset(client, dataset.municipality_code, cache_dir)
        source = "Using cached" if cached else "Downloaded"
        print(f"[{index}/{len(datasets)}] {source} {dataset.municipality_code} {dataset.title}")
        frames.append(addresses_from_gpkg(gpkg_bytes, dataset.municipality_code))

    if not frames:
        raise ValueError("No municipality datasets selected")
    addresses = pd.concat(frames, ignore_index=True).sort_values(
        ["postcode", "municipality_code", "x", "y"], ignore_index=True
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    addresses.to_parquet(output, index=False)
    print(f"Wrote {len(addresses):,} addresses to {output}")
    return len(addresses)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--cache",
        type=Path,
        metavar="DIRECTORY",
        help="Store GeoPackages in this directory and reuse existing municipality files.",
    )
    parser.add_argument(
        "--municipality",
        action="append",
        dest="municipality_codes",
        metavar="CODE",
        help="Only download this municipality code; repeat for more than one.",
    )
    args = parser.parse_args()
    download_addresses(args.output, args.municipality_codes, args.cache)


if __name__ == "__main__":
    main()
