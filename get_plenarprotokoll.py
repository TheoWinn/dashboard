import requests
import pandas as pd
import re, html

BASE = "https://search.dip.bundestag.de/api/v1"
API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"

# URLs and headers (_meta only entails meta information, _text includes the full text + meta)
url_meta = f"{BASE}/plenarprotokoll/" 
url_text = f"{BASE}/plenarprotokoll-text/"
headers = {"Authorization": f"ApiKey {API_KEY}"}

# Get plenarprotokoll for a specific date (2025-09-23)
params = {"f.datum.start": "2025-09-23",
          "f.datum.end": "2025-09-23"}

# request and normalize JSON response to pandas DataFrame
r_meta = requests.get(url_meta, headers=headers, params=params, timeout=30) # should return exactly one document
data_meta = r_meta.json()["documents"] 
data_meta = pd.json_normalize(data_meta)

# get full text version
r_text = requests.get(url_text, headers=headers, params=params, timeout=30)
data_text = r_text.json()["documents"]
data_text = pd.json_normalize(data_text)

# get only the plain text (without meta)
onlytext = r_text.json()["documents"][0]["text"]

# function to clean strings for export
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

# clean and export to Excel and txt
data_meta = data_meta.map(clean_excel_string)
data_meta.to_excel("data/plenarprotokoll-meta-2025-09-23.xlsx", index=False, engine="openpyxl")

data_text = data_text.map(clean_excel_string)
data_text.to_excel("data/plenarprotokoll-text-2025-09-23.xlsx", index=False, engine="openpyxl")

with open("data/plenarprotkoll-nurtext-2025-09-03.txt", "w+", encoding="utf-8") as text_file:
    text_file.write(clean_excel_string(onlytext))


####################################################
# ARCHIVE: get all vorgänge since 2025-01-01

# url = f"{BASE}/vorgang" 
# headers = {"Authorization": f"ApiKey {API_KEY}"}

# all_docs = []
# cursor="*"

# # infinite loop
# while True: 
#     params = {"cursor": cursor,
#               "rows": 100, # max 100
#               "f.datum.start": "2025-01-01"}  
#     r = requests.get(url, headers=headers, params=params, timeout=30)
#     data = r.json()
#     docs = data.get("documents", [])
#     if not docs:
#         break
#     all_docs.extend(docs)
#     print(f"Fetched {len(all_docs)} / {data.get('numFound')}")

#     new_cursor = data.get("cursor")
#     if not new_cursor or new_cursor == cursor:
#         break
#     cursor = new_cursor


# df = pd.json_normalize(all_docs)






