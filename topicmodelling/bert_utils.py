from sklearn.metrics.pairwise import cosine_similarity
from bertopic import BERTopic
import pandas as pd
from sentence_transformers import SentenceTransformer
import glob
import os
from datetime import datetime
from bertopic.vectorizers import OnlineCountVectorizer
from sklearn.decomposition import IncrementalPCA
import numpy as np
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import pandas as pd
import unicodedata
import re
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

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