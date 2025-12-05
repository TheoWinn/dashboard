import sqlite3

with sqlite3.connect("test.db") as conn:
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



import pandas as pd

df = pd.read_csv("../topicmodelling/data/raw_topics/topics_representations_2025.csv")

# Count unique combinations
unique_pairs = df[["protokoll_name", "protokoll_party"]].drop_duplicates()

print("Number of unique (name, party) combinations:", len(unique_pairs))

unique_filenames = df["filename"].unique()
print(len(unique_filenames))

with sqlite3.connect("test.db") as conn:
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE name='speakers';")
    print(cur.fetchone()[0])
    cur.execute("""
        SELECT COUNT(DISTINCT speaker_name || '|' || COALESCE(speaker_party, ''))
        FROM speakers;
    """)
    print("DB unique (name, party):", cur.fetchone()[0])