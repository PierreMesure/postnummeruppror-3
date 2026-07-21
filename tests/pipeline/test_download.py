from swedish_addresses.pipeline.download import (
    MUNICIPALITY_COUNT,
    gpkg_for_dataset,
    municipality_sources,
)


class FakeClient:
    def __init__(self):
        self.downloads: list[str] = []

    def get_municipality_gpkg(self, municipality_code: str) -> bytes:
        self.downloads.append(municipality_code)
        return b"new GeoPackage"

    def list_municipalities(self):
        raise AssertionError("The cached request must not list municipalities")


def test_gpkg_for_dataset_reuses_existing_cache(tmp_path):
    client = FakeClient()
    cache_path = tmp_path / "0180.gpkg"
    cache_path.write_bytes(b"cached GeoPackage")

    gpkg_bytes, cached = gpkg_for_dataset(client, "0180", tmp_path)

    assert gpkg_bytes == b"cached GeoPackage"
    assert cached is True
    assert client.downloads == []


def test_gpkg_for_dataset_downloads_and_populates_cache(tmp_path):
    client = FakeClient()

    gpkg_bytes, cached = gpkg_for_dataset(client, "0180", tmp_path)

    assert gpkg_bytes == b"new GeoPackage"
    assert cached is False
    assert client.downloads == ["0180"]
    assert (tmp_path / "0180.gpkg").read_bytes() == b"new GeoPackage"


def test_municipality_sources_uses_explicit_cached_request_without_api(tmp_path):
    (tmp_path / "0180.gpkg").write_bytes(b"cached GeoPackage")

    sources = municipality_sources(FakeClient(), tmp_path, ["0180"])

    assert sources == [("0180", "cached GeoPackage")]


def test_municipality_sources_uses_complete_cache_without_api(tmp_path):
    for code in range(MUNICIPALITY_COUNT):
        (tmp_path / f"{code:04}.gpkg").touch()

    sources = municipality_sources(FakeClient(), tmp_path)

    assert len(sources) == MUNICIPALITY_COUNT
    assert sources[0] == ("0000", "cached GeoPackage")
    assert sources[-1] == ("0289", "cached GeoPackage")
