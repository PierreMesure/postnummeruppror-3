import pandas as pd

from swedish_addresses.coverage import add_names


def test_add_names_joins_small_reference_tables(tmp_path):
    pd.DataFrame([{"county_code": "01", "county_name": "Stockholm"}]).to_csv(tmp_path / "counties-2026.csv", index=False)
    pd.DataFrame([{"municipality_code": "0180", "municipality_name": "Stockholm"}]).to_csv(tmp_path / "municipalities-2026.csv", index=False)
    pd.DataFrame([{"parish_code": "018001", "parish_name": "Domkyrkan"}]).to_csv(tmp_path / "parishes-2026.csv", index=False)
    coverage = pd.DataFrame(
        [{"postcode": "11122", "post_town": "Stockholm", "county_code": "01", "municipality_code": "0180", "district_code": "018001", "parish_code": "018001", "parish_match_status": "matched", "address_count": 2}]
    )

    result = add_names(coverage, tmp_path, {"018001": "Norrmalm"})

    assert result.loc[0, ["county_name", "municipality_name", "district_name", "parish_name"]].to_dict() == {
        "county_name": "Stockholm",
        "municipality_name": "Stockholm",
        "district_name": "Norrmalm",
        "parish_name": "Domkyrkan",
    }
