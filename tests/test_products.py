import pandas as pd

from swedish_addresses.products import build_products, partition_files


def test_build_products_aggregates_municipal_partitions(tmp_path):
    source = tmp_path / "enriched"
    source.mkdir()
    pd.DataFrame(
        {
            "postcode": ["11122", "11122", "11123"],
            "post_town": ["Stockholm", "Stockholm", "Stockholm"],
            "county_code": ["01", "01", "01"],
            "municipality_code": ["0180", "0180", "0180"],
            "district_code": ["018001", "018001", "018002"],
            "parish_code": ["018001", "018001", None],
            "parish_match_status": ["matched", "matched", "unmatched"],
            "x": [1.0, 3.0, 10.0],
            "y": [2.0, 4.0, 20.0],
        }
    ).to_parquet(source / "0180.parquet", index=False)

    counts = build_products(source, tmp_path / "products")

    assert counts["postcode_parish_rows"] == 1
    parishes = pd.read_parquet(tmp_path / "products/postcode-parishes.parquet")
    assert parishes.to_dict("records") == [{"postcode": "11122", "parish_code": "018001", "address_count": 2}]
    centroids = pd.read_parquet(tmp_path / "products/postcode-centroids.parquet")
    assert centroids.loc[centroids["postcode"].eq("11122"), ["x", "y"]].iloc[0].to_dict() == {"x": 2.0, "y": 3.0}


def test_partition_files_supports_previous_hive_layout(tmp_path):
    legacy = tmp_path / "municipality_code=0114"
    legacy.mkdir()
    (legacy / "addresses.parquet").touch()

    assert partition_files(tmp_path) == [legacy / "addresses.parquet"]


def test_build_products_can_select_one_deliverable(tmp_path):
    source = tmp_path / "enriched"
    source.mkdir()
    pd.DataFrame(
        {
            "postcode": ["11122"], "post_town": ["Stockholm"], "county_code": ["01"],
            "municipality_code": ["0180"], "district_code": ["018001"],
            "parish_code": ["018001"], "parish_match_status": ["matched"], "x": [1.0], "y": [2.0],
        }
    ).to_parquet(source / "0180.parquet", index=False)

    build_products(source, tmp_path / "products", {"postcode-centroids"})

    assert (tmp_path / "products/postcode-centroids.parquet").is_file()
    assert not (tmp_path / "products/postcode-parishes.parquet").exists()
