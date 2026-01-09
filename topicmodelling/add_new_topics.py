from bertopic import BERTopic
from river import cluster, stream
import pandas as pd
import numpy as np
import os
from datetime import datetime
from bert_utils import get_gemini_labels

topic_model.hdbscan_model.model.fading_factor = 0.001 
topic_model.hdbscan_model.model.cleanup_interval = 1000

# --- 2. LOAD NEW DATA ---
new_df = pd.read_csv("new_data_2025_03.csv")
new_docs = new_df["text"].astype(str).tolist()
new_docs_prefixed = [f"passage: {d}" for d in new_docs]

# --- 3. LOAD THE EXISTING MODEL ---
print("Loading model...")
topic_model = BERTopic.load("my_online_model")

# --- 4. UPDATE THE MODEL (Learn) ---
print("Updating model with new data...")
topic_model.partial_fit(new_docs_prefixed)

# --- 5. INFERENCE (Label the new data) ---
topics, probs = topic_model.transform(new_docs_prefixed)

new_df["topic"] = topics

# --- 6. SAVE EVERYTHING ---

topic_model.save(f"Bertopic_{datetime.today().strftime('%Y-%m-%d')}", serialization="pickle")

# 2. Save the results for this batch
new_df.to_csv(f"processed_batch_{datetime.today().strftime('%Y-%m-%d')}.csv", index=False)

# 3. Export the NEW Topic Definitions (Words might have changed!)
topic_info = topic_model.get_topic_info()
topic_info.to_csv(f"topic_definitions_{datetime.today().strftime('%Y-%m-%d')}.csv", index=False)

print("Update complete. Model saved for next batch.")