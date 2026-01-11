import pandas as pd

df = pd.read_csv("../topicmodelling/data/raw_topics/topics_representations_2025_youtube.csv", low_memory=False)

# df['speech_start'] = df[['transcript_start', 'start']].max(axis=1)
# df['speech_end'] = df[['transcript_end', 'end']].max(axis=1)
# df['speech_duration'] = round((df['speech_end'] - df['speech_start']), 5)
df['speech_duration'] = (df['end'] - df['start'])

print(df.shape)

dups = df[df.duplicated(
    subset=["text", "filename", "Topic", "speech_duration"],
    keep=False
)]

unique_speeches = df[["text", "filename", "Topic", "speech_duration"]].drop_duplicates().shape[0]
print("Number of unique speech_text entries:", unique_speeches)

dups = dups.sort_values(["text", "filename", "Topic", "speech_duration"])

dups.to_excel("../data/check_duplicates.xlsx", index=False)