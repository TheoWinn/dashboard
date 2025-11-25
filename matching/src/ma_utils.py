import re
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import xml.etree.ElementTree as ET

"""
ToDo:

get the input path right (is still downloaded manually)
reinschreiben, dass nicht gematched wird, wenn das matching schonmal gemacht wurde


Problem: 
26.09. was ist das thema zu dem kathrin michel spd redet? (protokoll_raw) 
das transcript stimmt nicht, aber die zeiten unabhängig davon schon oder? kontrollieren 

Warum fehlt ein Vid Match vom 26.09?



--------------------------------------
"""
import os
import re
import pandas as pd
from pathlib import Path
import xml.etree.ElementTree as ET
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SIM_THRESHOLD = 0.6
global_meta_rows = []


def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-zäöüß\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_date_from_filename(filename):
    """Extracts date pattern DD-MM-YYYY or DD-MM-YY from filename."""
    match = re.search(r"(\d{2}-\d{2}-\d{2,4})", filename)
    return match.group(1) if match else None


def matching_pipeline():
    csv_dir = Path("data(old)/out") # Change this 
    xml_dir = Path("bundestag/data/cut")
    out_dir = Path("matching/data/matched")
    out_dir.mkdir(parents=True, exist_ok=True)

    # === Step 1: Cluster files by date ===
    csv_by_date = {}
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
        raise RuntimeError("No overlapping dates between CSVs and XMLs found.")

    print(f"Found {len(common_dates)} common dates: {common_dates}")

    # === Step 2: Process each date ===
    for date_str in common_dates:
        print(f"\n=== Processing {date_str} ===")
        csv_files = csv_by_date[date_str]
        xml_files = xml_by_date[date_str]

     # check Metadata and skip if already matched
        meta_path = out_dir / "meta_file_matching.csv"
        already_done = set()

        if meta_path.exists():
            old_meta = pd.read_csv(meta_path)
            # Only consider rows where matching was successful
            matched_pairs = (
                old_meta[old_meta["flag"] == "matched"]
                [["xml_data", "video_data"]]
                .drop_duplicates()
            )
            already_done = set(tuple(x) for x in matched_pairs.values)

        # Filter out CSV files that are already matched
        filtered_csv_files = []
        for csv_file in csv_files:
            video_title = csv_file.name.replace(".csv", "")
            if (date_str, video_title) in already_done:
                print(f"  Skipping {video_title}: already matched in meta file.")
            else:
                filtered_csv_files.append(csv_file)

        # If nothing remains → skip whole date
        if len(filtered_csv_files) == 0:
            print(f"Skipping {date_str}: all videos already matched.")
            continue

        # Use the filtered list for the rest of the pipeline
        csv_files = filtered_csv_files

        # Combine all CSVs of that date
        df_csv = pd.concat([pd.read_csv(f) for f in csv_files])
        df_csv = df_csv[df_csv["text"].astype(str).str.strip().ne("")].reset_index(drop=True)
        print(f"  Loaded {len(df_csv)} transcript segments")

        # Load all XML speeches for that date. That is the matching loop
        protokoll_name, protokoll_party, protokoll_text, protokoll_docid = [], [], [], []
        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
            except ET.ParseError:
                print(f"  Warning: failed to parse {xml_file}, skipping")
                continue

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

            results.append({
                "protokoll_docid": protokoll_docid[best_idx],
                "protokoll_name": protokoll_name[best_idx],
                "protokoll_party": protokoll_party[best_idx],
                "similarity": best_sim,
                "transcript_start": r.get("start", ""),
                "transcript_end": r.get("end", ""),
                "transcript_text": seg_text,
                "transcript_speaker": r.get("speaker", ""),
                "protokoll_text": protokoll_text[best_idx]
            })

        # === Step 4: Save per date ===
        if results:
            out_path = out_dir / f"{date_str}_matched.csv"
            out_df = pd.DataFrame(results)
            out_df = out_df[out_df["similarity"] >= SIM_THRESHOLD]
            out_df.to_csv(out_path, index=False)
            print(f"  Saved {len(out_df)} matches to {out_path}")
       

        # === Step 5: Meta file creation and flagging missing matches ===
        # Works as follows: 
        # If for a common date, we dont have both the XML or the whisper transcripts:
        # the script flags the whole match as missing

        for csv_file in csv_files:
            video_title = csv_file.name.replace(".csv", "")

            df_csv_video = pd.read_csv(csv_file)
            df_csv_video = df_csv_video[df_csv_video["text"].astype(str).str.strip().ne("")]

            matched_segments = [
                r for r in results
                if r.get("transcript_text", None) in set(df_csv_video["text"].astype(str))
            ]

            # --- CORRECTED: only ONE meta entry per video file ---
            if len(matched_segments) > 0:
                # at least one match in this video → file is matched
                global_meta_rows.append({
                    "xml_data": date_str,
                    "video_data": video_title,
                    "flag": "matched"
                })
            else:
                # video file exists but none of its segments matched → hanging video
                global_meta_rows.append({
                    "xml_data": date_str,
                    "video_data": video_title,
                    "flag": "hanging_video"
                })

        # --- HANDLE video-only dates (csv but no xml) ---
        if date_str == common_dates[-1]:  
            video_only_dates = sorted(set(csv_by_date.keys()) - set(xml_by_date.keys()))
            for v_date in video_only_dates:
                for csv_file in csv_by_date[v_date]:
                    video_title = csv_file.name.replace(".csv", "")
                    global_meta_rows.append({
                        "xml_data": "",
                        "video_data": video_title,
                        "flag": "hanging_video"
                    })

        # --- HANDLE xml-only dates (xml but no csv) ---
        if date_str == common_dates[-1]:
            xml_only_dates = sorted(set(xml_by_date.keys()) - set(csv_by_date.keys()))
            for x_date in xml_only_dates:
                for xml_file in xml_by_date[x_date]:
                    global_meta_rows.append({
                        "flag": "hanging_xml",
                        "xml_data": x_date,
                        "video_data": ""
                        
                    })


        # Write or append meta file for the current date. Sort it so that the hanging* flags are on top 
        meta_path = out_dir / "meta_file_matching.csv"
        meta_df = pd.DataFrame(global_meta_rows, columns=["flag","xml_data", "video_data"])

        
        flag_order = {
            "hanging_xml": 0,
            "hanging_video": 1,
            "matched": 2
        }
        meta_df["flag_rank"] = meta_df["flag"].map(flag_order)

        # --- EXTRACT VIDEO DATE (if present) ---
        meta_df["video_date"] = meta_df["video_data"].str.extract(r"(\d{2}-\d{2}-\d{2,4})")
        meta_df["video_date"] = pd.to_datetime(meta_df["video_date"], format="%d-%m-%Y", errors="coerce")

        # --- SORT BY: (1) flag category, (2) video date ---
        meta_df = meta_df.sort_values(by=["flag_rank", "video_date"], ascending=[True, True])

        # --- CLEAN UP ---
        meta_df = meta_df.drop(columns=["flag_rank", "video_date"])

        # SAVE SORTED FILE
        meta_df.to_csv(meta_path, index=False)
        print(f"Saved sorted global meta information to {meta_path}")

