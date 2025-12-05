import pandas as pd

print("windows filename: ----------------------")
df = pd.read_csv("../topicmodelling/data/raw_topics/topics_representations_2025.csv")
# print list of all values in filename column
unique_filenames = df["filename"].unique()
for filename in unique_filenames:
    if "clustered" in filename:
        print(filename)

print("original text: ----------------------")
ts_meta = pd.read_csv("../youtube/data/raw/talkshow_audio/metadata.csv")
ts_meta.columns = ["url", "title", "channel", "date", "talkshow_name"]
for index, row in ts_meta.iterrows():
    print(f"{row['date']}_{row['title']}_clustered.csv")