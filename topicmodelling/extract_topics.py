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
from bert_utils import OnlineRepresentativeTracker

### SETUP ###

talkshow_path = "../youtube/data/clustered/talkshow_clustered/*.csv"
bundestag_path = "dashboard/youtube/data/transcribed/bundestag_transcript"#<-y<t transcript #"../matching/data/matched/*.csv" <- xml
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
        # Learn  phase
        for embedding, _ in stream.iter_array(embeddings):
            self.model.learn_one(embedding)
        self.predict(embeddings)      
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
initial_words=open('../stp_wrds.txt', 'r', encoding='utf-8').read().splitlines()
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
    min_df=1,             # Ignore words that appear in fewer than 10 documents
    ngram_range=(1, 2)     # Allow phrases like "Guten Morgen"
)

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
raw_combined_df = pd.concat(bundestag_dfs + talkshow_dfs, ignore_index=True)
combined_df = raw_combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
combined_df["text"] = "passage: " + combined_df["text"]
# Aggregate texts by filename to create larger "documents"
docs = combined_df["text"].astype(str).tolist()
# sources = daily_docs_df["source"].tolist()
# dates = daily_docs_df["date"].tolist()


embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct").to("cuda")



############################################################
sample_docs = docs[:1000] # Take first 1000 docs
# Ensure prefix is added!
embeddings = embedding_model.encode(sample_docs)
pca = IncrementalPCA(n_components=50)
pca_embeddings = pca.fit_transform(embeddings)

# 3. Measure Distances
from sklearn.metrics.pairwise import euclidean_distances
dists = euclidean_distances(pca_embeddings)
mean_dist = np.mean(dists)
min_dist = np.min(dists[dists > 0])

print(f"Mean Distance: {mean_dist:.4f}")
print(f"Min Non-Zero Distance: {min_dist:.4f}")
print(f"Current Threshold: 0.3")
##############################################################

river_model = cluster.DBSTREAM(
    clustering_threshold=0.42, # Increased from 0.18 to capture broader topics
    minimum_weight=1.0,
    intersection_factor=0.1,
    fading_factor=0.0,       # 0.001 means weight halves every ~700 steps.                              # For 50k docs, this is fine, but ensures recent topics dominate.    # Clean up weak clusters every chunk
)

dim_reduction_model = IncrementalPCA(n_components=70)
cluster_model = RiverBERTopicWrapper(river_model)

topic_model = BERTopic(
    language="German",
    embedding_model=embedding_model,
    vectorizer_model=vectorizer_model,
    hdbscan_model=cluster_model,
    umap_model=dim_reduction_model,
    min_topic_size=10
)

rep_tracker = OnlineRepresentativeTracker(top_n=3)
chunk_size = 1000
total_docs = len(docs)

for i in range(0, total_docs, chunk_size):
    chunk = docs[i:i+chunk_size]
    topic_model.partial_fit(chunk)
    chunk_embeddings = embedding_model.encode(chunk) 

    chunk_topics, _ = topic_model.transform(chunk, embeddings=chunk_embeddings)
    
    rep_tracker.update(chunk, chunk_embeddings, chunk_topics)
    print(f"Processed chunk {i} to {min(i+chunk_size, total_docs)}")

topics, probs = topic_model.transform(docs)
final_reps = rep_tracker.get_representatives()
topic_model.topic_representations_ = topic_model.topic_representations_(final_reps)
print(topic_model.get_topic_info().head(20))

combined_df["Topic"] = topics
combined_df["probability"] = probs


topic_info = topic_model.get_topic_info()

topic_info["Representation"] = topic_info["Representation"].apply(
    lambda x: ", ".join(x)
)

# Mean Distance: 0.4296
# Min Non-Zero Distance: 0.0000
# Current Threshold: 0.3
#topic_info = topic_info.rename(columns={"Topic":"topic"})

combined_df = combined_df.merge(
    topic_info[["Topic", "Representation"]],
    how = "left",
    on = "Topic"
)

output_file = os.path.join(output_path, "topics_representations_2025_youtube_3.csv")
os.makedirs(output_path, exist_ok = True)
combined_df.to_csv(output_file, index = False)

topic_info.to_csv((os.path.join(output_path, "topic_info_2025.csv")), index = False)

print("done")