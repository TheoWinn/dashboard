from hdbscan import HDBSCAN
from umap import UMAP
from bertopic import BERTopic
import pandas as pd
from sentence_transformers import SentenceTransformer
import glob
import os
import numpy as np
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from bert_utils import clean_encoding_artifacts, extract_date_from_filename, sliding_window,get_gemini_labels

### SETUP ###

talkshow_path = "../youtube/data/clustered/talkshow_clustered/*.csv"
bundestag_path = "../matching/data/matched/*.csv"
output_path = "data/raw_topics"

bundestag_dfs = []

#AAAAAAAAAAAAAAAAAAAAAAAA
initial_words=open('../stp_wrds.txt', 'r', encoding='utf-8').read().splitlines()
speech_fillers = [
    # Hesitations & Interjections
    "äh", "ähm", "hm", "tja", "pff", "naja", "oh", "ah", "okay", "ok", 
    "genau", "richtig", "klar", "gut", "so", "ja genau", "na gut", "na ja", "ja",
    "mhm", "hmm", "hmmm", "uh", "uhm", "Nee",
    # Common Speech Particles (Modalpartikel) - highly frequent in speech!
    "halt", "eben", "mal", "ja", "doch", "wohl", "schon", "eigentlich", 
    "irgendwie", "sowieso", "sozusagen", "quasi", "praktisch", "buchstäblich",
    "glaube", "meine", "finde", "denke", "sagen", "gesagt", # "ich glaube", "ich sage mal"
    # Phrases often transcribed as single tokens or short meaningless connectors
    "ding", "sache", "zeug", "bisschen", "bissel", "paar",
    "natürlich", "selbstverständlich", "absolut", "definitiv",
    "ganz", "gar", "überhaupt", "immer", "nie", "vielleicht", "dann", "Vielen Dank", 
    #Bundestag spezifisch
    "Herren","Damen", "Dame", "Frau", "Herr","Präsident", "Vizepräsident",
    "Abgeordnete", "Abgeordneter", "Kolleginnen", "Kollegen", "Kollege", "Kollegin","Frage",
    #Talkshow spezifisch
    "Folge","Sendung", "Das war's für heute", "Hey","hey","bedanke","bedanken","Zuschauen","er","ihm","ihn",
]
all_stop_words = set(speech_fillers + initial_words)
# Add title-cased versions of stop words to catch them at the start of sentences
expanded_stop_words = set(all_stop_words)
for word in all_stop_words:
    expanded_stop_words.add(word.title())
    expanded_stop_words.add(word.capitalize()) 
    expanded_stop_words.add(word.upper())
stop_words = list(expanded_stop_words)
#AAAAAAAAAAAAAAAAAAAAAAAA

all_stop_words = set(speech_fillers + initial_words)
# Add title-cased versions of stop words to catch them at the start of sentences
expanded_stop_words = set(all_stop_words)
for word in all_stop_words:
    expanded_stop_words.add(word.title())
    expanded_stop_words.add(word.capitalize()) 
    expanded_stop_words.add(word.upper())
stop_words = list(expanded_stop_words)

vectorizer_model = CountVectorizer(
    stop_words=stop_words, 
    lowercase=False,        # Text itself should not be lowercased to preserve meaning
    min_df=2,
    ngram_range = (1,2)         # Ignore words that appear in fewer than 10 document    # Allow phrases like "Guten Morgen"
)

bundestag_dfs = []

for file in glob.glob(bundestag_path):
    if "meta" in file.lower():
        continue
    df = pd.read_csv(file)
    df["date"] = extract_date_from_filename(file)
    df["source"] = "bundestag"
    df["filename"] = os.path.basename(file)
    try:
        df["text"] = df["protokoll_text"]
    except:
        df["text"] = df["text"]
    bundestag_dfs.append(df)

bundestag_df_full = pd.concat(bundestag_dfs, ignore_index=True)
print(f"b full: {bundestag_df_full.shape}")
bundestag_df_split = bundestag_df_full.assign(text=bundestag_df_full['text'].str.split(r'\n\n+')).explode('text')
print(f"b split: {bundestag_df_split.shape}")
bundestag_df_cleaned = bundestag_df_split[bundestag_df_split['text'].str.strip().str.len() > 200]
print(f"b cleaned: {bundestag_df_cleaned.shape}")

talkshow_dfs = []

for file in glob.glob(talkshow_path):
    df = pd.read_csv(file)
    df["date"] = extract_date_from_filename(file)
    df["source"] = "talkshow"
    df["filename"] = os.path.basename(file)
    talkshow_dfs.append(df)

talkshow_df_full =pd.concat(talkshow_dfs, ignore_index=True)
print(f"t full: {talkshow_df_full.shape}")
talkshow_df_full['text'] = talkshow_df_full['text'].apply(sliding_window)
print(f"t full: {talkshow_df_full.shape}")

# 4. Explode to create new rows
# Metadata (speaker, date, etc.) is automatically duplicated for each new chunk
talkshow_df_ready = talkshow_df_full.explode('text').dropna(subset=['text']).reset_index(drop=True)
print(f"t ready: {talkshow_df_ready.shape}")

bundestag_fixed = bundestag_df_cleaned.copy()
bundestag_fixed['text'] = bundestag_fixed['text'].apply(lambda x: sliding_window(str(x)))
print(f"b fixed: {bundestag_fixed.shape}")
bundestag_fixed = bundestag_fixed.explode('text').reset_index(drop=True)
print(f"b fixed: {bundestag_fixed.shape}")

combined_talkshows = pd.concat(talkshow_dfs, ignore_index=True)
print(f"comb ts: {combined_talkshows.shape}")
talkshows_test = combined_talkshows[combined_talkshows['text'].str.strip().str.len() > 200]
print(f"ts test: {talkshows_test.shape}")
# Combine DFs
raw_combined_df= pd.concat([bundestag_fixed, talkshow_df_ready], ignore_index=True)
print(f"raw comb: {raw_combined_df.shape}")
combined_df = raw_combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
print(f"comb: {combined_df.shape}")

# Aggregate texts by filename to create larger "documents"
combined_df_clean = combined_df.copy()
combined_df_clean["text"] = combined_df["text"].apply(clean_encoding_artifacts)
print(f"comb clean: {combined_df_clean.shape}")
docs= combined_df_clean["text"].astype(str).tolist()
print(f"docs: {len(docs)}")


embedding_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2").to("cuda")

topic_model = BERTopic(
    embedding_model = embedding_model,
    umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine'),

)

topics, probs = topic_model.fit_transform(docs)

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
get_gemini_labels((os.path.join(output_path, "topic_info_2025.csv")),language="german")

print("done")