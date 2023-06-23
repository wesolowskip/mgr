"""
This script takes destination path as an argument
"""
import re
import sys

import pandas as pd
import requests


def download_file_from_google_drive(id, destination):
    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    params = {'id': id, 'confirm': 1}
    response = session.get(URL, params=params, stream=True)

    save_response_content(response, destination)


def get_confirm_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value

    return None


def save_response_content(response, destination):
    CHUNK_SIZE = 32768

    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)


if __name__ == "__main__":

    data_path = sys.argv[1]
    download_urls = pd.read_html("https://jiachengli1995.github.io/google/index.html", extract_links="all")[1]

    for item in download_urls.iterrows():
        print(item[1][0][0])
        for which, url in zip(["review", "meta"], [item[1][1][1], item[1][2][1]]):
            file_id = re.match(r".*?/d/([^/]+)/", url).group(1)
            destination = f'{data_path}/{which}-{item[1][0][0]}.json.gz'
            download_file_from_google_drive(file_id, destination)
            print(f"{destination} done")
    os.system(f"gzip -d {data_path}/*.json.gz")