if __name__ == "__main__":
    matching_pipeline()






########### ARCHIVE - matching.py ###########

# import re
# import json
# import pandas as pd
# from pathlib import Path
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# from difflib import SequenceMatcher

# """
# ToDo:
# Cleaning: Some matches based on generic phrases (e.g. "thank you vice minister") -> didnt found solution for cleaning yet. have high similarity but are not informative. Do they just fly out when we do topic modelling? 
# Scale up to run on the whole speech and 4 vids
# Update the fucking git bro 
# --------------------------------------
# DONE sind die endpoints korrekt?
# DONE leonies aktuelle version einbauen
# DONE Party mit rein 
# DONE sind alle MPs da? 
# DONE nochmal für eine rede die minimalste similarity anschauen (manuell), 
# DONE wie viele matches haben wir unter 90/80/70%? Was sind die geringsten, ist das match trd correct? Liegt das an dem transcribieren oder sind das einfach die Vizes, wie viele fälle sind das?
# """


# def preprocess_text(text):
#     """
#     Cleans and standardizes text for comparison.
    
#     - Converts text to lowercase.
#     - Removes punctuation and numbers.
#     - Strips extra whitespace.
#     """
#     if not isinstance(text, str):

#         return ""
#     text = text.lower()
#     # Removes anything that is not a letter or whitespace
#     text = re.sub(r'[^a-zäöüß\s]', '', text)
#     # Replaces multiple whitespace characters with a single space
#     text = re.sub(r'\s+', ' ', text).strip()
#     return text

