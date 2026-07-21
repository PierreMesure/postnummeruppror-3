"""Build a compact, municipality-partitioned address dataset.

The pipeline deliberately keeps only one municipality in memory.  Its raw
stage is a durable, geometry-free address dataset; the enriched stage assigns
each physical address to a Svenska kyrkan parish polygon.
"""

from __future__ import annotations

import argparse
import io
import json
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .download import ADDRESS_LAYER, configured_client, gpkg_for_dataset, municipality_sources


DEFAULT_RAW_OUTPUT = Path("data/address-pipeline/raw")
DEFAULT_ENRICHED_OUTPUT = Path("data/address-pipeline/enriched")
DEFAULT_PARISH_BOUNDARIES = Path(
    "data/parish-boundaries/forsamlingar_2026-01-01/forsamlingar_2026-01-01.shp"
)
DEFAULT_PARISH_REFERENCE = Path("reference/scb/parishes-2026.csv")

SOURCE_COLUMNS = [
    "belagenhetsadress_objektidentitet",
    "versiongiltigfran",
    "adressplatsnummer",
    "statusforbelagenhetsadress",
    "bokstavstillagg",
    "lagestillagg",
    "lagestillaggsnummer",
    "adressplatstyp",
    "insamlingslage",
    "avvikerfranstandarden",
    "avvikandeadressplatsbeteckning",
    "postnummer",
    "postort",
    "popularnamn",
    "distriktskod",
    "lanskod",
    "kommunkod",
    "kommundel_faststalltnamn",
    "adressomrade_faststalltnamn",
    "adressomradestyp",
    "gardsadressomrade_faststalltnamn",
]
OUTPUT_COLUMNS = [
    "address_id",
    "valid_from",
    "address_number",
    "address_status",
    "letter_suffix",
    "location_suffix",
    "location_suffix_number",
    "address_type",
    "collection_location",
    "deviates_from_standard",
    "deviating_address_designation",
    "postcode",
    "post_town",
    "popular_name",
    "district_code",
    "county_code",
    "municipality_code",
    "municipality_part",
    "address_area",
    "address_area_type",
    "farm_address_area",
    "x",
    "y",
]
RENAME_COLUMNS = {
    "belagenhetsadress_objektidentitet": "address_id",
    "versiongiltigfran": "valid_from",
    "adressplatsnummer": "address_number",
    "statusforbelagenhetsadress": "address_status",
    "bokstavstillagg": "letter_suffix",
    "lagestillagg": "location_suffix",
    "lagestillaggsnummer": "location_suffix_number",
    "adressplatstyp": "address_type",
    "insamlingslage": "collection_location",
    "avvikerfranstandarden": "deviates_from_standard",
    "avvikandeadressplatsbeteckning": "deviating_address_designation",
    "postnummer": "postcode",
    "postort": "post_town",
    "popularnamn": "popular_name",
    "distriktskod": "district_code",
    "lanskod": "county_code",
    "kommunkod": "municipality_code",
    "kommundel_faststalltnamn": "municipality_part",
    "adressomrade_faststalltnamn": "address_area",
    "adressomradestyp": "address_area_type",
    "gardsadressomrade_faststalltnamn": "farm_address_area",
}


def _read_gpkg(gpkg_bytes: bytes, columns: list[str]) -> gpd.GeoDataFrame:
    # pyogrio assigns byte streams a /vsimem path without a .gpkg extension.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"File /vsimem/pyogrio_.* has GPKG application_id, but non conformant file extension",
            category=RuntimeWarning,
        )
        return gpd.read_file(
            io.BytesIO(gpkg_bytes),
            layer=ADDRESS_LAYER,
            columns=columns,
            engine="pyogrio",
            use_arrow=True,
        )


def _code(values: pd.Series, width: int) -> pd.Series:
    return values.astype("string").str.replace(r"\.0$", "", regex=True).str.zfill(width)


def raw_addresses_from_gpkg(gpkg_bytes: bytes, municipality_code: str) -> pd.DataFrame:
    """Extract the address fields needed for current address products."""
    addresses = _read_gpkg(gpkg_bytes, SOURCE_COLUMNS)
    missing = set(SOURCE_COLUMNS) - set(addresses.columns)
    if missing:
        raise ValueError(f"{municipality_code}: GeoPackage missing columns: {', '.join(sorted(missing))}")
    if not addresses.geometry.geom_type.eq("Point").all():
        raise ValueError(f"{municipality_code}: expected only Point geometries")

    result = addresses.drop(columns="geometry").rename(columns=RENAME_COLUMNS)
    result["x"] = addresses.geometry.x
    result["y"] = addresses.geometry.y
    result["municipality_code"] = _code(result["municipality_code"], 4).fillna(municipality_code)
    result["county_code"] = _code(result["county_code"], 2)
    result["district_code"] = _code(result["district_code"], 6)
    result["postcode"] = _code(result["postcode"], 5)
    return result[OUTPUT_COLUMNS].dropna(subset=["x", "y", "postcode"]).query("postcode != '00000'")


def partition_path(root: Path, municipality_code: str) -> Path:
    return root / f"{municipality_code}.parquet"


def write_partition(frame: pd.DataFrame, root: Path, municipality_code: str) -> Path:
    path = partition_path(root, municipality_code)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("addresses.tmp.parquet")
    frame.to_parquet(temporary, index=False)
    temporary.replace(path)
    return path


