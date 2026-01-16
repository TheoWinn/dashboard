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
from pathlib import Path
from pandas.errors import EmptyDataError
import re


### SETUP ###

talkshow_path = "../youtube/data/clustered/talkshow_clustered/*.csv"
bundestag_path = "../matching/data/matched/*.csv"
output_path = "data/raw_topics"
merge = True
testrun = "leonie11"

os.environ["HF_HUB_HTTP_TIMEOUT"] = "60"         # seconds
os.environ["HF_HUB_ETAG_TIMEOUT"] = "60"

### Stop-Words ###

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

vectorizer_model = CountVectorizer(
    stop_words=stop_words, 
    lowercase=False,        # Text itself should not be lowercased to preserve meaning
    min_df=2,
    ngram_range = (1,2)         # Ignore words that appear in fewer than 10 document    # Allow phrases like "Guten Morgen"
)

### Data Pre-Processing ###

# read in already processed filenames
output_dir = Path(output_path)
meta_file = output_dir/"metadata.csv"
if meta_file.exists():
    try:
        meta = pd.read_csv(meta_file, header = None)
        log_files = meta[0].tolist()
        meta = meta.values.tolist()
    except EmptyDataError:
        log_files, meta = [], []
else:
    log_files, meta = [], []

## BUNDESTAG

bundestag_dfs = []

pattern = re.compile(r"^(0[1-9]|[12][0-9]|3[01])-(08|09|10|11|12)-2025")

for file in glob.glob(bundestag_path):
    filename = os.path.basename(file)
    if filename not in log_files:
        # if pattern.match(filename):
            # print(f"test skip {filename}")
            # continue
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
        # append to meta_file
        today = datetime.now().date()
        meta.append([filename, today])

# concatenated df
bundestag_df_full = pd.concat(bundestag_dfs, ignore_index=True)
print(f"b full: {bundestag_df_full.shape}")
# remove short text (under 200 characters)
bundestag_df_short = bundestag_df_full[bundestag_df_full['text'].str.strip().str.len() > 200]
print(f"b short: {bundestag_df_short.shape}")
# split into smaller paragraphs
bundestag_df_split = bundestag_df_short.assign(text=bundestag_df_short['text'].str.split(r'\n\n+')).explode('text')
print(f"b split: {bundestag_df_split.shape}")
# chunk text into lists if too long
bundestag_fixed = bundestag_df_split.copy()
bundestag_fixed['text'] = bundestag_fixed['text'].apply(lambda x: sliding_window(str(x)))
print(f"b fixed: {bundestag_fixed.shape}")
# each chunk own line
bundestag_fixed = bundestag_fixed.explode('text').reset_index(drop=True)
print(f"b fixed: {bundestag_fixed.shape}")

## TALKSHOWS

talkshow_dfs = []

for file in glob.glob(talkshow_path):
    filename = os.path.basename(file)
    if filename not in log_files:
        # if pattern.match(filename):
            # print(f"test skip {filename}")
            # continue
        df = pd.read_csv(file)
        df["date"] = extract_date_from_filename(file)
        df["source"] = "talkshow"
        df["filename"] = os.path.basename(file)
        talkshow_dfs.append(df)
        # append to meta_file
        today = datetime.now().date()
        meta.append([filename, today])

# save metadata
pd.DataFrame(meta, columns=["filename", "date_processed"]).to_csv(meta_file, index=False, header=False)

# concatenated df
talkshow_df_full =pd.concat(talkshow_dfs, ignore_index=True)
print(f"t full: {talkshow_df_full.shape}")
# remove short text (under 200 characters)
talkshow_df_short = talkshow_df_full[talkshow_df_full['text'].str.strip().str.len() > 200]
print(f"t short: {talkshow_df_short.shape}")
# chunk text into lists if too long
talkshow_df_short['text'] = talkshow_df_short['text'].apply(sliding_window)
print(f"t short: {talkshow_df_short.shape}")
# each chunk own line
talkshow_df_ready = talkshow_df_short.explode('text').dropna(subset=['text']).reset_index(drop=True)
print(f"t ready: {talkshow_df_ready.shape}")

## COMBINE

# combine dfs
raw_combined_df= pd.concat([bundestag_fixed, talkshow_df_ready], ignore_index=True)
print(f"raw comb: {raw_combined_df.shape}")
# shuffle
combined_df = raw_combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
print(f"comb: {combined_df.shape}")
# clean encoding artifacts
combined_df_clean = combined_df.copy()
combined_df_clean["text"] = combined_df_clean["text"].apply(clean_encoding_artifacts)
print(f"comb clean: {combined_df_clean.shape}")
# transform into list
docs= combined_df_clean["text"].astype(str).tolist()
print(f"docs: {len(docs)}")

print(combined_df_clean["source"].value_counts())

### BERTopic ###

embedding_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2").to("cuda")
new_topics = set()
if merge:
    with open("models/last_model.txt", "r", encoding="utf-8") as f:
        base_model_name = f.read().strip()
    base_model_path = f"models/{base_model_name}" 
    base_model = BERTopic.load(base_model_path, embedding_model=embedding_model)
    weekly_model = BERTopic(
        embedding_model = embedding_model,
        umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine'),
        vectorizer_model=vectorizer_model
    )
    weekly_model.fit(docs)
    topic_model = BERTopic.merge_models([base_model, weekly_model], min_similarity=0.7)
    topics, probs = topic_model.transform(docs)
    # check for new topics
    base_topics = set(base_model.get_topic_info()["Topic"])
    merged_topics = set(topic_model.get_topic_info()["Topic"])
    new_topics = merged_topics - base_topics
else:
    topic_model = BERTopic(
        embedding_model = embedding_model,
        umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine'),
        vectorizer_model=vectorizer_model
    )
    topics, probs = topic_model.fit_transform(docs)

# save model
model_dir = Path("models")
model_dir.mkdir(parents=True, exist_ok=True)
model_name = f"bertopic_2025_{testrun}"
model_path = model_dir / model_name
topic_model.save(str(model_path))  # saves as a folder by default
print(f"Saved model to: {model_path}")
with open("models/last_model.txt", "w", encoding="utf-8") as f:
    f.write(model_name)

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

output_file = os.path.join(output_path, f"topics_representations_2025_{testrun}.csv")
os.makedirs(output_path, exist_ok = True)
combined_df.to_csv(output_file, index = False)

topic_info_to_save = topic_info

if merge:
    if new_topics:
        topic_info_to_save = topic_info[topic_info["topic"].isin(new_topics)]
    else:
        topic_info_to_save = None

if topic_info_to_save is not None:
    topic_info_to_save.to_csv((os.path.join(output_path, f"topic_info_2025_{testrun}.csv")), index = False)
    # get_gemini_labels((os.path.join(output_path, f"topic_info_2025_{testrun}.csv")),language="german")

print("done")