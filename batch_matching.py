# matching_batch.py
import re
import json
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

"""
Transcripts sind perfect, manchmal verschwinden noch die MPs in den Redebeiträgen der Vizes 

Cleaning: präsidenten / vize minister den party namen = redeführer zuorden 
den Ministern die party Regierung zuordnen
matches rausfiltern die 0,4 matching score haben (generische phrases wie "thank you vice minister")
"""

# ----------  preprocessing ----------
def preprocess_text(text):
    """
    Cleans and standardizes text for comparison.
    - Converts text to lowercase.
    - Removes punctuation and numbers.
    - Strips extra whitespace.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^a-zäöüß\s]', '', text)     # keep umlauts/ß
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ---------- batch runner  ----------
def main():
    # paths / dirs
    json_path = Path("data/plenarprotokoll-speeches-foralgo.json")  
    in_dir = Path("data/cleaned")                                   
    out_dir = Path("data/matched")                                   
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load JSON once  ----
    with open(json_path, "r", encoding="utf-8") as f:
        speeches_data = json.load(f)

    if isinstance(speeches_data, dict):
        speeches_list = speeches_data.get("speeches", [speeches_data])
    elif isinstance(speeches_data, list):
        speeches_list = speeches_data
    else:
        raise ValueError("Unexpected JSON structure.")

    protokoll_name, protokoll_party, protokoll_text = [], [], []

    for item in speeches_list:
        if not isinstance(item, dict):
            continue

        name = (item.get("speaker") or item.get("name") or "").strip()
        party = (item.get("party") or "").strip()
        text = (item.get("text") or "").strip()

        # --- LOGIC UPDATE ---
        lname = name.lower()
        # 1) Anyone with "präsident" (incl. "präsidentin" or "vizepräsident") → host
        if "präsident" in lname:
            party = "Host"
        # 2) If no party info and not already host → Ministry
        elif party == "":
            party = "Ministry"

        protokoll_name.append(name)
        protokoll_party.append(party)
        protokoll_text.append(text)



    # ---- Build TF-IDF index on all JSON speeches  ----
    json_texts_proc = [preprocess_text(t) for t in protokoll_text]
    tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), sublinear_tf=True)
    json_matrix = tfidf.fit_transform(json_texts_proc)

    # ---- Iterate over all whisper CSVs in data/cleaned. Set this file structure in your csv ----
    csv_paths = sorted(in_dir.glob("*.csv"))
    if not csv_paths:
        print(f"No CSVs found in {in_dir.resolve()}")
        return

    for csv_path in csv_paths:
        print(f"Processing: {csv_path.name}")
        df_csv = pd.read_csv(csv_path)
        df_csv = df_csv[df_csv["text"].astype(str).str.strip().ne("")].reset_index(drop=True)

        results = []
        for _, r in df_csv.iterrows():
            seg_text = str(r["text"])
            seg_text_proc = preprocess_text(seg_text)

            seg_vec = tfidf.transform([seg_text_proc])
            sims = cosine_similarity(seg_vec, json_matrix)[0]
            best_idx = int(sims.argmax())
            best_sim = float(sims[best_idx])

            results.append({
                "protokoll_name": protokoll_name[best_idx],
                "protokoll_party": protokoll_party[best_idx],
                "similarity": best_sim,
                "transcript_start": r.get("start", ""),
                "transcript_end": r.get("end", ""),
                "protokoll_text": protokoll_text[best_idx],
                "transcript_speaker": r.get("speaker", ""),
                "transcript_text": seg_text
            })

        out_df = pd.DataFrame(results)
        out_file = out_dir / f"{csv_path.stem}_matched.csv"
        out_df.to_csv(out_file, index=False)
        print(f"  -> Saved {len(out_df)} rows to '{out_file}'")

if __name__ == "__main__":
    main()
