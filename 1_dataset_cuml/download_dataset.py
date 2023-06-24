"""
This script takes destination path as an argument
"""
import os
import sys

import pandas as pd
import requests


def download_file(url, destination, chunk_size=32768):
    with requests.get(url, stream=True) as r:
        with open(destination, "wb") as f:
            for chunk in r.iter_content(chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)


if __name__ == "__main__":

    data_path = sys.argv[1]
    download_urls = pd.read_html("https://jiachengli1995.github.io/google/index.html", extract_links="all")[1]

    for item in download_urls.iterrows():
        print(item[1][0][0])
        for which, url in zip(["review", "meta"], [item[1][1][1], item[1][2][1]]):
            destination = f'{data_path}/{which}-{item[1][0][0]}.json.gz'
            download_file(url, destination)
            print(f"{destination} done")
    os.system(f"gzip -d {data_path}/*.json.gz")
