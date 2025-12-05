import sqlite3

create_speakers = """
CREATE TABLE IF NOT EXISTS speakers (
    speaker_id INTEGER PRIMARY KEY AUTOINCREMENT,
    speaker_name TEXT,
    speaker_party TEXT,
    UNIQUE (speaker_name, speaker_party)
);"""

create_files = """
CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    file_raw_url TEXT,
    file_date TEXT, 
    file_year INT,
    source TEXT NOT NULL,
    file_talkshow_name TEXT,
    CHECK (source IN ("bundestag", "talkshow")),
    UNIQUE (file_raw_url)
);"""

create_topics = """
CREATE TABLE IF NOT EXISTS topics (
    topic_id INT NOT NULL,
    topic_keywords TEXT,
    topic_label TEXT,
    PRIMARY KEY (topic_id)
    UNIQUE (topic_keywords, topic_label)
);"""

create_speeches = """
CREATE TABLE IF NOT EXISTS speeches (
    speech_id INTEGER PRIMARY KEY AUTOINCREMENT,
    speech_text TEXT,
    speech_duration TIME,
    file INT,
    speaker INT,
    topic INT,
    FOREIGN KEY (file) REFERENCES files(file_id),
    FOREIGN KEY (speaker) REFERENCES speakers(speaker_id),
    FOREIGN KEY (topic) REFERENCES topics(topic_id)
);"""


with sqlite3.connect("test.db") as conn:
    cursor = conn.cursor()
    cursor.execute(create_speakers)
    cursor.execute(create_files)    
    cursor.execute(create_topics)
    cursor.execute(create_speeches)
    # Insert default speaker (if not exists)
    cursor.execute("""
                INSERT OR IGNORE INTO speakers (speaker_name, speaker_party)
                VALUES ("Unknown", "Unknown")
                ;""")
    conn.commit()
    print("Database and tables created successfully.")