# def find_best_speech_match(transcript, speeches, top_n=3):
#     """
#     Purpose: given one Whisper segment (transcript) and a list of full 
#     JSON speeches (speeches), pick the most similar JSON speech.

#     Args:
#         transcript (str): The transcribed text from a video.
#         speeches (list[str]): A list of the official speech texts, when we have mulitple speeches later. 
#         top_n (int): The number of top candidates to check with the detailed comparison.
#                        A smaller number is faster.

#     Returns:
#         tuple: A tuple containing the best matching speech text and its
#                similarity score (from 0.0 to 1.0). Returns (None, 0.0) if no match is found.
#     """
#     if not transcript or not speeches:
#         return None, 0.0, None

#     # === Step 1: Preprocessing ===
#     # Clean the input transcript and all official speeches.
#     processed_transcript = preprocess_text(transcript)
#     processed_speeches = [preprocess_text(s) for s in speeches]
#     # Builds corpus (Json speeches first and then one whisper transcript)
#     all_texts = processed_speeches + [processed_transcript]

#     # === Step 2: Indexing and Candidate Search (TF-IDF) ===
#     # Create TF-IDF vector representations (the "fingerprints") for all texts.
#     # We use German stop words to improve relevance.
#     try:
#         tfidf_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), sublinear_tf=True)
#         tfidf_matrix = tfidf_vectorizer.fit_transform(all_texts)
#     except ValueError:
#         return None, 0.0, None
#     # Separate corpus: [:-1] JSON speeches, [-1] WHisper transcript
#     speeches_matrix = tfidf_matrix[:-1]
#     transcript_vector = tfidf_matrix[-1]
#     # Cosine similarity gives one similarty score per speech
#     similarities = cosine_similarity(transcript_vector, speeches_matrix)[0]
#     # Indices of top-N most similar speeches
#     candidate_indices = similarities.argsort()[::-1][:top_n]

#     # === Step 3: Detailed Comparison for those top-N most similar speeches ===
#     # Meaning we break ties, if there are ones.
#     best_match = None
#     best_score = 0.0
#     best_idx = None

#     for index in candidate_indices:
#         candidate_speech = speeches[index]
#         score = SequenceMatcher(None, transcript, candidate_speech).ratio()
#         if score > best_score:
#             best_score = score
#             best_match = candidate_speech
#             best_idx = index
            
#     cosine_score = float(similarities[best_idx]) if best_idx is not None else 0.0
#     return best_match, cosine_score, best_idx


    
# # Matching pipeline: for each Whisper segment, find the best matching Bundestag speech
# def refined_matching():
#     # ---- Paths ----
#     csv_path = Path("data/transcript_aligned_clustered.csv")
#     json_path = Path("data/plenarprotokoll-speeches-foralgo.json")
#     out_path = Path("data/matched_transcripts.csv")

#     # ---- Load CSV ----
#     df_csv = pd.read_csv(csv_path)
#     df_csv = df_csv[df_csv["text"].astype(str).str.strip().ne("")].reset_index(drop=True)

#     # ---- Load JSON ----
#     with open(json_path, "r", encoding="utf-8") as f:
#         speeches_data = json.load(f)

