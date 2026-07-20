# Postcode parishes

`postcode-parishes.parquet` is a many-to-many postcode-to-parish crosswalk. Each relationship is observed by spatially assigning address points to Svenska kyrkan parish polygons.

Build it with `uv run build-postcode-parishes`.

| Column | Type | Description |
| --- | --- | --- |
| `postcode` | string | Five-digit postcode. |
| `parish_code` | string | Six-digit LKF parish code. |
| `address_count` | integer | Number of spatially matched address points. |

Unmatched address points are excluded. A postcode may legitimately occur in more than one parish.
