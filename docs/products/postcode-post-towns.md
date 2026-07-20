# Postcode post towns

`postcode-post-towns.parquet` lists every observed current pair of five-digit postcode and post town, with the number of address points supporting it.

Build it with `uv run build-postcode-post-towns`.

| Column | Type | Description |
| --- | --- | --- |
| `postcode` | string | Five-digit postcode from the address record. |
| `post_town` | string | Postort from the address record. |
| `address_count` | integer | Number of current physical address points in the pair. |

This is address-derived coverage, not a complete list of administrative or box postcodes.
