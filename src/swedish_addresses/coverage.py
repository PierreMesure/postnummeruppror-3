"""Build a named postcode coverage table from enriched physical addresses."""

from __future__ import annotations

import argparse
import warnings
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .download import ADDRESS_LAYER
from .products import DEFAULT_ENRICHED_INPUT, partition_files


DEFAULT_CACHE = Path("cache/geotorget")
DEFAULT_REFERENCE = Path("reference/scb")
DEFAULT_OUTPUT = Path("data/address-pipeline/products/postcode-coverage.parquet")
GROUP_COLUMNS = [
    "postcode",
    "post_town",
    "county_code",
    "municipality_code",
    "district_code",
    "parish_code",
    "parish_match_status",
]


def _code(value: object, width: int) -> str:
    if pd.isna(value):
        return ""
    return str(value).removesuffix(".0").zfill(width)


def district_names(cache_dir: Path) -> dict[str, str]:
    """Extract the small district code/name lookup from cached address GPKGs."""
    names: dict[str, str] = {}
    for path in sorted(cache_dir.glob("*.gpkg")):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning, message=r".*non conformant file extension")
            frame = gpd.read_file(
                path,
                layer=ADDRESS_LAYER,
                columns=["distriktskod", "distriktsnamn"],
                engine="pyogrio",
                use_arrow=True,
                ignore_geometry=True,
            )
        for code, name in frame.dropna(subset=["distriktskod", "distriktsnamn"]).drop_duplicates().itertuples(index=False):
            normalized_code = _code(code, 6)
            normalized_name = str(name)
            existing = names.setdefault(normalized_code, normalized_name)
            if existing != normalized_name:
                raise ValueError(f"Conflicting district names for {normalized_code}: {existing!r}, {normalized_name!r}")
    return names


def add_names(coverage: pd.DataFrame, reference_dir: Path, districts: dict[str, str]) -> pd.DataFrame:
    counties = pd.read_csv(reference_dir / "counties-2026.csv", dtype="string").set_index("county_code")["county_name"]
    municipalities = pd.read_csv(reference_dir / "municipalities-2026.csv", dtype="string").set_index("municipality_code")["municipality_name"]
    parishes = pd.read_csv(reference_dir / "parishes-2026.csv", dtype="string").set_index("parish_code")["parish_name"]
    result = coverage.copy()
    result["county_name"] = result["county_code"].map(counties)
    result["municipality_name"] = result["municipality_code"].map(municipalities)
    result["district_name"] = result["district_code"].map(districts)
    result["parish_name"] = result["parish_code"].map(parishes)
    return result[
        [
            "postcode",
            "post_town",
            "county_code",
            "county_name",
            "municipality_code",
            "municipality_name",
            "district_code",
            "district_name",
            "parish_code",
            "parish_name",
            "parish_match_status",
            "address_count",
        ]
    ]


def build_postcode_coverage(enriched_input: Path, cache_dir: Path, reference_dir: Path, output: Path) -> int:
    """Group exact postcode/admin/parish combinations without national address state."""
    totals: dict[tuple[str, ...], int] = defaultdict(int)
    partitions = partition_files(enriched_input)
    if not partitions:
        raise FileNotFoundError(f"No enriched municipality files found in {enriched_input}")
    for index, part in enumerate(partitions, start=1):
        frame = pd.read_parquet(part, columns=GROUP_COLUMNS)
        for values, count in frame.groupby(GROUP_COLUMNS, dropna=False).size().items():
            key = tuple("" if pd.isna(value) else str(value) for value in values)
            totals[key] += int(count)
        print(f"[{index}/{len(partitions)}] Scanning {part.name}")

    coverage = pd.DataFrame(
        [dict(zip(GROUP_COLUMNS, values, strict=True), address_count=count) for values, count in sorted(totals.items())]
    )
    named = add_names(coverage, reference_dir, district_names(cache_dir))
    output.parent.mkdir(parents=True, exist_ok=True)
    named.to_parquet(output, index=False)
    return len(named)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_ENRICHED_INPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = build_postcode_coverage(args.input, args.cache, args.reference, args.output)
    print(f"Wrote {rows:,} postcode coverage rows to {args.output}")


if __name__ == "__main__":
    main()
