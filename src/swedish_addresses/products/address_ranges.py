"""Create transparent address-number ranges from enriched address points."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ..pipeline.enrich import add_pipeline_options, prepare_enriched_addresses
from .common import DEFAULT_ENRICHED_INPUT, partition_files


DEFAULT_OUTPUT = Path("data/address-pipeline/products/address-ranges")
GROUP_COLUMNS = [
    "address_area",
    "address_type",
    "postcode",
    "post_town",
    "county_code",
    "municipality_code",
    "district_code",
    "parish_code",
    "parish_match_status",
]
INPUT_COLUMNS = GROUP_COLUMNS + [
    "address_number",
    "letter_suffix",
    "location_suffix",
    "location_suffix_number",
    "deviates_from_standard",
]
OUTPUT_COLUMNS = [
    *GROUP_COLUMNS,
    "number_from",
    "letter_from",
    "number_to",
    "letter_to",
    "range_type",
    "address_count",
    "derivation_method",
]
NUMERIC_ADDRESS = re.compile(r"^\d+$")
SINGLE_LETTER = re.compile(r"^[A-Z]$")


def _text(value: object) -> str:
    return "" if pd.isna(value) else str(value)


def ranges_for_addresses(addresses: pd.DataFrame) -> pd.DataFrame:
    """Build address ranges for what can be proven from physical addresses.

    Numeric addresses are joined only across consecutive odd/even values. Letter
    suffixes are joined only across consecutive A-Z values for the same number.
    Everything else remains an individual source-address range.
    """
    frame = addresses[INPUT_COLUMNS].copy()
    for column in GROUP_COLUMNS:
        frame[column] = frame[column].map(_text)
    frame["address_number"] = frame["address_number"].map(_text)
    frame["letter_suffix"] = frame["letter_suffix"].map(_text).str.upper()
    has_location_detail = frame["location_suffix"].notna() | frame["location_suffix_number"].notna()
    is_standard = ~frame["deviates_from_standard"].fillna(False)
    is_numeric = frame["address_number"].map(lambda value: bool(NUMERIC_ADDRESS.fullmatch(value)))
    usable = is_standard & ~has_location_detail & is_numeric
    plain = usable & frame["letter_suffix"].eq("")
    lettered = usable & frame["letter_suffix"].map(lambda value: bool(SINGLE_LETTER.fullmatch(value)))
    covered = plain | lettered

    plain_values = (
        frame.loc[plain, [*GROUP_COLUMNS, "address_number"]]
        .groupby([*GROUP_COLUMNS, "address_number"], as_index=False)
        .size()
        .rename(columns={"size": "address_count"})
    )
    plain_values["number"] = plain_values["address_number"].astype(int)
    plain_values["range_type"] = plain_values["number"].mod(2).map({1: "NU", 0: "NJ"})
    numeric_keys = [*GROUP_COLUMNS, "range_type"]
    plain_values = plain_values.sort_values([*numeric_keys, "number"])
    plain_values["new_run"] = plain_values.groupby(numeric_keys)["number"].diff().ne(2)
    plain_values["run"] = plain_values.groupby(numeric_keys)["new_run"].cumsum()
    numeric_ranges = (
        plain_values.groupby([*numeric_keys, "run"], as_index=False)
        .agg(number_from=("number", "min"), number_to=("number", "max"), address_count=("address_count", "sum"))
        .drop(columns="run")
    )
    numeric_ranges["number_from"] = numeric_ranges["number_from"].astype(str)
    numeric_ranges["number_to"] = numeric_ranges["number_to"].astype(str)
    numeric_ranges["letter_from"] = None
    numeric_ranges["letter_to"] = None
    numeric_ranges["derivation_method"] = "numeric_contiguous"

    letter_values = (
        frame.loc[lettered, [*GROUP_COLUMNS, "address_number", "letter_suffix"]]
        .groupby([*GROUP_COLUMNS, "address_number", "letter_suffix"], as_index=False)
        .size()
        .rename(columns={"size": "address_count"})
    )
    letter_values["number"] = letter_values["address_number"].astype(int)
    letter_values["range_type"] = letter_values["number"].mod(2).map({1: "NU", 0: "NJ"})
    letter_keys = [*GROUP_COLUMNS, "address_number", "range_type"]
    letter_values["letter_order"] = letter_values["letter_suffix"].map(ord)
    letter_values = letter_values.sort_values([*letter_keys, "letter_order"])
    letter_values["new_run"] = letter_values.groupby(letter_keys)["letter_order"].diff().ne(1)
    letter_values["run"] = letter_values.groupby(letter_keys)["new_run"].cumsum()
    letter_ranges = (
        letter_values.groupby([*letter_keys, "run"], as_index=False)
        .agg(
            letter_from=("letter_suffix", "min"),
            letter_to=("letter_suffix", "max"),
            address_count=("address_count", "sum"),
        )
        .drop(columns="run")
        .rename(columns={"address_number": "number_from"})
    )
    letter_ranges["number_to"] = letter_ranges["number_from"]
    letter_ranges["derivation_method"] = "letter_contiguous"

    singles = frame.loc[~covered, [*GROUP_COLUMNS, "address_number", "letter_suffix"]].copy()
    singles = singles.rename(columns={"address_number": "number_from", "letter_suffix": "letter_from"})
    singles["number_to"] = singles["number_from"]
    singles["letter_to"] = singles["letter_from"].replace("", None)
    singles["letter_from"] = singles["letter_from"].replace("", None)
    singles["range_type"] = "single"
    singles["address_count"] = 1
    singles["derivation_method"] = "single_source_address"

    return pd.concat([numeric_ranges, letter_ranges, singles], ignore_index=True)[OUTPUT_COLUMNS]


def _partition_code(partition: Path) -> str:
    return partition.stem if partition.name != "addresses.parquet" else partition.parent.name.removeprefix("municipality_code=")


def build_address_ranges(enriched_input: Path, output: Path, skip_existing: bool = False) -> dict[str, int]:
    """Build flat, municipality-specific range files without national in-memory state."""
    partitions = partition_files(enriched_input)
    if not partitions:
        raise FileNotFoundError(f"No enriched municipality files found in {enriched_input}")
    output.mkdir(parents=True, exist_ok=True)
    if skip_existing:
        partitions = [part for part in partitions if not (output / f"{_partition_code(part)}.parquet").is_file()]
        if not partitions:
            return write_range_report(output)
    counts: dict[str, int] = defaultdict(int)
    for index, partition in enumerate(partitions, start=1):
        frame = pd.read_parquet(partition, columns=INPUT_COLUMNS)
        ranges = ranges_for_addresses(frame)
        municipality_code = _text(frame["municipality_code"].iloc[0])
        ranges.to_parquet(output / f"{municipality_code}.parquet", index=False)
        counts["municipalities"] += 1
        counts["source_addresses"] += len(frame)
        counts["ranges"] += len(ranges)
        counts["singleton_ranges"] += int(ranges["address_count"].eq(1).sum())
        print(f"[{index}/{len(partitions)}] {municipality_code}: {len(ranges):,} ranges", flush=True)

    counts["multi_address_ranges"] = counts["ranges"] - counts["singleton_ranges"]
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "source": str(enriched_input),
                "scope": "current physical addresses only",
                "range_rules": {
                    "numeric": "consecutive numbers of the same parity",
                    "letters": "consecutive A-Z suffixes for the same number",
                    "other": "one source address per range",
                },
                "counts": counts,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return dict(counts)


def write_range_report(output: Path) -> dict[str, int]:
    """Summarize already-built municipal range files without rebuilding them."""
    parts = sorted(output.glob("*.parquet"))
    if not parts:
        raise FileNotFoundError(f"No range files found in {output}")
    counts = {"municipalities": len(parts), "ranges": 0, "singleton_ranges": 0, "source_addresses": 0}
    for part in parts:
        frame = pd.read_parquet(part, columns=["address_count"])
        counts["ranges"] += len(frame)
        counts["singleton_ranges"] += int(frame["address_count"].eq(1).sum())
        counts["source_addresses"] += int(frame["address_count"].sum())
    counts["multi_address_ranges"] = counts["ranges"] - counts["singleton_ranges"]
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "source": str(DEFAULT_ENRICHED_INPUT),
                "scope": "current physical addresses only",
                "range_rules": {
                    "numeric": "consecutive numbers of the same parity",
                    "letters": "consecutive A-Z suffixes for the same number",
                    "other": "one source address per range",
                },
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
    parser.add_argument("--skip-existing", action="store_true", help="Resume a partial build without replacing municipal files.")
    parser.add_argument("--report", action="store_true", help="Write a report for existing range files without rebuilding them.")
    add_pipeline_options(parser)
    args = parser.parse_args()
    if args.report:
        counts = write_range_report(args.output)
    else:
        prepare_enriched_addresses(args, args.input)
        counts = build_address_ranges(args.input, args.output, args.skip_existing)
    print(
        "Wrote {ranges:,} ranges from {source_addresses:,} addresses; "
        "{singleton_ranges:,} are single-address ranges.".format(**counts)
    )


if __name__ == "__main__":
    main()
