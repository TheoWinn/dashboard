import requests
import pandas as pd
import os
import xml.etree.ElementTree as ET

###########################
## NOCH ZU KLÄREN!!!!!!
# Was soll mit alten Versionen (get_pleanrprotokoll) passieren? 
# Cutte: rede brcht ab wenn es eine zwischenfrage gibt (s. 20_25 Peter Bohnhof, Saksia Ludwig), aber kurzinterventionen funktioneren? 21_35 ID213505100
###########################

def download_xml_from_metadata(metadata_file, output_dir):
    """Downloads XML files from URLs listed in metadata."""
    # Ensure output_dir ends with slash
    if not output_dir.endswith('/'):
        output_dir += '/'
        
    # Save XML files directly in output_dir (not in output_dir/xml)
    os.makedirs(output_dir, exist_ok=True)
    
    df = pd.read_csv(metadata_file)
    
    for index, row in df.iterrows():
        xml_url = row['fundstelle.xml_url']
        doc_number = row['dokumentnummer'].replace('/', '_')  # Replace / with _
        
        # Create filename in the output_dir root
        xml_filename = os.path.join(output_dir, f"{doc_number}.xml")
        
        if os.path.isfile(xml_filename):
            continue

        try:
            response = requests.get(xml_url, timeout=30)
            response.raise_for_status()
            
            with open(xml_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Successfully downloaded XML for document {doc_number} -> {xml_filename}")
            
        except requests.RequestException as e:
            print(f"Error downloading {doc_number}: {e}")


def create_cut_xml(input_file, output_file):
    """
    Parse a plenary XML and cut each <rede> into speaker turns:
      - Start a new <speech> at every <p klasse="redner"> (the 'speaker line')
      - Collect only that speaker's own <p> paragraphs until the next <p klasse="redner">
      - Skip all <kommentar> (interjections) and all bare <name> (chair / vice president)
    Output:
      <speeches>
        <speech>
          <id>REDEID-01</id>
          <speaker>Vorname Nachname</speaker>
          <party_or_role>Fraktion or Rolle</party_or_role>
          <content>...</content>
        </speech>
        ...
      </speeches>
    """
    tree = ET.parse(input_file)
    root = tree.getroot()

    # -------- helpers --------------------------------------------------------
    def element_full_text(el):
        """Concatenate el.text + children texts + tails (namespace-agnostic)."""
        parts = []
        if el.text:
            parts.append(el.text)
        for c in el:
            parts.append(element_full_text(c))
            if c.tail:
                parts.append(c.tail)
        return "".join(parts).strip()

    def localname(tag):
        return tag.split("}", 1)[1] if "}" in tag else tag

    def find_descendant_by_local(parent, name):
        for e in parent.iter():
            if localname(e.tag) == name:
                return e
        return None

    def extract_speaker_from_redner_p(p_redner):
        """
        From a <p klasse="redner"> paragraph, extract:
          - speaker's first/last name
          - party (fraktion) OR role (rolle_kurz/rolle/rolle_lang)
          - a best-effort 'speaker_id' from <redner id="..."> if present
        """
        redner_node = find_descendant_by_local(p_redner, "redner")
        speaker_id = ""
        vorname = ""
        nachname = ""
        party_or_role = ""

        if redner_node is not None:
            # id attribute
            speaker_id = redner_node.get("id", "") or ""

            # name fields
            name_node = find_descendant_by_local(redner_node, "name")
            if name_node is not None:
                vn = find_descendant_by_local(name_node, "vorname")
                nn = find_descendant_by_local(name_node, "nachname")
                fr = find_descendant_by_local(name_node, "fraktion")

                # FIX: do not use `or` on Element objects
                rk = find_descendant_by_local(name_node, "rolle_kurz")
                if rk is None:
                    rk = find_descendant_by_local(name_node, "rolle")

                rl = find_descendant_by_local(name_node, "rolle_lang")

                vorname = (vn.text or "").strip() if (vn is not None and vn.text) else ""
                nachname = (nn.text or "").strip() if (nn is not None and nn.text) else ""

                # FIX: also remove truth-value testing in party_or_role selection
                if fr is not None and fr.text:
                    party_or_role = fr.text.strip()
                elif rk is not None and rk.text:
                    party_or_role = rk.text.strip()
                elif rl is not None and rl.text:
                    party_or_role = rl.text.strip()
                else:
                    party_or_role = ""

        # Fallback: sometimes text like "Name (Fraktion):" is in the p itself.
        # We deliberately do NOT parse that here to avoid noisy heuristics.
        speaker_label = f"{vorname} {nachname}".strip()
        return {"speaker_id": speaker_id, "speaker": speaker_label, "party_or_role": party_or_role}

    # -------- build output ---------------------------------------------------
    out_root = ET.Element("speeches")

    # iterate each <rede> (namespace-agnostic)
    for rede in (e for e in root.iter() if localname(e.tag) == "rede"):
        rede_id = rede.get("id", "").strip() or "REDE"
        seg_idx = 0

        current_speaker = None          # dict with keys: speaker_id, speaker, party_or_role
        current_chunks = []             # list of paragraph strings
        skip_until_redner = False

        def flush_segment():
            nonlocal seg_idx, current_speaker, current_chunks
            text = " ".join(ch for ch in current_chunks if ch).strip()
            if current_speaker and text:
                seg_idx += 1
                sp_el = ET.SubElement(out_root, "speech")
                ET.SubElement(sp_el, "id").text = f"{rede_id}-{seg_idx:02d}"
                ET.SubElement(sp_el, "speaker").text = current_speaker.get("speaker", "")
                ET.SubElement(sp_el, "party_or_role").text = current_speaker.get("party_or_role", "")
                ET.SubElement(sp_el, "content").text = text
            # reset buffer
            current_chunks = []

        # Iterate top-level children in correct order
        children = list(rede)

        for idx, child in enumerate(children):
            tag = localname(child.tag)

            # If we are skipping chair content until next speaker
            if skip_until_redner:
                if tag == "p" and child.get("klasse") == "redner":
                    # Presidency ended, new real speaker starts
                    skip_until_redner = False
                    flush_segment()
                    current_speaker = extract_speaker_from_redner_p(child)
                # else: keep skipping non-redner <p> and <kommentar>
                continue

            # Detect presidency start: <name> element
            if tag == "name":
                flush_segment()
                current_speaker = None
                skip_until_redner = True
                continue

            # Skip comments always
            if tag == "kommentar":
                continue

            # Start of a new real speaker
            if tag == "p" and child.get("klasse") == "redner":
                flush_segment()
                current_speaker = extract_speaker_from_redner_p(child)
                continue

            # Collect paragraphs for the current speaker
            if tag == "p" and current_speaker is not None:
                if child.get("klasse") != "redner":
                    txt = element_full_text(child)
                    if txt:
                        current_chunks.append(txt)

            # Anything else is ignored

        # Flush trailing segment at end of <rede>
        flush_segment()

    # ensure output directory exists
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    ET.indent(out_root, space="  ")
    ET.ElementTree(out_root).write(output_file, encoding="utf-8", xml_declaration=True)

def protocol_is_complete(xml_file_path):
    import xml.etree.ElementTree as ET

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception:
        return False

    end_tag_found = False
    schluss_found = False

    for p in root.iter("p"):
        klasse = p.get("klasse", "")
        if klasse == "Ende":
            end_tag_found = True
        if klasse.startswith("T_Beratung"):
            if p.text and "(Schluss:" in p.text:
                schluss_found = True

    if end_tag_found:
        return False
    if schluss_found:
        return True
    return False

def download_meta(base, api_key, start_date="2025-10-01", end_date=None, base_dir="../data"):
    """Download metadata from the API"""
    
    # Ensure base_dir exists
    os.makedirs(base_dir, exist_ok=True)
    raw_dir = os.path.join(base_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    # set up API request
    url = f"{base}/plenarprotokoll-text"
    headers = {"Authorization": f"ApiKey {api_key}"}
    cursor = "*"

    # Initialize / load metadata in RAW folder
    metadata_file = os.path.join(raw_dir, "metadata.csv")
    if os.path.isfile(metadata_file):
        meta = pd.read_csv(metadata_file, dtype={"id": str},
                           parse_dates=["aktualisiert"], encoding="utf-8-sig")
        ids = meta["id"].tolist()
    else:
        meta = pd.DataFrame()
        ids = []

    # storage for new metadata entries
    new_meta = []
    # new_versions = []

    # Fetch documents
    while True:
        params = {"cursor": cursor, "rows": 100,
                  "f.datum.start": start_date, "f.datum.end": end_date}
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        docs = data.get("documents")

        if not docs:
            break

        for doc in docs:
            if doc.get("herausgeber") == "BR":
                continue
            # aktualisiert = pd.to_datetime(doc.get("aktualisiert"),
                                        #   utc=True, errors="coerce").tz_convert(None)
            doc_id = str(doc.get("id"))
            # for now, ignore updates
            if doc_id in ids:
                continue
                # if aktualisiert <= meta.loc[meta["id"] == doc_id, "aktualisiert"].values[0]:
                #     continue
                # else:
                #     new_versions.append(doc)
            new_meta.append(doc)

        new_cursor = data.get("cursor")
        if not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor

    # Save metadata
    if new_meta:
        new_meta_df = pd.json_normalize(new_meta)
        new_meta_df = new_meta_df.drop(columns=["text"], errors='ignore')
        new_meta_df["id"] = new_meta_df["id"].astype(str)
        new_meta_df["aktualisiert"] = pd.to_datetime(new_meta_df["aktualisiert"],
                                                     utc=True, errors="coerce")
        meta_df = pd.concat([meta, new_meta_df], ignore_index=True)
        meta_df.to_csv(metadata_file, index=False, encoding="utf-8-sig")
        print(f"Saved metadata to {metadata_file}")

def perc_complete(metadata_file):
    # Load metadata
    df = pd.read_csv(metadata_file, dtype=str)

    # Convert is_complete column to boolean
    df["is_complete_bool"] = df["is_complete"].map(
        lambda x: True if x == "True" else False
    )

    total = len(df)
    incomplete = (~df["is_complete_bool"]).sum()

    percentage_incomplete = (incomplete / total) * 100 if total > 0 else 0

    print(f"Total protocols: {total}")
    print(f"Incomplete protocols: {incomplete}")
    print(f"Percentage incomplete: {percentage_incomplete:.2f}%")

def main(base, api_key, start_date="2025-10-01", end_date=None, base_dir="../data"):

    # paths
    raw_dir = os.path.join(base_dir, "raw")
    cut_dir = os.path.join(base_dir, "cut")
    metadata_file = os.path.join(raw_dir, "metadata.csv")

    # download new metadata
    try:
        print("-" * 60)
        print("Downloading new metadata...")
        download_meta(base=base,
                      api_key=api_key,
                      start_date=start_date,
                      end_date=end_date,
                      base_dir=base_dir
                      )
    except Exception as e:
        print("An error occurred when running download_meta", str(e))

    # download new xml files
    try:
        print("-" * 60)
        print("Downloading new XML files...")
        download_xml_from_metadata(metadata_file, raw_dir)
    except Exception as e:
        print("An error occurred when running download_xml_from_metadata", str(e))

    # cut new xml files & check their completeness
    try:
        print("-" * 60)
        print("Cutting XML files...")
        # read metafile
        meta = pd.read_csv(metadata_file, dtype=str)

        # Ensure we have a proper date column and format to DD-MM-YYYY
        if "datum" in meta.columns:
            meta["date_formatted"] = pd.to_datetime(
                meta["datum"], errors="coerce"
            ).dt.strftime("%d-%m-%Y")
        elif "datum.desplenarprotokolls" in meta.columns:
            meta["date_formatted"] = pd.to_datetime(
                meta["datum.desplenarprotokolls"], errors="coerce"
            ).dt.strftime("%d-%m-%Y")
        else:
            raise KeyError("No date column found in metadata to name files by date.")
        
        # cutting xml files
        cut_made = 0
        for _, row in meta.iterrows():
            date_str = row.get("date_formatted")
            if pd.isna(date_str) or not date_str:
                print("[WARNING] No valid date for row:", row)
                continue  # skip rows without valid date

            # Input from RAW folder uses document number or ID as fallback
            docnum = (row.get("dokumentnummer") or row.get("id") or "").replace("/", "_")
            input_xml_file = os.path.join(raw_dir, f"{docnum}.xml")

            # Output filename by date: DD-MM-YYYY_cut.xml
            output_cut_file = os.path.join(cut_dir, f"{date_str}_cut.xml")

            # if input does not exist, warn and skip
            if not os.path.isfile(input_xml_file):
                print(f"[WARNING] XML not found: {input_xml_file}")
                continue

            # it output file aready exists, skip
            if os.path.isfile(output_cut_file):
                continue
            
            # update completeness info
            meta.loc[row.name, "is_complete"] = protocol_is_complete(input_xml_file)
            
            # create cut xml
            print(f"Creating cut XML for {input_xml_file} -> {output_cut_file}")
            create_cut_xml(input_xml_file, output_cut_file)
            cut_made += 1

        # save updated metadata with is_complete column
        meta.to_csv(metadata_file, index=False, encoding="utf-8-sig")
        print(f"Cut {cut_made} new XML files")

    except Exception as e:
        print("An error occurred in cutting process", str(e))

    # print completeness stats
    try:
        print("-" * 60)
        print("Calculating completeness statistics...")
        perc_complete(metadata_file)
    except Exception as e:
        print("An error occurred when running perc_complete", str(e))

