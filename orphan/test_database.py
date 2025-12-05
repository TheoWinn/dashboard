import sqlite3
import csv
import pandas as pd
import re
import unicodedata
import base64
import pathvalidate as pv

def norm_text(x):
    if x is None or pd.isna(x):
        return "Unknown"
    x = unicodedata.normalize("NFKC", str(x))
    x = x.replace("\u00A0", " ")
    x = x.strip()
    return x if x else "Unknown"

# pattern to bring titles into filename style
p = r'[<>:"/\\|?*\x00-\x1F]'
def fix_mojibake(s: str) -> str:
    try:
        repaired = s.encode("latin1").decode("utf8")
    except Exception:
        repaired = s
    # normalize combining accents (fuÌˆhrt → führt)
    repaired = unicodedata.normalize("NFC", repaired)
    return repaired

def clean_title_for_filename(title: str) -> str:
    title = fix_mojibake(title)
    # Normalize unicode
    title = unicodedata.normalize("NFKC", title)
    # Replace separators that SHOULD become spaces (safe!)
    title = title.replace("|", " ")
    title = title.replace(":", " ")
    # Replace long dashes with space (keep hyphens!)
    title = title.replace("–", " ").replace("—", " ")
    # KEEP your successful behavior:
    # delete everything except allowed characters
    title = re.sub(r"[^0-9A-Za-zÄÖÜäöüß ._-]", "", title)
    # collapse spaces
    title = re.sub(r"\s+", " ", title).strip()
    return title

# talkshow transcripts
ts_meta = pd.read_csv("../youtube/data/raw/talkshow_audio/metadata.csv")
ts_meta.columns = ["url", "title", "channel", "date", "talkshow_name"]
# ts_meta["title"] = ts_meta["title"].apply(lambda x: clean_title_for_filename(x))
ts_meta["filename"] = ts_meta.apply(
    lambda r: pv.sanitize_filename(f"{r["date"]}_{r["title"]}_clustered.csv", platform="Windows"),
    axis=1
)
# either from matched data
bt_meta = pd.read_csv("../bundestag/data/raw/metadata.csv")
bt_meta["filename"] = bt_meta.apply(
    lambda r: f"{r["date_formatted"]}_matched.csv",
    axis=1
)
# or from yt transcripts
bt_yt_meta = pd.read_csv("../youtube/data/raw/bundestag_audio/metadata.csv")
bt_yt_meta.columns = ["url", "title", "channel", "date"]
bt_yt_meta["title"] = bt_yt_meta["title"].apply(lambda x: clean_title_for_filename(x))
bt_yt_meta["filename"] = bt_yt_meta.apply(
    lambda r: pv.sanitize_filename(f"{r["date"]}_{r["title"]}_clustered.csv", platform="Windows"),
    axis=1
)

conn = sqlite3.connect("test.db")
cur = conn.cursor()

insert_speakers = """INSERT OR IGNORE INTO speakers (speaker_name, speaker_party)
VALUES (?, ?)
;"""

insert_files = """INSERT OR IGNORE INTO files (file_name, file_raw_url, file_date, file_year, source, file_talkshow_name)
VALUES (?, ?, ?, ?, ?, ?)
;"""

insert_topics = """INSERT OR IGNORE INTO topics (topic_id, topic_keywords, topic_label)
VALUES (?, ?, ?)
;"""

insert_speeches = """INSERT OR IGNORE INTO speeches (speech_text, speech_duration, file, speaker, topic)
VALUES (?, ?, 
    (SELECT file_id FROM files WHERE file_name = ?),
    (SELECT speaker_id FROM speakers WHERE speaker_name = ? AND speaker_party = ?),
    ?)
;"""

last_unknown_filename = ""
last_matched = ""
with open("../topicmodelling/data/raw_topics/topics_representations_2025.csv", encoding="utf-8") as tr:
    reader = csv.DictReader(tr)
    for row in reader:
        # speakers
        speaker_name = norm_text(row["protokoll_name"])
        speaker_party = norm_text(row["protokoll_party"])
        # files
        file_name = pv.sanitize_filename(row["filename"], platform="POSIX")
        url = "Unknown"
        talkshow_name = "Unknown"
        speech_duration = "Unknown"
        file_raw_url = "Unknown"
        file_talkshow_name = "Unknown"
        if row["source"] == "bundestag":
            if "matched" in file_name:
                url = bt_meta.loc[bt_meta["filename"] == file_name, "fundstelle.xml_url"]
            elif "clustered" in file_name:
                url = bt_yt_meta.loc[bt_yt_meta["filename"] == file_name, "url"]
            else:
                print(f"Unknown bundestag file: {file_name}")
            speech_duration = (float(row["transcript_end"]) - float(row["transcript_start"])) / 60
        elif row["source"] == "talkshow":
            url = ts_meta.loc[ts_meta["filename"] == file_name, "url"]
            talkshow_name = ts_meta.loc[ts_meta["filename"] == file_name, "talkshow_name"]
            if not talkshow_name.empty:
                file_talkshow_name = talkshow_name.values[0]
            speech_duration = (float(row["end"]) - float(row["start"])) / 60
            # if not url.empty:
            #     matched = ts_meta.loc[ts_meta["filename"] == file_name, "filename"].values[0]
            #     if last_matched != matched:
            #         last_matched = matched
            #         print(f"matched filename: {file_name} to text: {matched}")
        if not url.empty:
            file_raw_url = url.values[0]

        if file_raw_url == "Unknown":
            if last_unknown_filename != file_name:
                last_unknown_filename = file_name
                print(f"Unknown URL for file: {file_name}")
        file_date = row["date"]
        file_year = int(file_date[:4])
        source = row["source"]
        # topics
        topic_id = int(row["topic"])
        topic_keywords = row["Representation"]
        topic_label = "Unknown" # add later
        # speeches
        speech_text = norm_text(row["text"])
        

        # Now insert into database
        cur.execute(insert_speakers, (speaker_name, speaker_party))
        cur.execute(insert_files, (file_name, file_raw_url, file_date, file_year, source, file_talkshow_name))
        cur.execute(insert_topics, (topic_id, topic_keywords, topic_label))
        cur.execute(insert_speeches, (speech_text, speech_duration, file_name, speaker_name, speaker_party, topic_id))
        

conn.commit()
conn.close()

        
        

        
        

