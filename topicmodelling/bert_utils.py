from sklearn.metrics.pairwise import cosine_similarity
from bertopic import BERTopic
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
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import pandas as pd
import unicodedata
import re

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

class OnlineRepresentativeTracker:
    def __init__(self, top_n=3, decay=1.0):
        self.top_n = top_n
        # Storage: {topic_id: {'docs': [], 'embeddings': []}}
        self.reps = {}
        # Optional: Decay old representatives' influence if needed
        self.decay = decay 

    def update(self, docs, embeddings, topics):
        """
        Updates the representative documents for the given batch.
        """
        unique_topics = set(topics)
        
        for topic in unique_topics:
            if topic == -1: continue # Skip outliers
            
            # 1. Extract current batch data for this topic
            indices = [i for i, t in enumerate(topics) if t == topic]
            batch_docs = [docs[i] for i in indices]
            batch_embs = [embeddings[i] for i in indices]
            
            # 2. Retrieve existing champions
            if topic not in self.reps:
                self.reps[topic] = {'docs': [], 'embeddings': []}
            
            current_docs = self.reps[topic]['docs']
            current_embs = self.reps[topic]['embeddings']
            
            # 3. Merge Pool (Old Champions + New Contenders)
            pool_docs = current_docs + batch_docs
            pool_embs = current_embs + batch_embs
            
            # If we don't have enough data to prune yet, just save and continue
            if len(pool_docs) <= self.top_n:
                self.reps[topic]['docs'] = pool_docs
                self.reps[topic]['embeddings'] = pool_embs
                continue

            # 4. Calculate "Local" Centroid of the pool
            # This approximates the topic center based on the best docs seen so far
            pool_embs_array = np.vstack(pool_embs)
            centroid = np.mean(pool_embs_array, axis=0).reshape(1, -1)
            
            # 5. Find the documents closest to this centroid
            sims = cosine_similarity(pool_embs_array, centroid).flatten()
            
            # Get indices of top_n highest similarity
            best_indices = np.argsort(sims)[-self.top_n:][::-1]
            
            # 6. Update Champions
            self.reps[topic]['docs'] = [pool_docs[i] for i in best_indices]
            self.reps[topic]['embeddings'] = [pool_embs[i] for i in best_indices]

    def get_representatives(self):
        """Returns a dict of {topic: [doc1, doc2...]}"""
        return {k: v['docs'] for k, v in self.reps.items()}

class NamedGroup(BaseModel):
    group_name: str       
    items: List[str]     

class OutputCollection(BaseModel):
    groups: List[NamedGroup]

def get_gemini_labels(csv_path,n_words: int =3,language="german"):

    file_name = os.path.basename(csv_path)

    input_Data=pd.read_csv(csv_path)
    input_data=input_Data["Representation"] #input_Data["Representation"].head(20)

    client = OpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    completion = client.beta.chat.completions.parse(
        model="gemini-2.5-flash", # Using a model optimized for Structured Outputs
        messages=[
            {
                "role": "system", 
                "content": "You are a data organizer. Analyze the list of lists provided by the user. Give each sub-list a short, descriptive name based on its contents."
            },
            {
                "role": "user", 
                "content": f"Here is the input data: {input_data} for the description use a maximum of {n_words} words. Do this in {language}."
            },
        ],
        response_format=OutputCollection, # Pass the Pydantic class here
    )

    parsed_response = completion.choices[0].message.parsed

    group_names = [group.group_name for group in parsed_response.groups]
    for group_name in group_names:
        print(group_name)
    output_df = pd.DataFrame(input_Data)
    output_df["Gemini_Label"] = group_names
    output_df.to_csv("gemini_labeled_"+file_name,index=False)
    return group_names

class CachedEmbeddingBackend:
    """
    Wrapper that caches embeddings so we don't compute them twice 
    (once for partial_fit, once for rep_tracker).
    """
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.current_embeddings = None

    def encode(self, documents, verbose=False):
        # We assume the loop calls encode manually first, 
        # so here we just return what we already calculated.
        if self.current_embeddings is not None and len(documents) == len(self.current_embeddings):
            return self.current_embeddings
        
        # Fallback if called unexpectedly
        return self.embedding_model.encode(documents, show_progress_bar=verbose)

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

# Apply to your dataframe

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