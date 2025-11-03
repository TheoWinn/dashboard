bt utils 


import requests
import pandas as pd
import os
import xml.etree.ElementTree as ET

###########################
## NOCH ZU KLÄREN!!!!!!
# Was soll mit alten Versionen (get_pleanrprotokoll) passieren?
# Dataordner nochmal anders nennen

###########################

def download_xml_from_metadata(metadata_file, output_dir):
    """Downloads XML files from URLs listed in metadata."""
    # Ensure output_dir ends with slash
    if not output_dir.endswith('/'):
        output_dir += '/'
        
    # Create xml directory if it doesn't exist
    xml_dir = os.path.join(output_dir, "xml")
    os.makedirs(xml_dir, exist_ok=True)
    print(f"Using XML directory: {xml_dir}")
    
    print(f"Reading metadata from: {metadata_file}")
    df = pd.read_csv(metadata_file)
    print(f"Found {len(df)} records in metadata")
    
    for index, row in df.iterrows():
        xml_url = row['fundstelle.xml_url']
        doc_number = row['dokumentnummer'].replace('/', '_')  # Replace / with _
        
        # Debug print
        print(f"Processing document {doc_number} with URL: {xml_url}")
        
        # Create filename from document number using os.path.join
        xml_filename = os.path.join(xml_dir, f"{doc_number}.xml")
        
        try:
            response = requests.get(xml_url, timeout=30)
            response.raise_for_status()
            
            with open(xml_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Successfully downloaded XML for document {doc_number}")
            
        except requests.RequestException as e:
            print(f"Error downloading {doc_number}: {e}")


def create_cut_xml(input_file, output_file):
    """
    Parse a plenary XML and, for every <rede id="...">:
      - read speaker (vorname, nachname, fraktion OR rolle)
      - collect ONLY the speaker's own paragraphs (<p> …) after the redner line
      - skip all <kommentar> (interjections) completely
      - stop collecting when a bare <name> tag appears (chair taking the floor)
    Write a compact XML with <speeches><speech><id/><speaker/><party_or_role/><content/></speech>…</speeches>.
    """
    tree = ET.parse(input_file)
    root = tree.getroot()

    # helper: full text of an element (text + children)
    def element_full_text(el):
        parts = []
        if el.text:
            parts.append(el.text)
        for c in el:
            parts.append(element_full_text(c))
            if c.tail:
                parts.append(c.tail)
        return "".join(parts).strip()

    out_root = ET.Element("speeches")

    # iterate all rede blocks
    for rede in root.findall(".//rede"):
        rede_id = rede.get("id", "")

        # 1) speaker block: the first paragraph with class="redner"
        p_redner = rede.find('./p[@klasse="redner"]')
        if p_redner is None:
            # no speaker line? skip this rede
            continue

        name_node = p_redner.find("./redner/name")
        if name_node is None:
            # sometimes structure differs; be defensive
            name_node = rede.find(".//redner/name")

        # extract name parts
        vorname  = (name_node.findtext("vorname") or "").strip() if name_node is not None else ""
        nachname = (name_node.findtext("nachname") or "").strip() if name_node is not None else ""

        # fraktion OR rolle (prefer fraktion if present)
        fraktion = name_node.findtext("fraktion") if name_node is not None else None
        rolle_kurz = name_node.findtext("rolle/rolle_kurz") if name_node is not None else None
        rolle_lang = name_node.findtext("rolle/rolle_lang") if name_node is not None else None
        party_or_role = (fraktion or rolle_kurz or rolle_lang or "").strip()

        # 2) collect speaker's own paragraphs:
        #    everything after the redner paragraph, ignoring <kommentar>,
        #    and stopping at a bare <name> (chair speaking)
        content_chunks = []
        started = False
        stop = False
        for child in list(rede):
            if child is p_redner:
                started = True
                continue
            if not started or stop:
                continue

            tag = child.tag.lower()

            # stop when the chair's <name> appears
            if tag == "name":
                stop = True
                continue

            # skip all comments/interjections
            if tag == "kommentar":
                continue

            # collect paragraphs only
            if tag == "p":
                text = element_full_text(child)
                if text:
                    content_chunks.append(text)

        content_text = " ".join(content_chunks).strip()

        # only add if we actually have content
        if content_text:
            sp_el = ET.SubElement(out_root, "speech")
            ET.SubElement(sp_el, "id").text = rede_id
            ET.SubElement(sp_el, "speaker").text = f"{vorname} {nachname}".strip()
            ET.SubElement(sp_el, "party_or_role").text = party_or_role
            ET.SubElement(sp_el, "content").text = content_text

    # ensure output directory exists
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

    ET.ElementTree(out_root).write(output_file, encoding="utf-8", xml_declaration=True)


def download_pp(base, api_key, start_date="2025-10-01", end_date=None, output_dir="data/raw"):
    """Downloads metadata and XML files from the API."""
    
    # Ensure output_dir exists and ends with slash
    if not output_dir.endswith('/'):
        output_dir += '/'
    
    # Create all necessary directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "xml"), exist_ok=True)
    
    url = f"{base}/plenarprotokoll-text"
    headers = {"Authorization": f"ApiKey {api_key}"}
    cursor = "*"

    # Initialize metadata
    metadata_file = os.path.join(output_dir, "metadata.csv")
    if os.path.isfile(metadata_file):
        meta = pd.read_csv(metadata_file, dtype={"id": str}, 
                          parse_dates=["aktualisiert"], encoding="utf-8-sig")
        ids = meta["id"].tolist()
    else:
        meta = pd.DataFrame()
        ids = []

    new_meta = []
    new_versions = []

    # Fetch documents
    while True:
        params = {"cursor": cursor, "rows": 100, 
                 "f.datum.start": start_date, "f.datum.end": end_date}
        r = requests.get(url, headers=headers, params=params, timeout=30)
        data = r.json()
        docs = data.get("documents")

        if not docs:
            break
        
        for doc in docs:
            if doc.get("herausgeber") == "BR":
                continue
                
            aktualisiert = pd.to_datetime(doc.get("aktualisiert"), 
                                         utc=True, errors="coerce").tz_convert(None)
            id = str(doc.get("id"))
            
            if id in ids:
                if aktualisiert <= meta.loc[meta["id"] == id, "aktualisiert"].values[0]:
                    continue
                else:
                    new_versions.append(doc)

            new_meta.append(doc)

        new_cursor = data.get("cursor")
        if not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor

    # Save metadata and download XML files
    if new_meta:
        new_meta_df = pd.json_normalize(new_meta)
        new_meta_df = new_meta_df.drop(columns=["text"], errors='ignore')
        new_meta_df["id"] = new_meta_df["id"].astype(str)
        new_meta_df["aktualisiert"] = pd.to_datetime(new_meta_df["aktualisiert"], 
                                                    utc=True, errors="coerce")
        meta_df = pd.concat([meta, new_meta_df], ignore_index=True)
        meta_df.to_csv(metadata_file, index=False, encoding="utf-8-sig")
        print(f"Saved metadata to {metadata_file}")
        
        # Download XML files
        download_xml_from_metadata(metadata_file, output_dir)

        # Create cut XML files for each downloaded XML
        meta_latest = pd.read_csv(metadata_file, dtype=str)
        # use dokumentnummer if available, else id
        meta_latest["docnum"] = meta_latest["dokumentnummer"].fillna(meta_latest["id"])
        meta_latest["docnum"] = meta_latest["docnum"].str.replace("/", "_")

        cut_made = 0
        for docnum in meta_latest["docnum"]:
            input_xml_file = os.path.join(output_dir, "xml", f"{docnum}.xml")
            output_cut_file = os.path.join(output_dir, "cut", f"{docnum}_cut.xml")

            if os.path.isfile(input_xml_file):
                print(f"Creating cut XML for {input_xml_file}...")
                create_cut_xml(input_xml_file, output_cut_file)
                print(f"Cut XML created: {output_cut_file}")
                cut_made += 1
            else:
                print(f"[SKIP] XML not found: {input_xml_file}")

        print(f"[CUT] created={cut_made}")
        
    else:
        print("No new protocols found.")

    print(f"Number of new versions: {len(new_versions)}")

# if __name__ == "__main__":
#     # Example usage:
#     download_pp(
#         base="https://search.dip.bundestag.de/api/v1",
#         api_key="OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw",
#         start_date="2025-10-01",
#         end_date=None,
#         output_dir="data/raw/"
#     )



###############################  ARCHIVE #####################################
# import requests
# import pandas as pd
# import os
# import xml.etree.ElementTree as ET

# ###########################
# ## NOCH ZU KLÄREN!!!!!!
# # Was soll mit alten Versionen (get_pleanrprotokoll) passieren?
# ###########################

# def download_xml_from_metadata(metadata_file, output_dir):
#     """Downloads XML files from URLs listed in metadata."""
#     # Ensure output_dir ends with slash
#     if not output_dir.endswith('/'):
#         output_dir += '/'
        
#     # Create xml directory if it doesn't exist
#     xml_dir = os.path.join(output_dir, "xml")
#     os.makedirs(xml_dir, exist_ok=True)
#     print(f"Using XML directory: {xml_dir}")
    
#     print(f"Reading metadata from: {metadata_file}")
#     df = pd.read_csv(metadata_file)
#     print(f"Found {len(df)} records in metadata")
    
#     for index, row in df.iterrows():
#         xml_url = row['fundstelle.xml_url']
#         doc_number = row['dokumentnummer'].replace('/', '_')  # Replace / with _
        
#         # Debug print
#         print(f"Processing document {doc_number} with URL: {xml_url}")
        
#         # Create filename from document number using os.path.join
#         xml_filename = os.path.join(xml_dir, f"{doc_number}.xml")
        
#         try:
#             response = requests.get(xml_url, timeout=30)
#             response.raise_for_status()
            
#             with open(xml_filename, 'w', encoding='utf-8') as f:
#                 f.write(response.text)
#             print(f"Successfully downloaded XML for document {doc_number}")
            
#         except requests.RequestException as e:
#             print(f"Error downloading {doc_number}: {e}")


# def create_cut_xml(input_file, output_file):
#     """Creates a new XML file with only the speaker's name, party, and speech content."""
    
#     # Parse the original XML file
#     tree = ET.parse(input_file)
#     root = tree.getroot()

#     # Create the root element for the new XML
#     new_root = ET.Element("speeches")

#     # Iterate through each speech in the original XML
#     for rede in root.findall('rede'):
#         # Extract speaker information
#         speaker_info = rede.find('.//redner/name')
#         if speaker_info is not None:
#             first_name = speaker_info.find('vorname').text
#             last_name = speaker_info.find('nachname').text
#             party = speaker_info.find('fraktion').text
#             full_name = f"{first_name} {last_name} ({party})"

#             # Create a new speech element
#             speech_element = ET.SubElement(new_root, "speech")
#             ET.SubElement(speech_element, "speaker").text = full_name
            
#             # Extract speech content
#             speech_content = []
#             for p in rede.findall('p'):
#                 speech_content.append(p.text)
            
#             # Join the speech content and add to the new XML
#             ET.SubElement(speech_element, "content").text = " ".join(speech_content)

#     # Write the new XML to a file
#     new_tree = ET.ElementTree(new_root)
#     new_tree.write(output_file, encoding='utf-8', xml_declaration=True)



# def download_pp(base, api_key, start_date="2025-10-01", end_date=None, output_dir="data/raw"):
#     """Downloads metadata and XML files from the API."""
    
#     # Ensure output_dir exists and ends with slash
#     if not output_dir.endswith('/'):
#         output_dir += '/'
    
#     # Create all necessary directories
#     os.makedirs(output_dir, exist_ok=True)
#     os.makedirs(os.path.join(output_dir, "xml"), exist_ok=True)
    
#     url = f"{base}/plenarprotokoll-text"
#     headers = {"Authorization": f"ApiKey {api_key}"}
#     cursor = "*"

#     # Initialize metadata
#     metadata_file = os.path.join(output_dir, "metadata.csv")
#     if os.path.isfile(metadata_file):
#         meta = pd.read_csv(metadata_file, dtype={"id": str}, 
#                           parse_dates=["aktualisiert"], encoding="utf-8-sig")
#         ids = meta["id"].tolist()
#     else:
#         meta = pd.DataFrame()
#         ids = []

#     new_meta = []
#     new_versions = []

#     # Fetch documents
#     while True:
#         params = {"cursor": cursor, "rows": 100, 
#                  "f.datum.start": start_date, "f.datum.end": end_date}
#         r = requests.get(url, headers=headers, params=params, timeout=30)
#         data = r.json()
#         docs = data.get("documents")

#         if not docs:
#             break
        
#         for doc in docs:
#             if doc.get("herausgeber") == "BR":
#                 continue
                
#             aktualisiert = pd.to_datetime(doc.get("aktualisiert"), 
#                                          utc=True, errors="coerce").tz_convert(None)
#             id = str(doc.get("id"))
            
#             if id in ids:
#                 if aktualisiert <= meta.loc[meta["id"] == id, "aktualisiert"].values[0]:
#                     continue
#                 else:
#                     new_versions.append(doc)

#             new_meta.append(doc)

#         new_cursor = data.get("cursor")
#         if not new_cursor or new_cursor == cursor:
#             break
#         cursor = new_cursor

#     # Save metadata and download XML files
#     if new_meta:
#         new_meta_df = pd.json_normalize(new_meta)
#         new_meta_df = new_meta_df.drop(columns=["text"], errors='ignore')
#         new_meta_df["id"] = new_meta_df["id"].astype(str)
#         new_meta_df["aktualisiert"] = pd.to_datetime(new_meta_df["aktualisiert"], 
#                                                     utc=True, errors="coerce")
#         meta_df = pd.concat([meta, new_meta_df], ignore_index=True)
#         meta_df.to_csv(metadata_file, index=False, encoding="utf-8-sig")
#         print(f"Saved metadata to {metadata_file}")
        
#         # Download XML files
#         download_xml_from_metadata(metadata_file, output_dir)

#         # Create cut XML files for each downloaded XML
#         for doc in new_meta:
#             doc_number = doc.get("id").replace('/', '_')  # Ensure valid filename
#             input_xml_file = os.path.join(output_dir, "xml", f"{doc_number}.xml")
#             output_cut_file = os.path.join(output_dir, "xml", f"{doc_number}_cut.xml")
#             create_cut_xml(input_xml_file, output_cut_file)

#     else:
#         print("No new protocols found.")

#     print(f"Number of new versions: {len(new_versions)}")

# if __name__ == "__main__":
#     # Example usage:
#     download_pp(
#         base="https://search.dip.bundestag.de/api/v1",
#         api_key="OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw",
#         start_date="2025-10-01",
#         end_date=None,
#         output_dir="data/raw/"
#     )





###############################################################################

# def download_pp(
#         base,
#         api_key, 
#         start_date="2025-10-01", 
#         end_date=None,
#         output_dir="data/raw" #change to data/raw_plenarprotokolle/ 
#         ):
    
#     url = f"{base}/plenarprotokoll-text"
#     headers = {"Authorization": f"ApiKey {api_key}"}

#     cursor="*"

#     if os.path.isfile(output_dir + "metadata.csv"):
#         meta = pd.read_csv(output_dir + "metadata.csv",
#                            dtype={"id": str},                      # keep id as string
#                            parse_dates=["aktualisiert"],           # parse as datetime
#                            encoding="utf-8-sig")
#         ids = meta["id"].tolist()
#     else:
#         meta = pd.DataFrame()
#         ids = []

#     new_meta = []  
#     new_versions = []

#     while True:
#         params = {"cursor": cursor,
#                   "rows": 100, # max 100
#                   "f.datum.start": start_date,
#                   "f.datum.end": end_date}
#         r = requests.get(url, headers=headers, params=params, timeout=30)
#         data = r.json()
#         docs = data.get("documents")

#         if not docs:
#             break
        
#         for doc in docs:

#             if doc.get("herausgeber") == "BR":
#                 continue
#             aktualisiert = pd.to_datetime(doc.get("aktualisiert"), utc=True, errors="coerce").tz_convert(None)
#             id = str(doc.get("id"))
#             if id in ids:
#                 if aktualisiert <= meta.loc[meta["id"] == id, "aktualisiert"].values[0]:
#                     continue
#                 else:
#                     new_versions.append(doc)
#                     # was soll mit alten versionen passieren?
#             filename = output_dir + doc.get("titel") + "_" + doc.get("aktualisiert")[0:10] + ".txt"
#             with open(filename, "w+", encoding="utf-8") as text_file:
#                 text_file.write(doc.get("text"))

#             new_meta.append(doc)
            

#         new_cursor = data.get("cursor")
#         if not new_cursor or new_cursor == cursor:
#             break
#         cursor = new_cursor

#     if new_meta:
#         new_meta_df = pd.json_normalize(new_meta)
#         #new_meta_df = new_meta_df[["id", "titel", "datum", "aktualisiert", "herausgeber", "dokumentnummer", "wahlperiode"]]
#         new_meta_df = new_meta_df.drop(columns=["text"])
#         new_meta_df["id"] = new_meta_df["id"].astype(str)
#         new_meta_df["aktualisiert"] = pd.to_datetime(new_meta_df["aktualisiert"], utc=True, errors="coerce")
#         meta_df = pd.concat([meta, new_meta_df], ignore_index=True)
#         meta_df.to_csv(output_dir + "metadata.csv", index=False, encoding="utf-8-sig")
#     else:
#         print("No new protocols found.")

#     print(f"number of new versions: {len(new_versions)}") # what to do with updated versions?
    
# # Example usage:
# download_pp(base="https://search.dip.bundestag.de/api/v1",
#             api_key="OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw",
#             start_date="2025-10-01",
#             end_date=None,
#             output_dir="data/raw") #change to data/raw_plenarprotokolle/ 