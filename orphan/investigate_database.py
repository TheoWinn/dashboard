import sqlite3
import numpy as np
import pandas as pd

with sqlite3.connect("../data/test.db") as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    tables = cur.fetchall()
    for (table,) in tables:
        print(f"\n=== TABLE: {table} ===")
        # number of rows
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        count = cur.fetchone()[0]
        print(f"Has {count} rows.")
        # get column names
        cur.execute(f"PRAGMA table_info({table});")
        columns = [col[1] for col in cur.fetchall()]
        # For speeches table → exclude speech_text
        if table == "speeches":
            columns_to_select = [c for c in columns if c != "speech_text"]
        else:
            columns_to_select = columns
        print("Columns:", columns_to_select)
        # build SELECT query
        col_str = ", ".join(columns_to_select)
        cur.execute(f"SELECT {col_str} FROM {table} LIMIT 20;")
        rows = cur.fetchall()
        # print rows
        if not rows:
            print("No rows.")
        else:
            for row in rows:
                print(row)


df = pd.read_csv("../topicmodelling/data/raw_topics/topics_representations_2025.csv", low_memory=False)
print(df.shape)

# Count unique combinations
unique_pairs = df[["protokoll_name", "protokoll_party"]].drop_duplicates()

print("Number of unique (name, party) combinations:", len(unique_pairs))

unique_filenames = df["filename"].unique()
print(len(unique_filenames))


with sqlite3.connect("../data/test.db") as conn:
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE name='speeches';")
    print(cur.fetchone()[0])
    cur.execute("""
        SELECT COUNT(DISTINCT speaker_name || '|' || COALESCE(speaker_party, ''))
        FROM speakers;
    """)
    print("DB unique (name, party):", cur.fetchone()[0])

# checking durations per topic
df['speech_start'] = df[['transcript_start', 'start']].max(axis=1)
df['speech_end'] = df[['transcript_end', 'end']].max(axis=1)
df['speech_duration'] = (df['speech_end'] - df['speech_start']) / 60
df['dur_bundestag'] = np.where(df['source'] == 'bundestag',
                               df['speech_duration'], 0)
df['dur_talkshow'] = np.where(df['source'] == 'talkshow',
                              df['speech_duration'], 0)
agg = (
    df.groupby('topic')
      .agg(
          topic_total_duration=('speech_duration', 'sum'),
          topic_total_duration_bundestag=('dur_bundestag', 'sum'),
          topic_total_duration_talkshow=('dur_talkshow', 'sum')
      )
      .reset_index()
)
print(agg.head(20))

unique_speeches = df[["text", "filename", "protokoll_name", "topic", "speech_duration"]].drop_duplicates().shape[0]
print("Number of unique speech_text entries:", unique_speeches)

dups = df[df.duplicated(subset=["text", "filename", "protokoll_name", "topic", "speech_duration"], keep=False)]
print(dups.sort_values(["text", "filename", "protokoll_name", "topic", "speech_duration"]))

# now for subset
print("Subset check:")
df = pd.read_csv("../data/topics_representations_sample.csv")
# checking durations per topic
df['speech_start'] = df[['transcript_start', 'start']].max(axis=1)
df['speech_end'] = df[['transcript_end', 'end']].max(axis=1)
df['speech_duration'] = (df['speech_end'] - df['speech_start']) / 60
df['dur_bundestag'] = np.where(df['source'] == 'bundestag',
                               df['speech_duration'], 0)
df['dur_talkshow'] = np.where(df['source'] == 'talkshow',
                              df['speech_duration'], 0)
agg = (
    df.groupby('topic')
      .agg(
          topic_total_duration=('speech_duration', 'sum'),
          topic_total_duration_bundestag=('dur_bundestag', 'sum'),
          topic_total_duration_talkshow=('dur_talkshow', 'sum')
      )
      .reset_index()
)
print(agg.head(20))