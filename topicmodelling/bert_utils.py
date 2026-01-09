from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import pandas as pd

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