#     if isinstance(speeches_data, dict):
#         speeches_list = speeches_data.get("speeches", [speeches_data])
#     elif isinstance(speeches_data, list):
#         speeches_list = speeches_data
#     else:
#         raise ValueError("Unexpected JSON structure.")
#     # Extract JSON fields
#     protokoll_name, protokoll_party, protokoll_text = [], [], []
#     for item in speeches_list:
#         if not isinstance(item, dict):
#             continue
#         protokoll_name.append((item.get("speaker") or item.get("name") or "").strip())
#         protokoll_party.append((item.get("party") or "").strip())
#         protokoll_text.append((item.get("text") or "").strip())


#     # ---- Matching ----
#     # Build a TF-IDF model on the full JSON speeches 
#     # 1. Preprocess JSON texts
#     json_texts_proc = [preprocess_text(t) for t in protokoll_text]
#     # 2. Fit TF-IDF 
#     tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), sublinear_tf=True)
#     # 3. Compute cosine similarity matrix
#     json_matrix = tfidf.fit_transform(json_texts_proc)
#     # 4. Output
#     results = []
#     for _, r in df_csv.iterrows():
#         seg_text = str(r["text"])
#         seg_text_proc = preprocess_text(seg_text)

#         # vectorize this single whisper snippet
#         seg_vec = tfidf.transform([seg_text_proc])
#         sims = cosine_similarity(seg_vec, json_matrix)[0]

#         best_idx = int(sims.argmax())
#         best_sim = float(sims[best_idx])

#         results.append({
#             "protokoll_name": protokoll_name[best_idx],
#             "protokoll_party": protokoll_party[best_idx],
#             "similarity": best_sim,
#             "transcript_start": r.get("start", ""),
#             "transcript_end": r.get("end", ""),
#             "protokoll_text": protokoll_text[best_idx],
#             "transcript_speaker": r.get("speaker", ""),
#             "transcript_text": seg_text
#             })

#     # ---- Save ----
#     out_df = pd.DataFrame(results)
#     out_df.to_csv(out_path, index=False)
#     print(f"Done! Saved {len(out_df)} rows to '{out_path}'")


# if __name__ == "__main__":
#     main()  




#################################################

#helper function to split long json texts into chunks (for very long speeches)
# def chunk_text(text: str, size: int = 800, overlap: int = 200):
#     text = (text or "").strip()
#     if not text:
#         return [""]
#     chunks, step, i = [], max(size - overlap, 1), 0
#     while i < len(text):
#         chunks.append(text[i:i+size])
#         i += step
#     return chunks


# # helper function for csv  matching (problem: one speech in csv goes over many rows while json is one text)
# def make_blocks(df, gap_seconds: float = 5.0, respect_speaker: bool = False, max_speaker_flips: int = 1):
#     """
#     Merge consecutive rows into blocks.
#     - If respect_speaker=False (default): only the time gap matters.
#     - If respect_speaker=True: allow up to `max_speaker_flips` label changes inside a block;
#       otherwise start a new block.
#     """
#     req = {"speaker", "start", "end", "text"}
#     if not req.issubset(df.columns):
#         raise ValueError(f"CSV must have columns: {sorted(req)}")

#     df = df.sort_values(["start", "end"]).reset_index(drop=True).copy()
#     block_id = 0
#     block_ids = [block_id]
#     flips_in_block = 0
#     last_speaker = df.at[0, "speaker"]

#     for i in range(1, len(df)):
#         gap = float(df.at[i, "start"]) - float(df.at[i-1, "end"])
#         same_spk = df.at[i, "speaker"] == df.at[i-1, "speaker"]

#         new_block = gap > gap_seconds
#         if respect_speaker:
#             if not same_spk:
#                 flips_in_block += 1
#                 if flips_in_block > max_speaker_flips:
#                     new_block = True
#             else:
#                 # reset flips counter when label stabilizes
#                 flips_in_block = 0

