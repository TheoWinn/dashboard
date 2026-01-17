from bertopic import BERTopic
import pandas as pd
from sentence_transformers import SentenceTransformer
import glob
import os
from datetime import datetime
import numpy as np
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import unicodedata
import re
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
from umap import UMAP
from sklearn.feature_extraction.text import CountVectorizer
from pandas.errors import EmptyDataError

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

class NamedGroup(BaseModel):
    group_name: str       
    items: List[str]     

class OutputCollection(BaseModel):
    groups: List[NamedGroup]

def get_gemini_labels(csv_path, n_words: int = 3, language="german"):
    
    # Load Data
    input_Data = pd.read_csv(csv_path)
    
    # 1. Convert to a standard list to avoid Pandas string truncation
    all_representations = input_Data["Representation"].tolist()
    
    env_path = find_dotenv()
    load_dotenv(env_path)
    client = OpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    all_labels = []
    batch_size = 20  # Process 20 topics at a time to ensure quality and prevent errors

    # 2. Loop through data in batches
    for i in range(0, len(all_representations), batch_size):
        batch = all_representations[i : i + batch_size]
        print(f"Processing batch {i} to {i + len(batch)}...")

        try:
            completion = client.beta.chat.completions.parse(
                model="gemini-2.5-flash",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert political analyst. "
                            "Interpret lists of keywords from German political debates. "
                            "Identify the specific underlying political issue for each list. "
                            "Avoid generic labels."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Analyze these {len(batch)} lists of keywords: {batch}\n\n" # Passing a Python list prints fully
                            f"Provide a descriptive label for each list in {language}. "
                            f"Max {n_words} words per label. "
                            "Return exactly one label per input list."
                        )
                    },
                ],
                response_format=OutputCollection,
            )

            parsed_response = completion.choices[0].message.parsed
            batch_labels = [group.group_name for group in parsed_response.groups]

            # Safety check: Ensure we got the same number of labels as inputs
            if len(batch_labels) != len(batch):
                print(f"Warning: Batch mismatch! Sent {len(batch)}, got {len(batch_labels)}")
                # Fill missing with "Error" or pad to avoid crashing
                batch_labels.extend(["Error"] * (len(batch) - len(batch_labels)))
            
            all_labels.extend(batch_labels)

        except Exception as e:
            print(f"Error processing batch {i}: {e}")
            all_labels.extend(["Error_API_Fail"] * len(batch))

    # 3. Assign back to DataFrame
    output_df = input_Data.copy()
    output_df["Gemini_Label"] = all_labels

    in_path = Path(csv_path)
    out_path = in_path.with_name(in_path.stem + "_gemini_labeled" + in_path.suffix)
    
    output_df.to_csv(out_path, index=False)
    return all_labels


def clean_encoding_artifacts(text):
    if not isinstance(text, str):
        return ""
    
    # 1. Normalize Unicode (Fixes \xa0, \u200b, ligatures like 'fi')
    # NFKC = Normalization Form Compatibility Composition
    text = unicodedata.normalize('NFKC', text)
    
    # 2. Hard-replace the specific punctuation that NFKC leaves alone
    # Replace different dashes with standard hyphen
    text = re.sub(r'[–—]', '-', text)
    # Replace smart quotes with standard quotes
    text = re.sub(r'[“”„«»]', '"', text)
    text = re.sub(r"[‘’‚]", "'", text)
    
    # 3. CRITICAL: Remove Soft Hyphens (\xad)
    # They are invisible but will destroy word frequencies
    text = text.replace('\xad', '')
    
    # 4. Collapse whitespace
    # Turns "Hello   \n  World" into "Hello World"
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def sliding_window(text, chunk_size=500, overlap=50):
    """
    Splits text into chunks of approx 'chunk_size' words (not exact tokens, but safe proxy).
    """
    words = text.split()
    # If text is short enough, return it as a single chunk
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    # Create chunks with overlap
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        # Stop if we've reached the end
        if i + chunk_size >= len(words):
            break
    return chunks

