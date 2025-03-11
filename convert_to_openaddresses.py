import pandas as pd
import geopandas as gpd
import os
from scb import Regions

gdf_list = []
for filename in os.listdir("tmp"):
    if filename.endswith(".gpkg"):
        print(f"Opening {filename}...")
        gdf = gpd.read_file(
            os.path.join("tmp", filename),
            engine="pyogrio",
            use_arrow=True,
            layer="belagenhetsadress",
        )
        gdf_list.append(gdf)

gdfs_concat = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True))
gdfs_concat.to_parquet("swedish_addresses.parquet", index=False)

regions = Regions()

print("Reading the file...")
gdfs_concat = gpd.read_parquet("swedish_addresses.parquet")
# print("Taking a sample of 5000...")
# gdfs_concat = gdfs_concat.sample(5000)
print("Matching region codes with names")
gdfs_concat["region"] = gdfs_concat["lanskod"].apply(regions.get_region_name)
print("Splitting lat, lon...")
gdfs_concat["lat"] = gdfs_concat.geometry.y
gdfs_concat["lon"] = gdfs_concat.geometry.x

gdf_openaddresses = gdfs_concat[
    [
        "kommunnamn",
        "adressomrade_faststalltnamn",
        "adressplatsnummer",
        "bokstavstillagg",
        "distriktsnamn",
        "region",
        "lat",
        "lon",
    ]
]

print("Writing to file...")
gdf_openaddresses.to_csv("swedish_addresses.csv", index=False, compression="zip")
gdf_openaddresses.sample(100).to_csv("swedish_addresses_sample.csv", index=False)
print("All done!")
