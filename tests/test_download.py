import sqlite3

from shapely import Point
from shapely import to_wkb

from swedish_addresses.download import addresses_from_gpkg, gpkg_for_dataset


def test_addresses_from_gpkg_extracts_postcode_and_coordinates(tmp_path):
    gpkg_path = tmp_path / "addresses.gpkg"
    connection = sqlite3.connect(gpkg_path)
    connection.executescript(
        """
        PRAGMA application_id = 1196437808;
        CREATE TABLE gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL, srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL, organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL, description TEXT
        );
        INSERT INTO gpkg_spatial_ref_sys VALUES ('SWEREF99 TM', 3006, 'EPSG', 3006, 'undefined', NULL);
        CREATE TABLE gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL,
            identifier TEXT UNIQUE, description TEXT DEFAULT '', last_change DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE, srs_id INTEGER
        );
        CREATE TABLE gpkg_geometry_columns (
            table_name TEXT NOT NULL, column_name TEXT NOT NULL, geometry_type_name TEXT NOT NULL,
            srs_id INTEGER NOT NULL, z TINYINT NOT NULL, m TINYINT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        );
        CREATE TABLE belagenhetsadress (id INTEGER PRIMARY KEY, postnummer INTEGER, geom BLOB NOT NULL);
        INSERT INTO gpkg_contents (table_name, data_type, identifier, srs_id) VALUES ('belagenhetsadress', 'features', 'addresses', 3006);
        INSERT INTO gpkg_geometry_columns VALUES ('belagenhetsadress', 'geom', 'POINT', 3006, 0, 0);
        """
    )
    # GeoPackage geometry header: magic, version, flags, little-endian SRS id, then WKB.
    header = b"GP" + bytes([0, 1]) + (3006).to_bytes(4, "little", signed=True)
    connection.execute("INSERT INTO belagenhetsadress VALUES (?, ?, ?)", (1, 12345, header + to_wkb(Point(674032, 6580821))))
    connection.commit()
    connection.close()

    result = addresses_from_gpkg(gpkg_path.read_bytes(), "0180")

    assert result.to_dict("records") == [
        {"municipality_code": "0180", "postcode": 12345, "x": 674032.0, "y": 6580821.0}
    ]


class FakeClient:
    def __init__(self):
        self.downloads: list[str] = []

    def get_municipality_gpkg(self, municipality_code: str) -> bytes:
        self.downloads.append(municipality_code)
        return b"new GeoPackage"


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
