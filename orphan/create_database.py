import sqlite3

create_speakers = """
CREATE TABLE IF NOT EXISTS speakers (
    speaker_id INTEGER PRIMARY KEY AUTOINCREMENT,
    speaker_name TEXT,
    speaker_party TEXT,
    UNIQUE (speaker_name, speaker_party)
);"""

# create_files = """
# CREATE TABLE IF NOT EXISTS files (
#     file_id INTEGER PRIMARY KEY AUTOINCREMENT,
#     file_name TEXT,
#     file_raw_url TEXT,
#     file_date TEXT, 
#     file_year INT,
#     source TEXT NOT NULL,
#     file_talkshow_name TEXT,
#     CHECK (source IN ("bundestag", "talkshow")),
#     UNIQUE (file_raw_url)
# );"""

create_files = """
CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    file_date TEXT, 
    file_year INT,
    source TEXT NOT NULL,
    CHECK (source IN ("bundestag", "talkshow")),
    UNIQUE (file_name)
);"""

create_topics = """
CREATE TABLE IF NOT EXISTS topics (
    topic_id INT NOT NULL,
    topic_keywords TEXT,
    topic_label TEXT,
    topic_duration INTEGER NOT NULL DEFAULT 0,
    topic_duration_bt INTEGER NOT NULL DEFAULT 0,
    topic_duration_ts INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (topic_id),
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
    FOREIGN KEY (topic) REFERENCES topics(topic_id),
    UNIQUE (speech_text, speech_duration, file, speaker, topic)
);"""

create_trigger_insert = """
CREATE TRIGGER IF NOT EXISTS trg_topic_duration_insert
AFTER INSERT ON speeches
BEGIN
    -- overall duration
    UPDATE topics
    SET topic_duration = topic_duration + COALESCE(NEW.speech_duration, 0)
    WHERE topic_id = NEW.topic;

    -- duration bt
    UPDATE topics
    SET topic_duration_bt = topic_duration_bt + COALESCE(NEW.speech_duration, 0)
    WHERE topic_id = NEW.topic 
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = NEW.file AND f.source = 'bundestag');
    
    -- duration ts
    UPDATE topics
    SET topic_duration_ts = topic_duration_ts + COALESCE(NEW.speech_duration, 0)
    WHERE topic_id = NEW.topic 
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = NEW.file AND f.source = 'talkshow');
END;"""

create_trigger_update = """
CREATE TRIGGER IF NOT EXISTS trg_topic_duration_update
AFTER UPDATE OF speech_duration, topic ON speeches
BEGIN
    -- overall duration
    UPDATE topics
    SET topic_duration = topic_duration - COALESCE(OLD.speech_duration, 0)
    WHERE topic_id = OLD.topic;
    
    UPDATE topics
    SET topic_duration = topic_duration + COALESCE(NEW.speech_duration, 0)
    WHERE topic_id = NEW.topic;

    -- duration bt
    UPDATE topics
    SET topic_duration_bt = topic_duration_bt - COALESCE(OLD.speech_duration, 0)
    WHERE topic_id = OLD.topic 
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = OLD.file AND f.source = 'bundestag');
    
    UPDATE topics
    SET topic_duration_bt = topic_duration_bt + COALESCE(NEW.speech_duration, 0)
    WHERE topic_id = NEW.topic
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = NEW.file AND f.source = 'bundestag');

    -- duration ts
    UPDATE topics
    SET topic_duration_ts = topic_duration_ts - COALESCE(OLD.speech_duration, 0)
    WHERE topic_id = OLD.topic 
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = OLD.file AND f.source = 'talkshow');
    
    UPDATE topics
    SET topic_duration_ts = topic_duration_ts + COALESCE(NEW.speech_duration, 0)
    WHERE topic_id = NEW.topic
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = NEW.file AND f.source = 'talkshow');
END;"""

create_trigger_delete = """
CREATE TRIGGER IF NOT EXISTS trg_topic_duration_delete
AFTER DELETE ON speeches
BEGIN
    -- overall duration
    UPDATE topics
    SET topic_duration = topic_duration - COALESCE(OLD.speech_duration, 0)
    WHERE topic_id = OLD.topic;

    -- duration bt
    UPDATE topics
    SET topic_duration_bt = topic_duration_bt - COALESCE(OLD.speech_duration, 0)
    WHERE topic_id = OLD.topic 
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = OLD.file AND f.source = 'bundestag');

    -- duration ts
    UPDATE topics
    SET topic_duration_ts = topic_duration_ts - COALESCE(OLD.speech_duration, 0)
    WHERE topic_id = OLD.topic 
        AND EXISTS (
            SELECT 1 FROM files f
            WHERE f.file_id = OLD.file AND f.source = 'talkshow');
END;"""


with sqlite3.connect("../data/test.db") as conn:
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
    # Triggers
    cursor.execute(create_trigger_insert)
    cursor.execute(create_trigger_update)
    cursor.execute(create_trigger_delete)
    conn.commit()
    print("Database and tables created successfully.")

