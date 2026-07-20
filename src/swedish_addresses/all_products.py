"""Generate every current address-derived product in dependency order."""

from __future__ import annotations

import argparse
from pathlib import Path

from .coverage import build_postcode_coverage
from .products import DEFAULT_ENRICHED_INPUT, DEFAULT_OUTPUT, build_products
from .ranges import DEFAULT_OUTPUT as DEFAULT_RANGES_OUTPUT
from .ranges import build_address_ranges


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_ENRICHED_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=Path("cache/geotorget"))
    parser.add_argument("--reference", type=Path, default=Path("reference/scb"))
    parser.add_argument("--skip-existing-ranges", action="store_true")
    args = parser.parse_args()

    print("Building compact postcode products")
    build_products(args.input, args.output_dir)
    print("Building address ranges")
    ranges_output = args.output_dir / DEFAULT_RANGES_OUTPUT.name
    build_address_ranges(args.input, ranges_output, args.skip_existing_ranges)
    print("Building named postcode coverage")
    build_postcode_coverage(args.input, args.cache, args.reference, args.output_dir / "postcode-coverage.parquet")
    print("Finished all current products")
