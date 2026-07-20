# Address ranges

The address-range product stores one Parquet file per municipality under `address-ranges/`, for example `address-ranges/0114.parquet`.

Build it with `uv run build-address-ranges`.

| Column | Description |
| --- | --- |
| `address_area`, `address_type` | Address-area name and Lantmäteriet address-place type. |
| `number_from`, `letter_from` | Start of the derived address range. |
| `number_to`, `letter_to` | End of the derived address range. |
| `range_type` | `NU` for odd ranges, `NJ` for even ranges, or `single`. |
| `postcode`, `post_town` | Postal attributes of the range. |
| `county_code`, `municipality_code`, `district_code`, `parish_code` | Administrative codes. |
| `parish_match_status` | Whether parish assignment was spatially matched. |
| `address_count` | Number of source address points represented. |
| `derivation_method` | `numeric_contiguous`, `letter_contiguous`, or `single_source_address`. |

Rules are deliberately conservative: numeric ranges merge only consecutive numbers of the same parity; letter ranges merge only consecutive `A` to `Z` suffixes for one number. Compound, non-standard, and location-qualified addresses remain individual ranges.
