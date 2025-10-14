import requests

BASE = "https://search.dip.bundestag.de/api/v1"
ID = "1"
API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"

url = f"{BASE}/aktivitaet/{ID}"
headers = {"Authorization": f"ApiKey {API_KEY}"}

r = requests.get(url, headers=headers, timeout=30)
print(r.status_code)
print(r.json())