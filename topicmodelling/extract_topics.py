from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP
import pandas as pd
from sentence_transformers import SentenceTransformer
import glob
import os
from datetime import datetime

### SETUP ###

talkshow_path = "../youtube/data/clustered/talkshow_clustered/*.csv"
bundestag_path = "../matching/data/matched/*.csv"
output_path = "data/raw_topics"

def extract_date_from_filename(path):
    """
    Takes Filenames of 'DD-MM-YYY_***_clustered.csv' and returns date from filename
    """

    base = os.path.basename(path)
    date_str = base.split("_")[0]
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        return None

bundestag_dfs = []

for file in glob.glob(bundestag_path):
    if "meta" in file.lower():
        continue
    df = pd.read_csv(file)
    df["date"] = extract_date_from_filename(file)
    df["source"] = "bundestag"
    df["filename"] = os.path.basename(file)
    df["text"] = df["protokoll_text"]
    bundestag_dfs.append(df)


talkshow_dfs = []

for file in glob.glob(talkshow_path):
    df = pd.read_csv(file)
    df["date"] = extract_date_from_filename(file)
    df["source"] = "talkshow"
    df["filename"] = os.path.basename(file)
    talkshow_dfs.append(df)


# Combine DFs
combined_df = pd.concat(bundestag_dfs + talkshow_dfs, ignore_index=True)

print("Combined Shape: ", combined_df.shape)
print(combined_df[["text", "date", "source", "filename"]].head())

docs = combined_df["text"].astype(str).tolist()
docs_prefixed = [f"passage: {d}" for d in docs]

sources = combined_df["source"].tolist()
dates = combined_df["date"].tolist()


embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct").to("cuda")

topic_model = BERTopic(
    embedding_model = embedding_model
)

topics, probs = topic_model.fit_transform(docs_prefixed)

print(topic_model.get_topic_info().head(20))

combined_df["topic"] = topics
combined_df["probability"] = probs


topic_info = topic_model.get_topic_info()

topic_info["Representation"] = topic_info["Representation"].apply(
    lambda x: ", ".join(x)
)

topic_info = topic_info.rename(columns={"Topic":"topic"})

combined_df = combined_df.merge(
    topic_info[["topic", "Representation"]],
    how = "left",
    on = "topic"
)

output_file = os.path.join(output_path, "topics_representations_2025.csv")
os.makedirs(output_path, exist_ok=True)
combined_df.to_csv(output_file, index=False)

print("done")