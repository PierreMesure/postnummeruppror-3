"""Generate every current address-derived product in dependency order."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..pipeline.enrich import (
    DEFAULT_PARISH_BOUNDARIES,
    DEFAULT_PARISH_REFERENCE,
    DEFAULT_RAW_OUTPUT,
    build_pipeline,
)
from .postcode_coverage import build_postcode_coverage
from .common import DEFAULT_ENRICHED_INPUT, DEFAULT_OUTPUT, build_products
from .address_ranges import DEFAULT_OUTPUT as DEFAULT_RANGES_OUTPUT
from .address_ranges import build_address_ranges


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_ENRICHED_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=Path("cache/geotorget"))
    parser.add_argument("--reference", type=Path, default=Path("reference/scb"))
    parser.add_argument("--raw-output", type=Path, default=DEFAULT_RAW_OUTPUT)
    parser.add_argument("--parish-boundaries", type=Path, default=DEFAULT_PARISH_BOUNDARIES)
    parser.add_argument("--parish-reference", type=Path, default=DEFAULT_PARISH_REFERENCE)
    parser.add_argument("--skip-existing-ranges", action="store_true")
    args = parser.parse_args()

    print("Building cached, enriched address partitions")
    build_pipeline(
        args.cache,
        args.raw_output,
        args.input,
        args.parish_boundaries,
        args.parish_reference,
    )
    print("Building compact postcode products")
    build_products(args.input, args.output_dir)
    print("Building address ranges")
    ranges_output = args.output_dir / DEFAULT_RANGES_OUTPUT.name
    build_address_ranges(args.input, ranges_output, args.skip_existing_ranges)
    print("Building named postcode coverage")
    build_postcode_coverage(args.input, args.cache, args.reference, args.output_dir / "postcode-coverage.parquet")
    print("Finished all current products")