#         if new_block:
#             block_id += 1
#             flips_in_block = 0
#         block_ids.append(block_id)

#     df["block_id"] = block_ids
#     return df

# import re
# import json
# import pandas as pd
# from pathlib import Path
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# from difflib import SequenceMatcher



# def preprocess_text(text):
#     """
#     Cleans and standardizes text for comparison.
    
#     - Converts text to lowercase.
#     - Removes punctuation and numbers.
#     - Strips extra whitespace.
#     """
#     if not isinstance(text, str):
#         return ""
#     text = text.lower()
#     # Removes anything that is not a letter or whitespace
#     text = re.sub(r'[^a-zäöüß\s]', '', text)
#     # Replaces multiple whitespace characters with a single space
#     text = re.sub(r'\s+', ' ', text).strip()
#     return text

# # helper function to split long json texts into chunks (for very long speeches)
# def chunk_text(text: str, size: int = 800, overlap: int = 200):
#     text = (text or "").strip()
#     if not text:
#         return [""]
#     chunks, step, i = [], max(size - overlap, 1), 0
#     while i < len(text):
#         chunks.append(text[i:i+size])
#         i += step
#     return chunks


# # helper function for csv  matching (problem: one speech in csv goes over many rows while json is one text)
# def make_blocks(df, gap_seconds: float = 5.0, respect_speaker: bool = False, max_speaker_flips: int = 1):
#     """
#     Merge consecutive rows into blocks.
#     - If respect_speaker=False (default): only the time gap matters.
#     - If respect_speaker=True: allow up to `max_speaker_flips` label changes inside a block;
#       otherwise start a new block.
#     """
#     req = {"speaker", "start", "end", "text"}
#     if not req.issubset(df.columns):
#         raise ValueError(f"CSV must have columns: {sorted(req)}")

#     df = df.sort_values(["start", "end"]).reset_index(drop=True).copy()
#     block_id = 0
#     block_ids = [block_id]
#     flips_in_block = 0
#     last_speaker = df.at[0, "speaker"]

#     for i in range(1, len(df)):
#         gap = float(df.at[i, "start"]) - float(df.at[i-1, "end"])
#         same_spk = df.at[i, "speaker"] == df.at[i-1, "speaker"]

#         new_block = gap > gap_seconds
#         if respect_speaker:
#             if not same_spk:
#                 flips_in_block += 1
#                 if flips_in_block > max_speaker_flips:
#                     new_block = True
#             else:
#                 # reset flips counter when label stabilizes
#                 flips_in_block = 0

#         if new_block:
#             block_id += 1
#             flips_in_block = 0
#         block_ids.append(block_id)

#     df["block_id"] = block_ids
#     return df


# def find_best_speech_match(transcript, speeches, top_n=3):
#     """
#     Finds the best speech match for a given transcript using a two-step process.

#     Args:
#         transcript (str): The transcribed text from a video.
#         speeches (list[str]): A list of the official speech texts.
#         top_n (int): The number of top candidates to check with the detailed comparison.
#                        A smaller number is faster.

#     Returns:
#         tuple: A tuple containing the best matching speech text and its
#                similarity score (from 0.0 to 1.0). Returns (None, 0.0) if no match is found.
#     """
#     if not transcript or not speeches:
#         return None, 0.0, None

#     # === Step 1: Preprocessing ===
#     # Clean the input transcript and all official speeches.
#     processed_transcript = preprocess_text(transcript)
#     processed_speeches = [preprocess_text(s) for s in speeches]
        
#     # Add the transcript to the list for vectorization
#     all_texts = processed_speeches + [processed_transcript]

#     # === Step 2: Indexing and Candidate Search (TF-IDF) ===
#     # Create TF-IDF vector representations (the "fingerprints") for all texts.
#     # We use German stop words to improve relevance.
#     try:
#         tfidf_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), sublinear_tf=True)
#         tfidf_matrix = tfidf_vectorizer.fit_transform(all_texts)
#     except ValueError:
#         return None, 0.0, None

