import pandas as pd

SCB_REGIONS_URL = "https://www.scb.se/contentassets/7a89e48960f741e08918e489ea36354a/kommunlankod_2025.xls"
REGION_NAMES_FILE = "region_names.csv"

class Regions:

    def __init__(self):
        try:
            df = pd.read_csv(REGION_NAMES_FILE)
        except FileNotFoundError:
            print("Local file for region names not found, downloading...")
            df = pd.read_excel(SCB_REGIONS_URL, skiprows=5)
            df = df[df["Code"] <= 25]
            df.to_csv(REGION_NAMES_FILE, index=False)

        self.regions = dict(zip(df["Code"], df["Name"]))

    def get_region_name(self, code):
        return self.regions[code] if code in self.regions else None
