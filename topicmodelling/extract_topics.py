from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP
import pandas as pd
from sentence_transformers import SentenceTransformer
import glob
import os
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer

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
    "ganz", "gar", "überhaupt", "immer", "nie", "vielleicht", "dann"
]
stop_words=set(speech_fillers+initial_words)
stop_words=list(stop_words)
vectorizer_model = CountVectorizer(
    stop_words=stop_words, 
    lowercase=False,        #need to wrap class to add lemmatization
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
combined_df = pd.concat(bundestag_dfs + talkshow_dfs, ignore_index=True)

print("Combined Shape: ", combined_df.shape)
print(combined_df[["text", "date", "source", "filename"]].head())

docs = combined_df["text"].astype(str).tolist()
docs_prefixed = [f"passage: {d}" for d in docs]

sources = combined_df["source"].tolist()
dates = combined_df["date"].tolist()


embedding_model = SentenceTransformer("intfloat/multilingual-e5-large-instruct").to("cuda")

cluster_model = MiniBatchKMeans(
    n_clusters=50,
    random_state=42,
    batch_size=1000
)

dim_reduction_model = IncrementalPCA(n_components=5)

topic_model = BERTopic(
    language="German",
    embedding_model=embedding_model,
    vectorizer_model=vectorizer_model,
    hdbscan_model=cluster_model,
    umap_model=dim_reduction_model,
    min_topic_size=10
)

chunk_size = 1000
total_docs = len(docs_prefixed)

for i in range(0, total_docs, chunk_size):
    chunk = docs_prefixed[i:i+chunk_size]
    topic_model.partial_fit(chunk)
    print(f"Processed chunk {i} to {min(i+chunk_size, total_docs)}")

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
os.makedirs(output_path, exist_ok = True)
combined_df.to_csv(output_file, index = False)

topic_info.to_csv((os.path.join(output_path, "topic_info_2025.csv")), index = False)

print("done")