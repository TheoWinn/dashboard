import re
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import xml.etree.ElementTree as ET
import sys

SIM_THRESHOLD = 0.6

def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^a-zäöüß\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_date_from_filename(filename):
    """Extracts date pattern DD-MM-YYYY or DD-MM-YY from filename."""
    match = re.search(r"(\d{2}-\d{2}-\d{2,4})", filename)
    return match.group(1) if match else None

def matching_pipeline():
    # === PATH FIX: Resolve paths relative to this script file ===
    # Script location: .../matching/src/ma_utils.py
    # Root location:   .../ (project root)
    script_dir = Path(__file__).resolve().parent
    
    # Target: .../youtube/data/clustered/bundestag_clustered
    csv_dir = script_dir.parent.parent / "youtube" / "data" / "clustered" / "bundestag_clustered"
    
    # Target: .../bundestag/data/cut
    xml_dir = script_dir.parent.parent / "bundestag" / "data" / "cut"
    
    # Target: .../matching/data/matched
    out_dir = script_dir.parent / "data" / "matched"
    
    print(f"DEBUG: Script location: {script_dir}")
    print(f"DEBUG: CSV Directory:   {csv_dir}")
    print(f"DEBUG: XML Directory:   {xml_dir}")
    
    if not csv_dir.exists():
        print(f"ERROR: CSV directory not found at {csv_dir}")
        return
    if not xml_dir.exists():
        print(f"ERROR: XML directory not found at {xml_dir}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    meta_path = out_dir / "meta_file_matching.csv"
    global_meta_rows = []  # reset every run (no global state)

    # === Step 1: Cluster files by date ===
    csv_by_date = {}
    # glob patterns are case sensitive on Linux/Cluster
    for csv_path in csv_dir.glob("*.csv"):
        date_str = extract_date_from_filename(csv_path.name)
        if date_str:
            csv_by_date.setdefault(date_str, []).append(csv_path)

    xml_by_date = {}
    for xml_path in xml_dir.glob("*.xml"):
        date_str = extract_date_from_filename(xml_path.name)
        if date_str:
            xml_by_date.setdefault(date_str, []).append(xml_path)

    common_dates = sorted(set(csv_by_date.keys()) & set(xml_by_date.keys()))
    
    if not common_dates:
        print("\nERROR: No overlapping dates found.")
        print(f" - Dates in CSVs ({len(csv_by_date)}): {list(csv_by_date.keys())[:5]}...")
        print(f" - Dates in XMLs ({len(xml_by_date)}): {list(xml_by_date.keys())[:5]}...")
        raise RuntimeError("No overlapping dates between CSVs and XMLs found.")

    print(f"Found {len(common_dates)} common dates: {common_dates}")

    print("CSV-only dates:", sorted(set(csv_by_date.keys()) - set(xml_by_date.keys())))
    print("XML-only dates:", sorted(set(xml_by_date.keys()) - set(csv_by_date.keys())))

    # read in meta data
    meta_path = out_dir / "meta_file_matching.csv"
    already_matched_csv = []
    global_meta_rows = []
    if meta_path.exists():
        old_meta = pd.read_csv(meta_path, dtype=str)

        # Safety: if old meta contains repeated header lines as rows, drop them
        for col in ["flag", "xml_data", "video_data"]:
            if col in old_meta.columns:
                old_meta = old_meta[old_meta[col].astype(str).ne(col)]

        # Keep only the expected columns
        if {"flag", "xml_data", "video_data"}.issubset(old_meta.columns):
            old_meta = old_meta[["flag", "xml_data", "video_data"]].copy()
            global_meta_rows = old_meta.to_dict("records")

            already_matched_csv = old_meta[old_meta["flag"] == "matched"]["video_data"].tolist()
        else:
            # If file exists but is malformed, start fresh
            global_meta_rows = []
            already_matched_csv = []

    # # read in meta data from downloading protocols
    # download_meta_path = xml_dir / "../raw/metadata.csv"
    # incomplete_xml_dates = []
    # if download_meta_path.exists():
    #     download_meta = pd.read_csv(download_meta_path)
    #     incomplete_xml_dates = download_meta[download_meta["is_complete"] == False]["date_formatted"].tolist()

    # === Step 2: Process each date ===
    for date_str in common_dates:
        print(f"\n=== Processing {date_str} ===")
        csv_files = csv_by_date[date_str]
        xml_files = xml_by_date[date_str]

        # ---- check meta: skip videos already marked as matched ----
        already_done = set()
        if meta_path.exists():
            old_meta = pd.read_csv(meta_path)

            # Safety: if old meta contains repeated header lines as rows, drop them
            for col in ["flag", "xml_data", "video_data"]:
                if col in old_meta.columns:
                    old_meta = old_meta[old_meta[col].astype(str).ne(col)]

            if {"flag", "xml_data", "video_data"}.issubset(old_meta.columns):
                matched_pairs = (
                    old_meta[old_meta["flag"] == "matched"][["xml_data", "video_data"]]
                    .drop_duplicates()
                )
                already_done = set(tuple(x) for x in matched_pairs.values)

        # Filter out CSV files that are already matched
        filtered_csv_files = []
        for csv_file in csv_files:
            video_data = csv_file.stem  # EXACT string written to meta
            if (date_str, video_data) in already_done:
                print(f"  Skipping {video_data}: already matched in meta file.")
            else:
                filtered_csv_files.append(csv_file)

        if len(filtered_csv_files) == 0:
            print(f"Skipping {date_str}: all videos already matched.")
            continue

        csv_files = filtered_csv_files

        # Combine all CSVs of that date
        df_csv = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)
        df_csv = df_csv[df_csv["text"].astype(str).str.strip().ne("")].reset_index(drop=True)
        print(f"  Loaded {len(df_csv)} transcript segments")
        total_speeches_in_csv = len(df_csv)

        # Load all XML speeches for that date
        protokoll_name, protokoll_party, protokoll_text, protokoll_docid = [], [], [], []
        total_speeches_in_xml = 0
        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
            except ET.ParseError:
                print(f"  Warning: failed to parse {xml_file}, skipping")
                continue

            total_speeches_in_xml += len(root.findall(".//speech"))

            for sp in root.findall(".//speech"):
                speaker = (sp.findtext("speaker") or sp.findtext("name") or "").strip()
                party = (sp.findtext("party_or_role") or sp.findtext("party") or "").strip()
                content = (sp.findtext("content") or sp.findtext("text") or "").strip()
                if not content:
                    continue
                protokoll_name.append(speaker)
                protokoll_party.append(party)
                protokoll_text.append(content)
                protokoll_docid.append(xml_file.stem)

        if not protokoll_text:
            print(f"  No speeches found for {date_str}, skipping.")
            continue

        # === Step 3: TF-IDF Matching ===
        xml_texts_proc = [preprocess_text(t) for t in protokoll_text]
        tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        xml_matrix = tfidf.fit_transform(xml_texts_proc)

        results = []
        for _, r in df_csv.iterrows():
            seg_text = str(r["text"])
            seg_text_proc = preprocess_text(seg_text)
            if not seg_text_proc:
                continue

            try:
                seg_vec = tfidf.transform([seg_text_proc])
            except Exception:
                continue

            sims = cosine_similarity(seg_vec, xml_matrix)[0]
            best_idx = int(sims.argmax())
            best_sim = float(sims[best_idx])

            if best_sim < SIM_THRESHOLD:
                continue

            results.append(
                {
                    "protokoll_docid": protokoll_docid[best_idx],
                    "protokoll_name": protokoll_name[best_idx],
                    "protokoll_party": protokoll_party[best_idx],
                    "similarity": best_sim,
                    "transcript_start": r.get("start", ""),
                    "transcript_end": r.get("end", ""),
                    "transcript_text": seg_text,
                    "transcript_speaker": r.get("speaker", ""),
                    "protokoll_text": protokoll_text[best_idx],
                }
            )

        # === Step 4: Save per date ===
        if results:
            out_path = out_dir / f"{date_str}_matched.csv"
            out_df = pd.DataFrame(results)
            out_df = out_df[out_df["similarity"] >= SIM_THRESHOLD]
            out_df.to_csv(out_path, index=False)
            print(f"  Saved {len(out_df)} matches to {out_path}")
        else:
            print(f"  No matches above threshold for {date_str}")

        # === Step 5: Meta flags for each CSV video on common date ===
        # matched: at least one segment matched
        # no_matches_found: xml+csv exist, but nothing matched above threshold
        # hanging_video: csv exists for a date that has no xml at all (handled below)
        for csv_file in csv_files:
            video_data = csv_file.stem

            df_csv_video = pd.read_csv(csv_file)
            df_csv_video = df_csv_video[df_csv_video["text"].astype(str).str.strip().ne("")]
            video_texts = set(df_csv_video["text"].astype(str))

            matched_segments = [r for r in results if r.get("transcript_text") in video_texts]

            global_meta_rows.append(
                {
                    "flag": "matched" if len(matched_segments) > 0 else "no_matches_found",
                    "xml_data": date_str,
                    "video_data": video_data,
                }
            )

    # --- handle video-only dates (csv but no xml) ---
    video_only_dates = sorted(set(csv_by_date.keys()) - set(xml_by_date.keys()))
    for v_date in video_only_dates:
        for csv_file in csv_by_date[v_date]:
            global_meta_rows.append(
                {"flag": "hanging_video", "xml_data": "", "video_data": csv_file.stem}
            )

    # --- handle xml-only dates (xml but no csv) ---
    xml_only_dates = sorted(set(xml_by_date.keys()) - set(csv_by_date.keys()))
    for x_date in xml_only_dates:
        global_meta_rows.append({"flag": "hanging_xml", "xml_data": x_date, "video_data": ""})

    # === Write meta file once ===
    meta_df = pd.DataFrame(global_meta_rows)
    meta_df = meta_df[["flag", "xml_data", "video_data"]].drop_duplicates()

    flag_order = {"hanging_xml": 0, "hanging_video": 1, "no_matches_found": 2, "matched": 3}
    meta_df["flag_rank"] = meta_df["flag"].map(flag_order).fillna(99)

    meta_df["video_date"] = meta_df["video_data"].str.extract(r"(\d{2}-\d{2}-\d{2,4})")
    meta_df["video_date"] = pd.to_datetime(meta_df["video_date"], format="%d-%m-%Y", errors="coerce")

    meta_df = meta_df.sort_values(by=["flag_rank", "video_date"], ascending=[True, True])
    meta_df = meta_df.drop(columns=["flag_rank", "video_date"])

    meta_df.to_csv(meta_path, index=False)
    print(f"Saved sorted meta information to {meta_path}")

if __name__ == "__main__":
    matching_pipeline()