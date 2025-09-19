import os
import requests
from typing import List, Dict, Any

# Constants / configuration
API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"#os.getenv("BUNDESTAG_DIP_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "https://www.dip.bundestag.de/api/v1"  # adjust if needed

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def fetch_documents(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch a number of 'Drucksachen' (documents) from the Bundestag API.
    """
    params = {
        "anzahl": limit,   # “anzahl” = number of items (German APIs often use such terms)
        # possibly other filters like date, type, etc.
    }
    url = f"{BASE_URL}/drucksachen"  # check the correct endpoint path
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json()
    # The structure of JSON may have e.g. data["items"] or similar
    return data.get("Data", []) or data.get("items", []) or data

def fetch_persons(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch a number of persons (MdBs etc.)
    """
    params = {
        "anzahl": limit,
    }
    url = f"{BASE_URL}/personen"
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json()
    return data.get("Data", []) or data.get("items", []) or data

def main():
    # Fetch documents
    docs = fetch_documents(limit=10)
    print("Documents:")
    for d in docs:
        print(f"- ID: {d.get('id')}, Title: {d.get('titel')}")
    
    # Fetch persons
    persons = fetch_persons(limit=10)
    print("Persons:")
    for p in persons:
        print(f"- {p.get('id')}, Name: {p.get('vorname')} {p.get('nachname')}")

if __name__ == "__main__":
    main()