def load_parishes(boundary_path: Path, parish_reference: Path) -> gpd.GeoDataFrame:
    """Load territorial parish polygons and validate their LKF codes against SCB."""
    if not boundary_path.is_file():
        raise FileNotFoundError(
            f"Parish boundary shapefile not found: {boundary_path}. "
            "Run scripts/download_parish_boundaries.py first."
        )
    if not parish_reference.is_file():
        raise FileNotFoundError(f"SCB parish reference not found: {parish_reference}")
    boundaries = gpd.read_file(boundary_path, columns=["lkfkod", "namn"], engine="pyogrio", use_arrow=True)
    if not {"lkfkod", "namn"}.issubset(boundaries.columns):
        raise ValueError("Parish boundary shapefile must contain lkfkod and namn")
    reference = pd.read_csv(parish_reference, dtype="string").set_index("parish_code")
    boundaries["parish_code"] = _code(boundaries["lkfkod"], 6)
    unknown_codes = set(boundaries["parish_code"]) - set(reference.index)
    if unknown_codes:
        raise ValueError(f"Parish boundaries contain unknown LKF code(s): {', '.join(sorted(unknown_codes))}")
    return boundaries[["parish_code", "geometry"]].to_crs("EPSG:3006")


def enrich_with_parishes(addresses: pd.DataFrame, parishes: gpd.GeoDataFrame) -> pd.DataFrame:
    """Assign parish codes by point-in-polygon without retaining point geometry."""
    points = gpd.GeoDataFrame(
        addresses.copy(),
        geometry=gpd.points_from_xy(addresses["x"], addresses["y"]),
        crs="EPSG:3006",
    )
    joined = gpd.sjoin(points, parishes, how="left", predicate="within")
    joined["parish_match_status"] = joined["parish_code"].notna().map(
        {True: "matched", False: "unmatched"}
    )
    return pd.DataFrame(joined.drop(columns=["geometry", "index_right"]))


def build_pipeline(
    cache_dir: Path,
    raw_output: Path,
    enriched_output: Path,
    parish_boundaries: Path,
    parish_reference: Path,
    requested_codes: list[str] | None = None,
) -> dict[str, int]:
    """Build raw and enriched partitions, retaining one municipality at a time."""
    parishes = load_parishes(parish_boundaries, parish_reference)
    counts = {"municipalities": 0, "raw_addresses": 0, "matched_addresses": 0, "unmatched_addresses": 0}
    client = configured_client()
    sources = municipality_sources(client, cache_dir, requested_codes)
    for index, (code, title) in enumerate(sources, start=1):
        gpkg_bytes, cached = gpkg_for_dataset(client, code, cache_dir)
        source = "Using cached" if cached else "Downloaded"
        print(f"[{index}/{len(sources)}] {source} {code} {title}")
        raw = raw_addresses_from_gpkg(gpkg_bytes, code)
        write_partition(raw, raw_output, code)
        enriched = enrich_with_parishes(raw, parishes)
        write_partition(enriched, enriched_output, code)
        matched = int(enriched["parish_match_status"].eq("matched").sum())
        counts["municipalities"] += 1
        counts["raw_addresses"] += len(raw)
        counts["matched_addresses"] += matched
        counts["unmatched_addresses"] += len(enriched) - matched
        print(f"         {len(raw):,} addresses; {matched:,} parish matches")

    enriched_output.mkdir(parents=True, exist_ok=True)
    (enriched_output / "manifest.json").write_text(
        json.dumps(
            {
                "pipeline": "address-parish-enrichment",
                "coordinate_reference_system": "EPSG:3006",
                "parish_boundaries": str(parish_boundaries),
                "parish_reference": str(parish_reference),
                "counts": counts,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return counts


def add_pipeline_options(parser: argparse.ArgumentParser) -> None:
    """Add shared GeoPackage acquisition and enrichment options to a parser."""
    parser.add_argument("--cache", type=Path, default=Path("cache/geotorget"))
    parser.add_argument("--raw-output", type=Path, default=DEFAULT_RAW_OUTPUT)
    parser.add_argument("--parish-boundaries", type=Path, default=DEFAULT_PARISH_BOUNDARIES)
    parser.add_argument("--parish-reference", type=Path, default=DEFAULT_PARISH_REFERENCE)
    parser.add_argument("--municipality", action="append", dest="municipality_codes", metavar="CODE")


def prepare_enriched_addresses(args: argparse.Namespace, enriched_output: Path) -> dict[str, int]:
    """Acquire, cache, and enrich the source addresses for a product command."""
    return build_pipeline(
        args.cache,
        args.raw_output,
        enriched_output,
        args.parish_boundaries,
        args.parish_reference,
        args.municipality_codes,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enriched-output", type=Path, default=DEFAULT_ENRICHED_OUTPUT)
    add_pipeline_options(parser)
    args = parser.parse_args()
    counts = prepare_enriched_addresses(args, args.enriched_output)
    print(
        "Wrote {raw_addresses:,} addresses across {municipalities} municipalities "
        "({matched_addresses:,} parish matches, {unmatched_addresses:,} unmatched).".format(**counts)
    )


if __name__ == "__main__":
    main()
