import requests
import pandas as pd
import re, html

BASE = "https://search.dip.bundestag.de/api/v1"
API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"

url_meta = f"{BASE}/plenarprotokoll/" 
url_text = f"{BASE}/plenarprotokoll-text/"
headers = {"Authorization": f"ApiKey {API_KEY}"}

params = {"f.datum.start": "2025-09-23",
          "f.datum.end": "2025-09-23"}

r_meta = requests.get(url_meta, headers=headers, params=params, timeout=30)
data_meta = r_meta.json()["documents"]
data_meta = pd.json_normalize(data_meta)

r_text = requests.get(url_text, headers=headers, params=params, timeout=30)
data_text = r_text.json()["documents"]
data_text = pd.json_normalize(data_text)
onlytext = r_text.json()["documents"][0]["text"]

def clean_excel_string(s):
    if isinstance(s, str):
        # remove illegal control characters for Excel
        s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
        # replace HTML line breaks with newlines
        s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
        # strip other HTML tags
        s = re.sub(r"<[^>]+>", "", s)
        # unescape HTML entities (&ouml; -> ö, &ndash; -> –)
        s = html.unescape(s)
    return s

data_meta = data_meta.map(clean_excel_string)
data_meta.to_excel("data/plenarprotokoll-meta-2025-09-23.xlsx", index=False, engine="openpyxl")

data_text = data_text.map(clean_excel_string)
data_text.to_excel("data/plenarprotokoll-text-2025-09-23.xlsx", index=False, engine="openpyxl")

with open("data/plenarprotkoll-nurtext-2025-09-03.txt", "w+", encoding="utf-8") as text_file:
    text_file.write(clean_excel_string(onlytext))