def extract_topics(talkshow_path = "../youtube/data/clustered/talkshow_clustered/*.csv", 
                   bundestag_path = "../matching/data/matched/*.csv", 
                   output_path = "data/raw_topics", 
                   model_path = "models", 
                   merge = True
                   ):

    ### SETUP ###

    os.environ["HF_HUB_HTTP_TIMEOUT"] = "60"         
    os.environ["HF_HUB_ETAG_TIMEOUT"] = "60"

    ### STOP-WORDS ###

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

    ### DATA PRE-Processing ###

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

    today = datetime.now().date()

    ## BUNDESTAG

    bundestag_dfs = []

    for file in glob.glob(bundestag_path):
        filename = os.path.basename(file)
        if filename not in log_files:
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
            # append to meta list
            meta.append([filename, today])

    if bundestag_dfs:
        # concatenated df
        bundestag_df_full = pd.concat(bundestag_dfs, ignore_index=True)
        # remove short text (under 200 characters)
        bundestag_df_short = bundestag_df_full[bundestag_df_full['text'].str.strip().str.len() > 200]
        # split into smaller paragraphs
        bundestag_df_split = bundestag_df_short.assign(text=bundestag_df_short['text'].str.split(r'\n\n+')).explode('text')
        # chunk text into lists if too long
        bundestag_fixed = bundestag_df_split.copy()
        bundestag_fixed['text'] = bundestag_fixed['text'].apply(lambda x: sliding_window(str(x)))
        # each chunk own line
        bundestag_fixed = bundestag_fixed.explode('text').reset_index(drop=True)

    ## TALKSHOWS

    talkshow_dfs = []

    for file in glob.glob(talkshow_path):
        filename = os.path.basename(file)
        if filename not in log_files:
            df = pd.read_csv(file)
            df["date"] = extract_date_from_filename(file)
            df["source"] = "talkshow"
            df["filename"] = os.path.basename(file)
            talkshow_dfs.append(df)
            # append to meta list
            meta.append([filename, today])

    # save metadata
    if meta:
        pd.DataFrame(meta, columns=["filename", "date_processed"]).to_csv(meta_file, index=False, header=False)

    if talkshow_dfs:
        # concatenated df
        talkshow_df_full =pd.concat(talkshow_dfs, ignore_index=True)
        # remove short text (under 200 characters)
        talkshow_df_short = talkshow_df_full[talkshow_df_full['text'].str.strip().str.len() > 200]
        # chunk text into lists if too long
        talkshow_df_short['text'] = talkshow_df_short['text'].apply(sliding_window)
        # each chunk own line
        talkshow_df_ready = talkshow_df_short.explode('text').dropna(subset=['text']).reset_index(drop=True)

    ## COMBINE

    if (not talkshow_dfs) and (not bundestag_dfs):
        print("WARNING: no new files found. Stopping further proceedings.")
        return None, None

    # combine dfs
    raw_combined_df= pd.concat([bundestag_fixed, talkshow_df_ready], ignore_index=True)
    # shuffle
    combined_df = raw_combined_df.sample(frac=1, random_state=42).reset_index(drop=True)
    # clean encoding artifacts
    combined_df_clean = combined_df.copy()
    combined_df_clean["text"] = combined_df_clean["text"].apply(clean_encoding_artifacts)
    # transform into list
    docs= combined_df_clean["text"].astype(str).tolist()

    print(combined_df_clean["source"].value_counts())

    ### BERTopic ###

    embedding_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2").to("cuda")

    new_topics = set()

    if merge:
        # load in last model as base model
        with open(f"{model_path}/last_model.txt", "r", encoding="utf-8") as f:
            base_model_name = f.read().strip()
        base_model_path = f"{model_path}/{base_model_name}" 
        base_model = BERTopic.load(base_model_path, embedding_model=embedding_model)
        # train new model
        weekly_model = BERTopic(
            embedding_model = embedding_model,
            umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine'),
            vectorizer_model=vectorizer_model
        )
        weekly_model.fit(docs)
        # merge models
        topic_model = BERTopic.merge_models([base_model, weekly_model], min_similarity=0.7)
        # sort new docs in topics
        topics, probs = topic_model.transform(docs)
        # check for new topics
        base_topics = set(base_model.get_topic_info()["Topic"])
        merged_topics = set(topic_model.get_topic_info()["Topic"])
        new_topics = merged_topics - base_topics
    else:
        # train model & sort data into topics
        topic_model = BERTopic(
            embedding_model = embedding_model,
            umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine'),
            vectorizer_model=vectorizer_model
        )
        topics, probs = topic_model.fit_transform(docs)

    # save model
    model_dir = Path(model_path)
    model_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    model_name = f"bertopic_{now}"
    model_path = model_dir / model_name
    topic_model.save(str(model_path)) 
    print(f"Saved model to: {model_path}")
    with open(model_path, "w", encoding="utf-8") as f:
        f.write(model_name)

    print(topic_model.get_topic_info().head(20))

    # append topics to speeches
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

    # save speeches with topics
    speeches_filename = f"topic_speeches_{now}.csv"
    output_file = os.path.join(output_path, speeches_filename)
    os.makedirs(output_path, exist_ok = True)
    combined_df.to_csv(output_file, index = False)

    # filter topic_info if necessary (i.e. topics are new)
    topic_info_to_save = topic_info
    if merge:
        if new_topics:
            topic_info_to_save = topic_info[topic_info["topic"].isin(new_topics)]
        else:
            topic_info_to_save = None
    
    # generate label and save topic_info if necessary (i.e. topics are new)
    info_filename = None
    if topic_info_to_save is not None:
        info_filename = f"topic_info_{now}.csv"
        topic_info_to_save.to_csv((os.path.join(output_path, info_filename)), index = False)
        get_gemini_labels((os.path.join(output_path, info_filename)), language="german")
        print("New topics with labels saved")

    print("Done")

    return speeches_filename, info_filename