#     # Separate the speeches' matrix from the transcript's vector
#     speeches_matrix = tfidf_matrix[:-1]
#     transcript_vector = tfidf_matrix[-1]

#     # Cosine similarity as a 1-D array
#     similarities = cosine_similarity(transcript_vector, speeches_matrix)[0]

#     # Indices of top-N most similar speeches
#     candidate_indices = similarities.argsort()[::-1][:top_n]
    

#     # === Step 3: Detailed Comparison (SequenceMatcher) ===
#     # Now, we only compare the transcript against the best few candidates.
#     best_match = None
#     best_score = 0.0
#     best_idx = None

#     for index in candidate_indices:
#         candidate_speech = speeches[index]
#         score = SequenceMatcher(None, transcript, candidate_speech).ratio()
#         if score > best_score:
#             best_score = score
#             best_match = candidate_speech
#             best_idx = index
            
#     cosine_score = float(similarities[best_idx]) if best_idx is not None else 0.0
#     return best_match, cosine_score, best_idx


    
# #4. Matching process: for each Whisper segment, find the best matching Bundestag speech
# def main():
#     # ---- Paths ----
#     csv_path = Path("data/transcript_aligned_clustered.csv")
#     json_path = Path("data/plenarprotokoll-speeches.json")
#     out_path = Path("data/matched_transcripts.csv")

#     # ---- Load CSV ----
#     df_csv = pd.read_csv(csv_path)
#     df_csv = df_csv[df_csv["text"].astype(str).str.strip().ne("")].reset_index(drop=True)

#     # ---- Load JSON ----
#     with open(json_path, "r", encoding="utf-8") as f:
#         speeches_data = json.load(f)

#     if isinstance(speeches_data, dict):
#         speeches_list = speeches_data.get("speeches", [speeches_data])
#     elif isinstance(speeches_data, list):
#         speeches_list = speeches_data
#     else:
#         raise ValueError("Unexpected JSON structure.")

#     # Extract name and text
#     json_names, json_texts = [], []
#     for item in speeches_list:
#         if not isinstance(item, dict):
#             continue
#         name = (item.get("speaker") or item.get("name") or "").strip()
#         text = (item.get("text") or "").strip()
#         for ch in chunk_text(text, size=800, overlap=200):
#             json_names.append(name)
#             json_texts.append(ch)

#     # ---- Matching ----
#     df_csv = make_blocks(df_csv, gap_seconds=5.0, respect_speaker=False)

#     # Aggregate one row per block (concat text, min start, max end)
#     agg = (df_csv
#         .groupby("block_id", as_index=False)
#         .agg({
#             "speaker": "first",
#             "start": "min",
#             "end": "max",
#             "text": lambda x: " ".join(map(str, x))
#         })
#         )
#     agg.rename(columns={
#         "speaker": "block_speaker",
#         "start": "block_start",
#         "end": "block_end",
#         "text": "block_text"
#     }, inplace=True)

#     # ---- Match once per block ----
#     block_matches = []
#     for _, br in agg.iterrows():
#         best_speech, sim, idx = find_best_speech_match(br["block_text"], json_texts)
#         block_matches.append({
#             "block_id": br["block_id"],
#             "json_idx": idx,
#             "name_json": json_names[idx] if idx is not None else "",
#             "text_json": best_speech if best_speech else "",
#             "similarity": sim
#         })
#     df_block_matches = pd.DataFrame(block_matches)

#     # ---- Attach block match back to each original CSV row ----
#     df_final = df_csv.merge(df_block_matches, on="block_id", how="left")

#     # ---- Build output in your requested per-row format ----
#     df_out = pd.DataFrame({
#         "name (from json)": df_final["name_json"].fillna(""),
#         "text (from json)": df_final["text_json"].fillna(""),
#         "speaker (from csv)": df_final["speaker"],
#         "start (from csv)": df_final["start"],
#         "end (from csv)": df_final["end"],
#         "text (from csv)": df_final["text"],
#         "similarity score": df_final["similarity"].fillna(0.0)
#     })

