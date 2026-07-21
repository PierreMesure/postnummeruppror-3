"""Shared builders for compact, current postcode products."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ..pipeline.enrich import add_pipeline_options, prepare_enriched_addresses


DEFAULT_ENRICHED_INPUT = Path("data/address-pipeline/enriched")
DEFAULT_OUTPUT = Path("data/address-pipeline/products")
PRODUCT_NAMES = (
    "postcode-post-towns",
    "postcode-administrative-areas",
    "postcode-parishes",
    "postcode-centroids",
)


def _counter() -> dict[str, float | int]:
    return {"address_count": 0, "x_sum": 0.0, "y_sum": 0.0}


def _add_count(counter: dict[tuple[str, ...], int], frame: pd.DataFrame, columns: list[str]) -> None:
    for values, count in frame.groupby(columns, dropna=False).size().items():
        key = values if isinstance(values, tuple) else (values,)
        counter[tuple("" if pd.isna(value) else str(value) for value in key)] += int(count)


def partition_files(enriched_input: Path) -> list[Path]:
    """Return current flat partitions, or the previous layout for migration only."""
    flat = sorted(enriched_input.glob("*.parquet"))
    if flat:
        return flat
    return sorted(enriched_input.glob("municipality_code=*/addresses.parquet"))


def build_products(
    enriched_input: Path, output: Path, products: set[str] | None = None
) -> dict[str, int]:
    """Create small product tables without loading all address partitions at once."""
    selected = set(PRODUCT_NAMES if products is None else products)
    unknown = selected - set(PRODUCT_NAMES)
    if unknown:
        raise ValueError(f"Unknown product(s): {', '.join(sorted(unknown))}")
    partitions = partition_files(enriched_input)
    if not partitions:
        raise FileNotFoundError(f"No enriched municipality files found in {enriched_input}")

    postcode_towns: dict[tuple[str, ...], int] = defaultdict(int)
    postcode_areas: dict[tuple[str, ...], int] = defaultdict(int)
    postcode_parishes: dict[tuple[str, ...], int] = defaultdict(int)
    centroids: dict[tuple[str, ...], dict[str, float | int]] = defaultdict(_counter)
    unmatched = 0

    for index, partition in enumerate(partitions, start=1):
        print(f"[{index}/{len(partitions)}] Scanning {partition.name}")
        frame = pd.read_parquet(partition)
        _add_count(postcode_towns, frame, ["postcode", "post_town"])
        _add_count(postcode_areas, frame, ["postcode", "county_code", "municipality_code", "district_code"])

        matched = frame.loc[frame["parish_match_status"].eq("matched")]
        unmatched += len(frame) - len(matched)
        _add_count(postcode_parishes, matched, ["postcode", "parish_code"])

        grouped = frame.groupby(["postcode", "post_town"], dropna=False).agg(
            address_count=("postcode", "size"), x_sum=("x", "sum"), y_sum=("y", "sum")
        )
        for values, row in grouped.iterrows():
            key = tuple("" if pd.isna(value) else str(value) for value in values)
            aggregate = centroids[key]
            aggregate["address_count"] += int(row["address_count"])
            aggregate["x_sum"] += float(row["x_sum"])
            aggregate["y_sum"] += float(row["y_sum"])

    output.mkdir(parents=True, exist_ok=True)
    postcode_town_rows = [
        {"postcode": postcode, "post_town": post_town, "address_count": count}
        for (postcode, post_town), count in sorted(postcode_towns.items())
    ]
    postcode_area_rows = [
        {
            "postcode": postcode,
            "county_code": county_code,
            "municipality_code": municipality_code,
            "district_code": district_code,
            "address_count": count,
        }
        for (postcode, county_code, municipality_code, district_code), count in sorted(postcode_areas.items())
    ]
    postcode_parish_rows = [
        {"postcode": postcode, "parish_code": parish_code, "address_count": count}
        for (postcode, parish_code), count in sorted(postcode_parishes.items())
    ]
    centroid_rows = [
        {
            "postcode": postcode,
            "post_town": post_town,
            "address_count": int(values["address_count"]),
            "x": values["x_sum"] / values["address_count"],
            "y": values["y_sum"] / values["address_count"],
        }
        for (postcode, post_town), values in sorted(centroids.items())
    ]

    product_rows = {
        "postcode-post-towns": postcode_town_rows,
        "postcode-administrative-areas": postcode_area_rows,
        "postcode-parishes": postcode_parish_rows,
        "postcode-centroids": centroid_rows,
    }
    for product, rows in product_rows.items():
        if product in selected:
            pd.DataFrame(rows).to_parquet(output / f"{product}.parquet", index=False)
    counts = {
        "municipality_partitions": len(partitions),
        "postcode_post_town_rows": len(postcode_town_rows),
        "postcode_administrative_area_rows": len(postcode_area_rows),
        "postcode_parish_rows": len(postcode_parish_rows),
        "postcode_centroid_rows": len(centroid_rows),
        "unmatched_addresses_excluded_from_parishes": unmatched,
    }
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "source": str(enriched_input),
                "coordinate_reference_system": "EPSG:3006",
                "scope": "current physical addresses only",
                "products": sorted(selected),
                "counts": counts,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_ENRICHED_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--product", choices=PRODUCT_NAMES, action="append", dest="products")
    add_pipeline_options(parser)
    args = parser.parse_args()
    prepare_enriched_addresses(args, args.input)
    counts = build_products(args.input, args.output, set(args.products) if args.products else None)
    print("Wrote compact postcode products: " + ", ".join(f"{key}={value:,}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
