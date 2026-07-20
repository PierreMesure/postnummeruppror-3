# Postcode administrative areas

`postcode-administrative-areas.parquet` records every observed relationship between a postcode and its county, municipality, and statistical district.

Build it with `uv run build-postcode-administrative-areas`.

| Column | Type | Description |
| --- | --- | --- |
| `postcode` | string | Five-digit postcode. |
| `county_code` | string | SCB county code. |
| `municipality_code` | string | SCB municipality code. |
| `district_code` | string | Lantmäteriet district code, where available. |
| `address_count` | integer | Number of current physical address points in the combination. |

Use `postcode-coverage.parquet` when human-readable names and parish code are also needed.