#     # save a compact per-block summary for QA
#     df_blocks_out = (agg
#         .merge(df_block_matches, on="block_id", how="left")
#         .rename(columns={
#             "block_speaker": "speaker (csv, block)",
#             "block_start": "start (csv, block)",
#             "block_end": "end (csv, block)",
#             "block_text": "text (csv, block)",
#             "name_json": "name (json)",
#             "text_json": "text (json)",
#             "similarity": "similarity (block)"
#         })
#     )

#     # ---- Save ----
#     df_out.to_csv(out_path, index=False)
#     df_blocks_out.to_csv(out_path.with_name("matched_transcripts_blocks.csv"), index=False)
#     print(f"Done! Saved {len(df_out)} per-row matches to '{out_path}'")
#     print(f"Also saved per-block matches to '{out_path.with_name('matched_transcripts_blocks.csv')}'")

# if __name__ == "__main__":
#     main()  


#import json
# import re
# from pathlib import Path
# import pandas as pd
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# from difflib import SequenceMatcher

# # ---------- Config: set your date once ----------
# DATE = "2025-09-25"
# PATH_JSON = Path(f"data/plenarprotokoll-speeches.json")  # speeches
# PATH_CSV  = Path("data/transcript_aligned_clustered.csv")                 # whisper

# # ---------- Preprocessing (keeps German letters) ----------
# GERMAN_LETTERS = "a-zäöüß"
# NON_GERMAN_RE = re.compile(rf"[^ {GERMAN_LETTERS}\s]", flags=re.IGNORECASE)
# WS_RE = re.compile(r"\s+")

# def preprocess_text(text: str) -> str:
#     """
#     Cleans and standardizes text for comparison:
#       - casefold (better than lower for unicode)
#       - remove punctuation/numbers but KEEP German umlauts and ß
#       - collapse whitespace
#     """
#     if not isinstance(text, str):
#         return ""
#     text = text.casefold()
#     text = NON_GERMAN_RE.sub(" ", text)
#     text = WS_RE.sub(" ", text).strip()
#     return text

# # ---------- Core matching (your skeleton, adjusted) ----------
# def find_best_speech_match(transcript: str, speeches: list[str], top_n: int = 3):
#     """
#     Two-step match:
#       1) TF-IDF (German stopwords) to shortlist candidates
#       2) SequenceMatcher on original texts to refine
#     Returns (best_text, best_score, best_index). Best_index is within 'speeches'.
#     """
#     if not transcript or not speeches:
#         return None, 0.0, None

#     processed_transcript = preprocess_text(transcript)
#     processed_speeches = [preprocess_text(s) for s in speeches]
#     all_texts = processed_speeches + [processed_transcript]

#     try:
#         tfidf = TfidfVectorizer(stop_words="german")
#         tfidf_matrix = tfidf.fit_transform(all_texts)
#     except ValueError:
#         return None, 0.0, None

#     speeches_matrix = tfidf_matrix[:-1]
#     transcript_vec = tfidf_matrix[-1]

#     sims = cosine_similarity(transcript_vec, speeches_matrix)[0]
#     candidate_indices = sims.argsort()[::-1][:max(top_n, 1)]

#     best_match, best_score, best_idx = None, 0.0, None
#     for idx in candidate_indices:
#         candidate_text = speeches[idx]
#         score = SequenceMatcher(None, transcript, candidate_text).ratio()
#         if score > best_score:
#             best_score = score
#             best_match = candidate_text
#             best_idx = idx

#     return best_match, best_score, best_idx

# # ---------- Batch match: Whisper segments -> Bundestag speeches ----------
# def match_whisper_to_plenar(csv_path: Path, json_path: Path, top_n: int = 3, min_len: int = 20):
#     """
#     Loads transcript_aligned_clustered.csv and plenarprotokoll-speeches.json,
#     matches each Whisper segment to the closest Bundestag speech.
#     Returns a DataFrame of matches.
#     """
#     # Load
#     df_csv = pd.read_csv(csv_path)
#     with open(json_path, "r", encoding="utf-8") as f:
#         speeches_raw = json.load(f)
#     df_json = pd.DataFrame(speeches_raw)

