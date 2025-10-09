import requests
import pandas as pd
import re, html

BASE = "https://search.dip.bundestag.de/api/v1"
API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"

url = f"{BASE}/vorgang" 
headers = {"Authorization": f"ApiKey {API_KEY}"}

all_docs = []
cursor="*"

# infinite loop
while True: 
    params = {"cursor": cursor,
              "rows": 100, # max 100
              "f.datum.start": "2025-01-01"}  
    r = requests.get(url, headers=headers, params=params, timeout=30)
    data = r.json()
    docs = data.get("documents", [])
    if not docs:
        break
    all_docs.extend(docs)
    print(f"Fetched {len(all_docs)} / {data.get('numFound')}")

    new_cursor = data.get("cursor")
    if not new_cursor or new_cursor == cursor:
        break
    cursor = new_cursor


df = pd.json_normalize(all_docs)


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

df = df.map(clean_excel_string)
df.to_csv("data/vorgang.csv", index=False, encoding="utf-8-sig")
df.to_excel("data/vorgang.xlsx", index=False, engine="openpyxl")
print(f"Saved {len(df)} rows to all_results.csv")



