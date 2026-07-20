# Postnummerupproret 3.0

A simple script to download the dataset [Belägenhetsadress Nedladdning, vektor](https://geotorget.lantmateriet.se/geodataprodukter/belagenhetsadress-nedladdning-vektor-api) from the APIs of the Swedish mapping, cadastral and land registration authority (*Lantmäteriet).

The download client is [geotorget-py](https://github.com/PierreMesure/geotorget-py).
Each municipal GeoPackage is obtained in memory as bytes by default; only the final Parquet file is stored locally. Coordinates are `x` and `y` in the GeoPackages' SWEREF 99 TM coordinate reference system (EPSG:3006).

This dataset contains all addresses from all municipalities in Sweden.

Once downloaded, the script unzips the files, opens them with GeoPandas and keeps the columns "postnummer" (postcodes) and "geometry" (containing a single coordinate in [EPSG:3006](https://spatialreference.org/ref/epsg/3006/)). It concatenates data from all the municipalities and exports it as parquet.

I uploaded the parquet file on [HuggingFace](https://huggingface.co/datasets/PierreMesure/swedish_postcodes) for people to reuse it, it can be used as a ground truth for the location of postcodes in Sweden.

## Setup

Create `.env` from the example and add Geotorget credentials with access to the
dataset:

```bash
cp .env.example .env
uv sync
```

## Download all municipalities

```bash
uv run download-addresses
```

This writes `data/swedish_addresses.parquet`, with these columns:

| Column | Meaning |
| --- | --- |
| `municipality_code` | Four-digit municipality code from the STAC collection |
| `postcode` | Address postcode |
| `x` | Easting, EPSG:3006 |
| `y` | Northing, EPSG:3006 |

Use `--output` to choose a location. For a small credentialed smoke test, use a
single municipality:

```bash
uv run download-addresses --municipality 0180 --output data/stockholm.parquet
```

## Cache GeoPackages

Pass `--cache` to retain each municipal GeoPackage. The downloader uses the
municipality code as the filename (for example, `cache/geotorget/0180.gpkg`) and
uses that file whenever it already exists, avoiding a repeat download:

```bash
uv run download-addresses --cache cache/geotorget
```

Run the test suite with `uv run pytest`.

## Parish boundaries

Download Svenska kyrkan's current parish-boundary shapefile (EPSG:3006) with:

```bash
uv run python scripts/download_parish_boundaries.py
```

The archive and extracted shapefile are stored under
`data/parish-boundaries/`. Its `lkfkod` attribute joins to
`reference/scb/parishes-2026.csv`; `namn` is the parish name. Use a different
published version when required, for example
`--effective-date 2027-01-01`.

The 2026 boundary layer has 1,251 territorial parishes. Five SCB LKF entries
have no boundary geometry (`018090`, `018092`, `018093`, `108002`, `148025`),
so they cannot be assigned with a point-in-polygon join.

## Enriched address pipeline

With cached municipal GeoPackages and parish boundaries in place, build raw and
parish-enriched Parquet partitions without loading the country into memory:

```bash
uv run build-address-pipeline --cache cache/geotorget
```

This writes one file per municipality, for example `raw/0114.parquet` and
`enriched/0114.parquet`, under `data/address-pipeline/`. The enriched files add `parish_code`,
`parish_match_status`. Parish, county, and municipality names stay in the SCB
reference tables rather than being duplicated in every address row.

## Compact postcode products

Build current, physical-address-derived postcode products from the enriched
partitions:

```bash
uv run build-address-products
```

The command streams municipal Parquet files and writes these small tables under
`data/address-pipeline/products/`:

- `postcode-post-towns.parquet`
- `postcode-administrative-areas.parquet`
- `postcode-parishes.parquet`
- `postcode-centroids.parquet` (mean address coordinates in EPSG:3006)

## Address ranges

Build physical-address ranges using consecutive odd/even number runs and
consecutive letter suffixes:

```bash
uv run build-address-ranges
```

This writes one municipal file per municipality under
`data/address-pipeline/products/address-ranges/`, plus a manifest reporting the
number of singleton ranges.

## Named postcode coverage

Build the current physical-address equivalent of a postcode/county/municipality/
district/parish table:

```bash
uv run build-postcode-coverage
```

The output `data/address-pipeline/products/postcode-coverage.parquet` contains
only observed combinations and `address_count`; human-readable administrative
names are added from the small reference tables.

## Product commands

Each deliverable can be rebuilt independently, for example:

```bash
uv run build-postcode-centroids
uv run build-address-ranges
uv run build-postcode-coverage
```

`build-postcode-products` remains available when rebuilding the four compact
postcode tables together; `build-address-products` is retained as a backwards-
compatible alias.

Run all current address-derived products after the enriched-address pipeline
with:

```bash
uv run build-all-products --cache cache/geotorget
```

## What's next

When it comes to geodata, Sweden is still in a very unique position. While most other EU countries have understood the value of (open) data as an infrastructure, our Swedish politicians have not and they have kept it locked behind high fees, undermining innovation, transparency and other open data benefits.

In particular, postcode data isn't open in Sweden. And the post company Postnord has given exclusive rights to a [private company](https://www.postnummerservice.se/om-oss/) to sell the data, a strange monopoly that many have questioned since it started in 2005 but that still exists today.

Since 2019, the EU Commission has informed member states that they would need to open certain [*High Value datasets*](https://digital-strategy.ec.europa.eu/en/news/commission-defines-high-value-datasets-be-made-available-re-use) and a directive was introduced in 2022 to that end. Some Swedish agencies like Lantmäteriet dragged their feet until the 2024 deadline and even obtained a final exemption until February 2025 but the time has come for them to free their data.

And this data contains postcode information, making it possible for new services to emerge and provide postcode data in a way that's useful for businesses and other critical needs. Exciting times ahead!
