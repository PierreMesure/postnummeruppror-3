import pandas as pd
from geopandas import GeoDataFrame
from shapely import box

from swedish_addresses.pipeline import enrich_with_parishes, partition_path


def test_partition_path_is_a_flat_municipality_file(tmp_path):
    assert partition_path(tmp_path, "0114") == tmp_path / "0114.parquet"


def test_enrich_with_parishes_assigns_only_containing_polygon():
    addresses = pd.DataFrame(
        {
            "municipality_code": ["0180", "0180"],
            "postcode": ["11122", "11123"],
            "x": [1.0, 3.0],
            "y": [1.0, 1.0],
        }
    )
    parishes = GeoDataFrame(
        {"parish_code": ["018001"]},
        geometry=[box(0, 0, 2, 2)],
        crs="EPSG:3006",
    )

    result = enrich_with_parishes(addresses, parishes)

    assert result["parish_code"].iloc[0] == "018001"
    assert pd.isna(result["parish_code"].iloc[1])
    assert result["parish_match_status"].tolist() == ["matched", "unmatched"]