#     # Expect columns:
#     # df_csv: 'text' (Whisper segments), optional: 'start','end','speaker'
#     # df_json: 'text','speaker','party','date' (as created earlier)
#     if "text" not in df_csv or "text" not in df_json:
#         raise ValueError("Both CSV and JSON must have a 'text' column.")

#     # Prepare lists for matching
#     speech_texts = df_json["text"].astype(str).tolist()

#     rows = []
#     for i, seg in enumerate(df_csv["text"].astype(str)):
#         # optionally skip ultra-short bits (noise/fillers)
#         if len(seg.strip()) < min_len:
#             rows.append({
#                 "csv_idx": i,
#                 "csv_text": seg,
#                 "csv_start": df_csv.get("start", pd.Series([None]*len(df_csv))).iloc[i],
#                 "csv_end": df_csv.get("end", pd.Series([None]*len(df_csv))).iloc[i],
#                 "csv_speaker": df_csv.get("speaker", pd.Series([None]*len(df_csv))).iloc[i],
#                 "json_idx": None,
#                 "json_text": None,
#                 "json_speaker": None,
#                 "json_party": None,
#                 "json_date": None,
#                 "similarity": 0.0,
#             })
#             continue

#         best_text, best_score, best_idx = find_best_speech_match(seg, speech_texts, top_n=top_n)

#         if best_idx is not None:
#             rows.append({
#                 "csv_idx": i,
#                 "csv_text": seg,
#                 "csv_start": df_csv.get("start", pd.Series([None]*len(df_csv))).iloc[i],
#                 "csv_end": df_csv.get("end", pd.Series([None]*len(df_csv))).iloc[i],
#                 "csv_speaker": df_csv.get("speaker", pd.Series([None]*len(df_csv))).iloc[i],
#                 "json_idx": best_idx,
#                 "json_text": df_json.loc[best_idx, "text"],
#                 "json_speaker": df_json.get("speaker", pd.Series([None]*len(df_json))).iloc[best_idx],
#                 "json_party": df_json.get("party", pd.Series([None]*len(df_json))).iloc[best_idx],
#                 "json_date": df_json.get("date", pd.Series([None]*len(df_json))).iloc[best_idx],
#                 "similarity": float(best_score),
#             })
#         else:
#             rows.append({
#                 "csv_idx": i,
#                 "csv_text": seg,
#                 "csv_start": df_csv.get("start", pd.Series([None]*len(df_csv))).iloc[i],
#                 "csv_end": df_csv.get("end", pd.Series([None]*len(df_csv))).iloc[i],
#                 "csv_speaker": df_csv.get("speaker", pd.Series([None]*len(df_csv))).iloc[i],
#                 "json_idx": None,
#                 "json_text": None,
#                 "json_speaker": None,
#                 "json_party": None,
#                 "json_date": None,
#                 "similarity": 0.0,
#             })

#     matches = pd.DataFrame(rows)
#     return matches

# # ---------- Run & save ----------
# if __name__ == "__main__":
#     matches = match_whisper_to_plenar(PATH_CSV, PATH_JSON, top_n=4, min_len=20)
#     # Filter to only matched rows (exclude very short or unmatched segments)
#     matches_cleaned = matches.dropna(subset=["json_text", "json_speaker"]).copy()

#     # Select and reorder final output columns
#     final = matches_cleaned[[
#         "csv_speaker", "csv_text", "json_speaker", "json_text", "similarity"
#     ]]

#     out_path = Path(f"data/matching_speeches_yt_{DATE}.csv")
#     final.to_csv(out_path, index=False)

#     print(f"saved {len(final)} matched speech pairs → {out_path}")
#     print(final.head(10))














