import pandas as pd

df = pd.read_csv("../topicmodelling/data/raw_topics/topics_representations_2025.csv", low_memory=False)

df['speech_start'] = df[['transcript_start', 'start']].max(axis=1)
df['speech_end'] = df[['transcript_end', 'end']].max(axis=1)
# df['speech_duration'] = round((df['speech_end'] - df['speech_start']), 5)
df['speech_duration'] = (df['speech_end'] - df['speech_start'])

print(df.shape)

sub = df[["filename", 
          "protokoll_name", 
          "topic", 
          "speech_duration",
          "text",
          "protokoll_text",
          "transcript_text",
          "source",
          "transcript_speaker",
          "similarity", 
          "speech_start",
          "speech_end",
          "protokoll_party",
          "transcript_start",
          "transcript_end",
          "date",
          "cluster_idx",
          "speaker",
          "start",
          "end",
          "words",
          "speaker_block",
          "probability",
          "Representation",
          "protokoll_docid",]]

print(sub.shape)

dups = sub[sub.duplicated(
    subset=["text", "filename", "protokoll_name", "topic", "speech_duration"],
    keep=False
)]

unique_speeches = sub[["text", "filename", "protokoll_name", "topic", "speech_duration"]].drop_duplicates().shape[0]
print("Number of unique speech_text entries:", unique_speeches)

dups = dups.sort_values(["text", "filename", "protokoll_name", "topic", "speech_duration"])

dups.to_excel("../data/check_duplicates.xlsx", index=False)