# Products

These products are derived from current Lantmäteriet belägenhetsaddress points, enriched with SCB administrative code tables and Svenska kyrkan parish boundaries. They cover physical, geographical addresses only; they do not include box, reply-mail, large-customer, or other administrative postcodes.

| Product | Output | Build command |
| --- | --- | --- |
| [Postcode post towns](products/postcode-post-towns.md) | `postcode-post-towns.parquet` | `build-postcode-post-towns` |
| [Postcode administrative areas](products/postcode-administrative-areas.md) | `postcode-administrative-areas.parquet` | `build-postcode-administrative-areas` |
| [Postcode parishes](products/postcode-parishes.md) | `postcode-parishes.parquet` | `build-postcode-parishes` |
| [Postcode centroids](products/postcode-centroids.md) | `postcode-centroids.parquet` | `build-postcode-centroids` |
| [Address ranges](products/address-ranges.md) | `address-ranges/*.parquet` | `build-address-ranges` |
| [Named postcode coverage](products/postcode-coverage.md) | `postcode-coverage.parquet` | `build-postcode-coverage` |

Run every current product with:

```bash
uv run build-all-products --cache cache/geotorget --skip-existing-ranges
```
