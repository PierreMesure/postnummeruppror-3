# Postcode centroids

`postcode-centroids.parquet` contains arithmetic mean coordinates for current physical address points in each postcode/post-town combination.

Build it with `uv run build-postcode-centroids`.

| Column | Type | Description |
| --- | --- | --- |
| `postcode` | string | Five-digit postcode. |
| `post_town` | string | Postort. |
| `address_count` | integer | Number of address points used. |
| `x` | float | Mean easting in SWEREF 99 TM (EPSG:3006). |
| `y` | float | Mean northing in SWEREF 99 TM (EPSG:3006). |

These are address-derived representative points, not official postal centroids.
