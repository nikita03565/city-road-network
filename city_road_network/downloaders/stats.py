import os
import zipfile
from pathlib import Path
from typing import Literal

import pandas as pd
import requests

from city_road_network.config import nhts_url, rus_pop_url
from city_road_network.utils.utils import get_cache_subdir, get_logger

logger = get_logger(__name__)

cache_dir = get_cache_subdir()
nhts_zip_path = os.path.join(cache_dir, "nhts.zip")
nhts_path = os.path.join(cache_dir, "nhts")
russtat_path = os.path.join(cache_dir, "russtat.xlsx")


def download_russtat_data():
    """Downloads XLSX file describing average household size in Russia"""
    response = requests.get(rus_pop_url)
    response.raise_for_status()
    with open(russtat_path, "wb") as f:
        f.write(response.content)


def download_nhts_data():
    """Downloads NHTS data and extracts archive."""
    if not Path(nhts_zip_path).is_file():
        response = requests.get(nhts_url)
        response.raise_for_status()
        with open(nhts_zip_path, "wb") as f:
            f.write(response.content)
        logger.info("Saved nhts archive to %s", os.path.abspath(nhts_zip_path))

    with zipfile.ZipFile(nhts_zip_path, "r") as zip_file:
        zip_file.extractall(nhts_path)
    logger.info("Extracted nhts to %s. Directory content: %s", os.path.abspath(nhts_path), os.listdir(nhts_path))


def get_nhts_dataset(name: Literal["vehpub.csv", "perpub.csv", "hhpub.csv", "trippub.csv"]) -> pd.DataFrame:
    """Reads one of files from NHTS. Downloads data if not present in cache.

    :param name: Name of dataset.
    :type name: Literal[&quot;vehpub.csv&quot;, &quot;perpub.csv&quot;, &quot;hhpub.csv&quot;, &quot;trippub.csv&quot;]
    :return: NHTS dataset as Pandas DataFrame.
    :rtype: pd.DataFrame
    """
    csv_path = os.path.join(nhts_path, name)
    if not Path(csv_path).is_file():
        download_nhts_data()
    df = pd.read_csv(csv_path)
    return df


def transform_russtat_data(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms XLSX file describing average household size in Russia to appropriate form.

    :param df: DataFrame containing results of `pd.read_excel`.
    :type df: pd.DataFrame
    :return: Transformed DataFrame.
    :rtype: pd.DataFrame
    """
    records = df.to_dict("records")
    city_line = "Городские населенные пункты"
    village_line = "Сельские населенные пункты"
    filler = "в том числе:"
    new_records = []
    for idx, rec in enumerate(records[:-2]):
        if rec["region"] in (city_line, village_line, filler):
            continue
        if city_line != records[idx + 1]["region"]:
            new_records.append({**rec, "avg_city_hh_size": rec["avg_hh_size"]})
            continue
        city_row = records[idx + 1]
        assert city_line == city_row["region"], city_row
        new_records.append({**rec, "avg_city_hh_size": city_row["avg_hh_size"]})

    new_df = pd.DataFrame(new_records)
    new_df["region"] = new_df["region"].str.replace("\n", "", regex=False)
    return new_df


def get_russtat_data() -> pd.DataFrame:
    """Downloads XLSX file describing average household size in Russia or reads from cache and transforms to appropriate form.

    :return: DataFrame describing average household size in Russia.
    :rtype: pd.DataFrame
    """
    if not Path(russtat_path).is_file():
        logger.info("Russstat data was not found. Downloading...")
        download_russtat_data()

    df = pd.read_excel(
        russtat_path,
        skiprows=4,
        names=[
            "region",
            "hh_count",
            "pop_count",
            "hh_size_1",
            "hh_size_2",
            "hh_size_3",
            "hh_size_4",
            "hh_size_5",
            "hh_size_6",
            "hh_size_6_count",
            "avg_hh_size",
        ],
    )
    return transform_russtat_data(df)
