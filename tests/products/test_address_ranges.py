import pandas as pd

from swedish_addresses.products.address_ranges import ranges_for_addresses


def test_ranges_join_only_contiguous_numbers_and_letters():
    shared = {
        "address_area": "Testgatan", "address_type": "Gatuadressplats", "postcode": "11122",
        "post_town": "Stockholm", "county_code": "01", "municipality_code": "0180",
        "district_code": "018001", "parish_code": "018001", "parish_match_status": "matched",
        "location_suffix": None, "location_suffix_number": None, "deviates_from_standard": False,
    }
    frame = pd.DataFrame(
        [
            {**shared, "address_number": "1", "letter_suffix": None},
            {**shared, "address_number": "3", "letter_suffix": None},
            {**shared, "address_number": "7", "letter_suffix": None},
            {**shared, "address_number": "2", "letter_suffix": None},
            {**shared, "address_number": "4", "letter_suffix": None},
            {**shared, "address_number": "9", "letter_suffix": "A"},
            {**shared, "address_number": "9", "letter_suffix": "B"},
            {**shared, "address_number": "9", "letter_suffix": "D"},
            {**shared, "address_number": "107-16", "letter_suffix": None},
        ]
    )

    result = ranges_for_addresses(frame)

    observed = result[["number_from", "letter_from", "number_to", "letter_to", "range_type", "address_count"]].fillna("").to_dict("records")
    assert {tuple(sorted(row.items())) for row in observed} == {tuple(sorted(row.items())) for row in [
        {"number_from": "1", "letter_from": "", "number_to": "3", "letter_to": "", "range_type": "NU", "address_count": 2},
        {"number_from": "7", "letter_from": "", "number_to": "7", "letter_to": "", "range_type": "NU", "address_count": 1},
        {"number_from": "2", "letter_from": "", "number_to": "4", "letter_to": "", "range_type": "NJ", "address_count": 2},
        {"number_from": "9", "letter_from": "A", "number_to": "9", "letter_to": "B", "range_type": "NU", "address_count": 2},
        {"number_from": "9", "letter_from": "D", "number_to": "9", "letter_to": "D", "range_type": "NU", "address_count": 1},
        {"number_from": "107-16", "letter_from": "", "number_to": "107-16", "letter_to": "", "range_type": "single", "address_count": 1},
    ]}
