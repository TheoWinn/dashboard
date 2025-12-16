from bertopic import BERTopic
#from hdbscan import HDBSCAN
#from umap import UMAP
import pandas as pd
from sentence_transformers import SentenceTransformer
import glob
import os
from datetime import datetime
from bertopic.vectorizers import OnlineCountVectorizer
from river import cluster 
from river import stream
from sklearn.decomposition import IncrementalPCA
import numpy as np

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

    def partial_fit(self, X, y=None, sample_weight=None):
        X = np.asarray(X, dtype=np.float64)
        return super().partial_fit(X, y, sample_weight=sample_weight)


class RiverBERTopicWrapper:
    def __init__(self, model):
        self.model = model
        self.labels_ = []

    def partial_fit(self, embeddings, y=None):
        # 1. Learn (Train) phase
        for embedding, _ in stream.iter_array(embeddings):
            self.model.learn_one(embedding)

        # 2. Predict phase (Update self.labels_ for BERTopic to read)
        # We call our own predict method to populate self.labels_
        self.predict(embeddings)
        
        # 3. Return self (Standard Scikit-Learn convention)
        return self

    def predict(self, embeddings):
        labels = []
        for embedding, _ in stream.iter_array(embeddings):
            label = self.model.predict_one(embedding)
            
            # Handle noise (None -> -1)
            if label is None:
                labels.append(-1)
            else:
                labels.append(label)

        self.labels_ = np.array(labels)
        return self.labels_

# Setup for removing stop words/fillers from topic AFTER topics have been modelled for better human understanding
initial_words=open('stp_wrds.txt', 'r', encoding='utf-8').read().splitlines()
speech_fillers = [
    # Hesitations & Interjections
    "äh", "ähm", "hm", "tja", "pff", "naja", "oh", "ah", "okay", "ok", 
    "genau", "richtig", "klar", "gut", "so", "ja genau", "na gut", "na ja", "ja",
    "mhm", "hmm", "hmmm", "uh", "uhm",
    # Common Speech Particles (Modalpartikel) - highly frequent in speech!
    "halt", "eben", "mal", "ja", "doch", "wohl", "schon", "eigentlich", 
    "irgendwie", "sowieso", "sozusagen", "quasi", "praktisch", "buchstäblich",
    "glaube", "meine", "finde", "denke", "sagen", "gesagt", # "ich glaube", "ich sage mal"
    # Phrases often transcribed as single tokens or short meaningless connectors
    "ding", "sache", "zeug", "bisschen", "bissel", "paar",
    "natürlich", "selbstverständlich", "absolut", "definitiv",
    "ganz", "gar", "überhaupt", "immer", "nie", "vielleicht", "dann",
    #Bundestag spezifisch
    "Herren","Damen", "Dame", "Frau", "Herr","Präsident", "Vizepräsident",
    "Abgeordnete", "Abgeordneter", "Kolleginnen", "Kollegen", "Kollege", "Kollegin"
]
all_stop_words = set(speech_fillers + initial_words)

# Add title-cased versions of stop words to catch them at the start of sentences
expanded_stop_words = set(all_stop_words)
for word in all_stop_words:
    expanded_stop_words.add(word.title())
    expanded_stop_words.add(word.capitalize()) 
    expanded_stop_words.add(word.upper())
stop_words = list(expanded_stop_words)
vectorizer_model = OnlineCountVectorizer(
    stop_words=stop_words, 
    decay=.01,
    lowercase=False,        # Text itself should not be lowercased to preserve meaning
    min_df=5,             # Ignore words that appear in fewer than 10 documents
    ngram_range=(1, 2)     # Allow phrases like "Guten Morgen"
)

# bundestag_dfs = []

# for file in glob.glob(bundestag_path):
#     if "meta" in file.lower():
#         continue
#     df = pd.read_csv(file)
#     df["date"] = extract_date_from_filename(file)
#     df["source"] = "bundestag"
#     df["filename"] = os.path.basename(file)
#     df["text"] = df["protokoll_text"]
#     bundestag_dfs.append(df)


# talkshow_dfs = []

# for file in glob.glob(talkshow_path):
#     df = pd.read_csv(file)
#     df["date"] = extract_date_from_filename(file)
#     df["source"] = "talkshow"
#     df["filename"] = os.path.basename(file)
#     talkshow_dfs.append(df)


# # Combine DFs
# raw_combined_df = pd.concat(bundestag_dfs + talkshow_dfs, ignore_index=True)


#raw_combined_df.to_csv("end_df.csv", encoding='utf-8', index=False)
raw_combined_df = pd.read_csv("end_df.csv", encoding='utf-8',dtype=dtype_settings)
combined_df = raw_combined_df.copy()

# 1. Fill the missing 'date' column using 'protokoll_docid'
# We grab the first 10 characters (08-10-2025) from the ID
combined_df['date'] = combined_df['protokoll_docid'].astype(str).str[:10]

# 2. Now convert to datetime objects
combined_df['date'] = pd.to_datetime(combined_df['date'], format='%d-%m-%Y', errors='coerce')

# 3. Clean the text column
combined_df['text'] = combined_df['text'].fillna('').astype(str)
combined_df = combined_df[combined_df['text'].str.split().str.len() > 15].reset_index(drop=True)


# 5. Aggregate
daily_docs_df = combined_df.groupby(['date', 'source'])['text'].apply(lambda x: " ".join(x)).reset_index()
daily_docs_df = daily_docs_df.sort_values('date')

# Aggregate texts by filename to create larger "documents"

docs = daily_docs_df["text"].astype(str).tolist()
# sources = daily_docs_df["source"].tolist()
# dates = daily_docs_df["date"].tolist()


embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct")#.to("cuda")


river_model = cluster.DBSTREAM(
    clustering_threshold=0.2, 
    minimum_weight=1.0,
    intersection_factor=0.3,
    fading_factor=0.01,
)

dim_reduction_model = IncrementalPCA(n_components=12)
cluster_model = RiverBERTopicWrapper(river_model)

topic_model = BERTopic(
    language="German",
    embedding_model=embedding_model,
    vectorizer_model=vectorizer_model,
    hdbscan_model=cluster_model,
    umap_model=dim_reduction_model,
    min_topic_size=1
)

chunk_size = 1000
total_docs = len(docs)

for i in range(0, total_docs, chunk_size):
    chunk = docs[i:i+chunk_size]
    topic_model.partial_fit(chunk)
    print(f"Processed chunk {i} to {min(i+chunk_size, total_docs)}")

topics, probs = topic_model.transform(docs)

print(topic_model.get_topic_info().head(20))

combined_df["Topic"] = topics
combined_df["probability"] = probs

topic_info = topic_model.get_topic_info()

topic_info["Representation"] = topic_info["Representation"].apply(
    lambda x: ", ".join(x)
)

topic_info = topic_info.rename(columns={"Topic":"topic"})

combined_df = combined_df.merge(
    topic_info[["Topic", "Representation"]],
    how = "left",
    on = "Topic"
)

output_file = os.path.join(output_path, "topics_representations_2025.csv")
os.makedirs(output_path, exist_ok = True)
combined_df.to_csv(output_file, index = False)

topic_info.to_csv((os.path.join(output_path, "topic_info_2025.csv")), index = False)

print("done")