#!/usr/bin/env python3
"""Download SCB's current administrative code tables into repository CSV files.

The source workbooks are public and intentionally not committed.  The generated
CSV files are small, easy to review, and retain leading zeroes in every code.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from pathlib import Path


SOURCES = {
    "municipalities": (
        "kommunlankod-2026.xlsx",
        "https://www.scb.se/contentassets/7a89e48960f741e08918e489ea36354a/"
        "kommunlankod-2026.xlsx",
    ),
    "parishes": (
        "lkf2026.xlsx",
        "https://www.scb.se/contentassets/13ec5841d80045498d960d456e87ea78/"
        "2025-06-19/lkf2026.xlsx",
    ),
}
NAMESPACE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CELL_REFERENCE = re.compile(r"([A-Z]+)")


def column_index(reference: str) -> int:
    """Return the zero-based column index for an Excel cell reference."""
    match = CELL_REFERENCE.match(reference)
    if match is None:
        raise ValueError(f"Invalid cell reference: {reference}")
    value = 0
    for letter in match.group(1):
        value = value * 26 + ord(letter) - ord("A") + 1
    return value - 1


def worksheet_rows(workbook: bytes, sheet: int = 1) -> Iterator[list[str]]:
    """Read an XLSX worksheet with only the Python standard library.

    SCB's sheets use shared strings and ordinary scalar cells.  A deliberately
    small reader keeps this refresh script dependency-free while preserving
    codes such as ``01`` and ``0114`` exactly as published.
    """
    with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = ["".join(item.itertext()) for item in root]

        root = ET.fromstring(archive.read(f"xl/worksheets/sheet{sheet}.xml"))
        for row in root.findall(f".//{NAMESPACE}row"):
            cells: dict[int, str] = {}
            for cell in row.findall(f"{NAMESPACE}c"):
                value = cell.find(f"{NAMESPACE}v")
                if value is None or value.text is None:
                    continue
                text = value.text
                if cell.get("t") == "s":
                    text = shared_strings[int(text)]
                cells[column_index(cell.attrib["r"])] = text.strip()
            if cells:
                yield [cells.get(index, "") for index in range(max(cells) + 1)]


def fetch(filename: str, url: str, source_dir: Path | None) -> bytes:
    if source_dir is not None:
        return (source_dir / filename).read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": "swedish-addresses/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_counties_and_municipalities(workbook: bytes) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    counties: list[dict[str, str]] = []
    municipalities: list[dict[str, str]] = []
    for row in worksheet_rows(workbook):
        if len(row) < 2:
            continue
        code, name = row[0], row[1]
        if len(code) == 2 and code.isdigit():
            counties.append({"county_code": code, "county_name": name})
        elif len(code) == 4 and code.isdigit():
            municipalities.append(
                {
                    "municipality_code": code,
                    "municipality_name": name,
                    "county_code": code[:2],
                }
            )
    if len(counties) != 21 or len(municipalities) != 290:
        raise ValueError(f"Unexpected SCB table size: {len(counties)} counties, {len(municipalities)} municipalities")
    return counties, municipalities


def build_parishes(workbook: bytes) -> list[dict[str, str]]:
    parishes: list[dict[str, str]] = []
    previous_municipality_code = ""
    for row in worksheet_rows(workbook):
        row += [""] * (6 - len(row))
        _, _, municipality_code, _, parish_code, parish_name = row[:6]
        if not (len(parish_code) == 6 and parish_code.isdigit()):
            continue
        if municipality_code:
            previous_municipality_code = municipality_code
        parishes.append(
            {
                "parish_code": parish_code,
                "parish_name": parish_name,
                "municipality_code": previous_municipality_code,
            }
        )
    if not parishes:
        raise ValueError("No parish rows found in the SCB workbook")
    return parishes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("reference/scb"))
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Use already-downloaded SCB workbooks from this directory instead of downloading them.",
    )
    args = parser.parse_args()

    municipality_name, municipality_url = SOURCES["municipalities"]
    parish_name, parish_url = SOURCES["parishes"]
    counties, municipalities = build_counties_and_municipalities(
        fetch(municipality_name, municipality_url, args.source_dir)
    )
    parishes = build_parishes(fetch(parish_name, parish_url, args.source_dir))

    write_csv(args.output_dir / "counties-2026.csv", ["county_code", "county_name"], counties)
    write_csv(
        args.output_dir / "municipalities-2026.csv",
        ["municipality_code", "municipality_name", "county_code"],
        municipalities,
    )
    write_csv(
        args.output_dir / "parishes-2026.csv",
        ["parish_code", "parish_name", "municipality_code"],
        parishes,
    )
    print(f"Wrote {len(counties)} counties, {len(municipalities)} municipalities, and {len(parishes)} parishes to {args.output_dir}")


if __name__ == "__main__":
    main()
