# Postnummerupproret 3.0

A simple script to download the dataset [Belägenhetsadress Nedladdning, vektor](https://geotorget.lantmateriet.se/geodataprodukter/belagenhetsadress-nedladdning-vektor-api) from the APIs of the Swedish mapping, cadastral and land registration authority (*Lantmäteriet).

This dataset contains all addresses from all municipalities in Sweden.

Once downloaded, the script unzips the files, opens them with GeoPandas and keeps the columns "postnummer" (postcodes) and "geometry" (containing a single coordinate in [EPSG:3006](https://spatialreference.org/ref/epsg/3006/)). It concatenates data from all the municipalities and exports it as parquet.

I uploaded the parquet file on [HuggingFace](https://huggingface.co/datasets/PierreMesure/swedish_postcodes) for people to reuse it, it can be used as a ground truth for the location of postcodes in Sweden.

## How to reuse

You will need an account on Geotorget with the access rights to the dataset.

```bash
cp .env.example .env
```

Put your username and password in the newly created `.env` file.

Then setup the project with Python:

```bash
pip install -r requirements.txt
```

And download the data:

```bash
python download.py
```

## What's next

When it comes to geodata, Sweden is still in a very unique position. While most other EU countries have understood the value of (open) data as an infrastructure, our Swedish politicians have not and they have kept it locked behind high fees, undermining innovation, transparency and other open data benefits.

In particular, postcode data isn't open in Sweden. And the post company Postnord has given exclusive rights to a [private company](https://www.postnummerservice.se/om-oss/) to sell the data, a strange monopoly that many have questioned since it started in 2005 but that still exists today.

Since 2019, the EU Commission has informed member states that they would need to open certain [*High Value datasets*](https://digital-strategy.ec.europa.eu/en/news/commission-defines-high-value-datasets-be-made-available-re-use) and a directive was introduced in 2022 to that end. Some Swedish agencies like Lantmäteriet dragged their feet until the 2024 deadline and even obtained a final exemption until February 2025 but the time has come for them to free their data.

And this data contains postcode information, making it possible for new services to emerge and provide postcode data in a way that's useful for businesses and other critical needs. Exciting times ahead!
