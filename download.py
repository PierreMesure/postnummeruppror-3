import os
import requests
import zipfile
import io
from dotenv import load_dotenv
import geopandas as gpd
import pandas as pd

load_dotenv()

URL = "https://api.lantmateriet.se/stac-vektor/v1/collections/belagenhetsadresser"
USERNAME = os.getenv("GEOTORGET_USERNAME")
PASSWORD = os.getenv("GEOTORGET_PASSWORD")

tmp_folder = "tmp"
os.makedirs(tmp_folder, exist_ok=True)


def get_all_links():
    data = requests.get(URL + "/items?limit=300").json()
    return [feature["assets"]["data"]["href"] for feature in data["features"]]


def get_gpkg(link):
    print(f"Downloading municipality {link[-8:-4]}")
    response = requests.get(link, auth=(USERNAME, PASSWORD))

    if response.status_code == 401:
        print("Authorization denied")
        return None
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        for file in zip_file.namelist():
            if file.endswith(".gpkg"):
                # Save the file to tmp directory
                tmp_file_path = os.path.join(tmp_folder, file)
                with zip_file.open(file) as zf:
                    with open(tmp_file_path, 'wb') as f:
                        f.write(zf.read())
                return zip_file.open(file).read()

    return None

gdfs = []

for link in get_all_links():
    data = io.BytesIO(get_gpkg(link))
    gdf = gpd.read_file(data, driver="GPKG", engine="pyogrio", use_arrow=True)
    gdfs.append(gdf[["postnummer", "geometry"]])

gdfs_concat = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
gdfs_concat = gdfs_concat.sort_values(by="postnummer", ignore_index=True)
gdfs_concat = gdfs_concat[gdfs_concat["postnummer"] != 0]
gdfs_concat.to_parquet("swedish_postcodes.parquet", index=False)
