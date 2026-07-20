# Named postcode coverage

`postcode-coverage.parquet` is the main user-facing postcode reference table. It contains only administrative/parish combinations actually observed among current physical address points.

Build it with `uv run build-postcode-coverage`.

| Column | Description |
| --- | --- |
| `postcode`, `post_town` | Postal attributes from the address record. |
| `county_code`, `county_name` | SCB county reference. |
| `municipality_code`, `municipality_name` | SCB municipality reference. |
| `district_code`, `district_name` | Lantmäteriet district reference, where source data supplies a code. |
| `parish_code`, `parish_name` | SCB LKF parish reference, where spatially matched. |
| `parish_match_status` | `matched` or `unmatched`. |
| `address_count` | Number of source address points in the exact combination. |

This is the closest current, physical-address-derived equivalent to a postcode file enriched with county, municipality, district, and parish information. It does not represent non-geographical postcodes.
