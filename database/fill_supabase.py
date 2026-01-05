from dotenv import load_dotenv
import os
import csv
import pandas as pd
import unicodedata
import psycopg2
import hashlib

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

def norm_text(x):
    if x is None or pd.isna(x):
        return "Unknown"
    x = unicodedata.normalize("NFKC", str(x))
    x = x.replace("\u00A0", " ").strip()
    return x if x else "Unknown"

def make_speech_key(speech_text, seconds, file_id, speaker_id, topic_id):
    raw = f"{speech_text}|{seconds}|{file_id}|{speaker_id}|{topic_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

upsert_speaker = """
INSERT INTO private.speakers (speaker_name, speaker_party)
VALUES (%s, %s)
ON CONFLICT (speaker_name, speaker_party)
DO UPDATE SET 
    speaker_name = EXCLUDED.speaker_name
RETURNING speaker_id;"""

upsert_file = """
INSERT INTO private.files (file_name, file_date, file_year, source)
VALUES (%s, %s, %s, %s)
ON CONFLICT (file_name)
DO UPDATE SET 
    file_name = EXCLUDED.file_name
RETURNING file_id;"""

upsert_topic = """
INSERT INTO private.topics (topic_id, topic_keywords, topic_label)
VALUES (%s, %s, %s)
ON CONFLICT (topic_id)
DO NOTHING;"""

upsert_speech = """
INSERT INTO private.speeches (speech_key, speech_text, speech_duration, file, speaker, topic)
VALUES (%s, %s, make_interval(secs => %s), %s, %s, %s)
ON CONFLICT (speech_key)
DO NOTHING;"""

speaker_cache = {}
file_cache = {}
topic_cache = set()

with psycopg2.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        with open("../topicmodelling/data/raw_topics/topics_representations_2025.csv", encoding="utf-8") as tr:
            reader = csv.DictReader(tr)

            for i, row in enumerate(reader, start=1):
                # getting data
                speaker_name = norm_text(row["protokoll_name"])
                speaker_party = norm_text(row["protokoll_party"])
                file_name = norm_text(row["filename"])
                file_date = norm_text(row["date"])
                file_year = int(file_date[:4])
                source = row["source"]
                if source == "bundestag":
                    seconds = float(row["transcript_end"]) - float(row["transcript_start"])
                elif source == "talkshow":
                    seconds = float(row["end"]) - float(row["start"])
                else:
                    print(f"Unknown source: {source}")
                    continue
                topic_id = int(row["topic"])
                topic_keywords = row["Representation"]
                topic_label = "Unknown"
                speech_text = norm_text(row["text"])

                # upserting data
                # speaker
                skey = (speaker_name, speaker_party)
                speaker_id = speaker_cache.get(skey)
                if speaker_id is None:
                    cur.execute(upsert_speaker, (speaker_name, speaker_party))
                    speaker_id = cur.fetchone()[0]
                    speaker_cache[skey] = speaker_id
                # file
                file_id = file_cache.get(file_name)
                if file_id is None:
                    cur.execute(upsert_file, (file_name, file_date, file_year, source))
                    file_id = cur.fetchone()[0]
                    file_cache[file_name] = file_id
                # topic
                if topic_id not in topic_cache:
                    cur.execute(upsert_topic, (topic_id, topic_keywords, topic_label))
                    topic_cache.add(topic_id)
                # speech
                speech_key = make_speech_key(speech_text, seconds, file_id, speaker_id, topic_id)
                cur.execute(upsert_speech, (speech_key, speech_text, seconds, file_id, speaker_id, topic_id))
        
                if i % 5000 == 0:
                    conn.commit()
                    print(f"Inserted/updated {i} rows...")
        conn.commit()

print("Database population completed.")