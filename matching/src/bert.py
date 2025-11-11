import pandas as pd
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from bertopic.representation import KeyBERTInspired
import warnings
import os
from sklearn.feature_extraction.text import CountVectorizer
warnings.filterwarnings('ignore')


# ==============================================================================
# My Notes
# ==============================================================================
# can smo give feedback to my matching output? ne
# we can finetune with openai. Money from marc? 
# Bert läuft jetzt nur über die transcripte. ist das ok?
# brauchen noch einen Folder für topic modelling 
# sollte ein bert nicht über den ganzen corpus laufen? Sonst haben wir ja pro späre unterschiedliche vectore? dann ist das eine große tabelle aber mit handle dran, ob die quelle BT oder TS is
#
# Model:
# lOOP DAZU, dass der input path nicht gehartcoded ist
# custom stopwörter müssen noch entfernt werden
# what happend to the speeches "jetzt der nächste redner?" werden speeches rausgeworfen? (müssten 77 haben max)welche werden rausgerechnet, sind das auch hoffentlich nur die uninformativen und warum werden einige rausgerechne?
# each speech is assigned one topic. is that what we want? 
#Bert nochmal mit den speeches laufen lassen 
# Stoppwärter wie "jetzt" sollten nicht drin sein, aber wenn wir die hart-coden, kommen halt andere stopwords rein
# Bert: Kontrollieren, ob für kathrin (SPD, line 8) die zeiten und die themen grob stimmen 
# warum regierung in 2 topics
# Andere representations von dem Bert holen
# 

# ==============================================================================
# Output interpretation
# ==============================================================================

"""
BERT MODEL INTERPRETATION
How to understand the topics.csv:
What we have now with the model (see matching/data/matched date_matched_topics.csv)
1. speech_duration_minutes: The length of the speech in minutes. Calculated from (transcript_end - transcript_start) / 60
2. topic: The numeric identifier for the topic assigned to this speech. Start from 0. Topic -1 represents outliers
3. topic_name: This is the full topic name that BERTopic creates. It starts with the topic number and includes the top keywords that define this topic.
f.e. 9_sozialstaat_sozialstaates_reformen_reform is topic sozialstaat
4. topic_keywords: The top 3 most important keywords that represent this topic
5. topic_probability: The confidence score that this speech belongs to Topic (f.e. to topic 9)

Example interpretation in full context: 
look at line 9, speech from Kathrin Michel, SPD. What the model tells us ist: 
This is a 3.4-minute speech that discusses welfare state reforms (Topic 9). The BERTopic model is 40% confident 
that this speech is about welfare state reforms, based on the keywords:
sozialstaat (welfare state), sozialstaates, and reformen (reforms).

TOPIC STATS INTERPRETATION
How to understand the topic_stats.csv:
topic: The topic number assigned by BERTopic.
topic_keywords: The top 3 characteristic keywords of the topic, found by the model
Total_Minutes: Sum of speech durations in this topic cluster.
Avg_Minutes_Per_Speech: Calculated as total time divided by number of speeches.
Num_Speeches: The number of speeches assigned to this topic cluster
Sample_Speakers: Up to 3 speaker identifiers from speeches in this topic
Percentage_of_Total_Time: % of total speech time spent on this topic (excluding outliers).

Example interpretation in full context:
look at the first line. What the topic_stats.csv tells us here is: 
Topic 0 covers government proposals for 2026 ("regierungsentwurf, 2026, jetzt"). 
It was discussed in 12 speeches, taking a total of 56.5 minutes (23.3% of all speaking time). 
Main contributors include SPEAKER_11, SPEAKER_02, and SPEAKER_14.
"""
# ==============================================================================
# Path stuff
# ==============================================================================
INPUT_FILE = 'matching/data/matched/26-09-2025_matched.csv'
OUTPUT_FILE = 'matching/data/matched/26-09-2025_matched_topics.csv'

# ==============================================================================
# STEP 1: Load Data
# ==============================================================================
print("="*80)
print("\n[1/8] Loading data...")
# Check if file exists
if not os.path.exists(INPUT_FILE):
    print(f"ERROR: File not found at {INPUT_FILE}")
    print(f"Current working directory: {os.getcwd()}")
    exit(1)

# Load CSV
df = pd.read_csv(INPUT_FILE)
print(f"Loaded {len(df)} speeches")

# Display columns
print(f"\nAvailable columns: {df.columns.tolist()}")

# Calculate speech duration in minutes
df['speech_duration_minutes'] = (df['transcript_end'] - df['transcript_start']) / 60
print(f"Calculated speech durations")

# Extract documents for analysis
docs = df['protokoll_text'].fillna('').tolist() #i only use the speeches (from BT protokolls for topic modelling. Thats up for discussion tho
print(f" Prepared {len(docs)} documents for topic modeling")

# Display sample
print(f"\nSample data:")
print(df[['transcript_speaker', 'speech_duration_minutes']].head(3))

# ==============================================================================
# STEP 2: Create Embeddings
# ==============================================================================
print("\n" + "="*80)
print("[2/8] Creating embeddings for  text...")
print("="*80)

# Use multilingual model optimized for German
embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print(f"Model: {embedding_model}")

print("\nEncoding documents (this may take a few minutes)...")
embeddings = embedding_model.encode(docs, show_progress_bar=True)
print(f"Created embeddings with shape: {embeddings.shape}")

# ==============================================================================
# STEP 3: Initialize BERTopic Model
# ==============================================================================
print("\n" + "="*80)
print("[3/8] Initializing BERTopic model...")
print("="*80)

# Use KeyBERTInspired for better topic word representation
representation_model = KeyBERTInspired()


# Create BERTopic model following BERTopic documentation
topic_model = BERTopic(
    language='german',                          # Optimize for German
    embedding_model=embedding_model,            # Use our multilingual model
    representation_model=representation_model,  # Better coherence
    min_topic_size=2,                          # Minimum 2 speeches per topic (small dataset)
    nr_topics='auto',                          # Auto-detect optimal number of topics
    calculate_probabilities=True,              # Calculate topic probabilities
    verbose=True
)
print(" BERTopic model initialized")
print(f"  - Language: German")
print(f"  - Min topic size: 2")
print(f"  - Representation: KeyBERTInspired")

# ==============================================================================
# STEP 4: Fit Model and Transform Documents
# ==============================================================================
print("\n" + "="*80)
print("[4/8] Fitting BERTopic model and extracting topics...")
print("="*80)

print("This may take a few minutes...")
topics, probs = topic_model.fit_transform(docs, embeddings)
print(f"\n Model fitted successfully")
print(f"Found {len(set(topics))} topics (including outliers)")

# ==============================================================================
# STEP 5: Analyze Topics
# ==============================================================================
print("\n" + "="*80)
print("[5/8] Analyzing discovered topics...")
print("="*80)

# Get topic information
topic_info = topic_model.get_topic_info()
print("\nTopic Overview:")
print(topic_info[['Topic', 'Count', 'Name']])

# Display top keywords for each topic
print("\n" + "-"*80)
print("TOP KEYWORDS PER TOPIC:")
print("-"*80)
for topic_num in topic_info['Topic']:
    if topic_num != -1:  # Skip outlier topic
        words = topic_model.get_topic(topic_num)
        if words:
            print(f"\nTopic {topic_num}:")
            top_words = [f"{word} ({score:.3f})" for word, score in words[:6]]
            print(f"  {', '.join(top_words)}")

# ==============================================================================
# STEP 6: Add Topics to DataFrame
# ==============================================================================
print("\n" + "="*80)
print("[6/8] Adding topic assignments to speeches dataframe...")
print("="*80)

# Add topic information to dataframe
df['topic'] = topics
df['topic_name'] = df['topic'].map(
    lambda x: topic_info[topic_info['Topic']==x]['Name'].values[0] if x in topic_info['Topic'].values else 'Unknown'
)
df['topic_probability'] = [max(prob) if len(prob) > 0 else 0 for prob in probs]

# Get top 3 words for each topic (cleaner than full name)
topic_keywords = {}
for topic_num in topic_info['Topic']:
    if topic_num != -1:
        words = topic_model.get_topic(topic_num)
        if words:
            topic_keywords[topic_num] = ', '.join([word for word, score in words[:3]])
        else:
            topic_keywords[topic_num] = 'No keywords'
    else:
        topic_keywords[topic_num] = 'Outlier'

df['topic_keywords'] = df['topic'].map(topic_keywords)

print(f"Added topic assignments to all {len(df)} speeches")

# Display sample results
print("\nSample speeches with assigned topics:")
sample_cols = ['transcript_speaker', 'speech_duration_minutes', 'topic', 'topic_keywords', 'topic_probability']
print(df[sample_cols].head(10).to_string())

# ==============================================================================
# STEP 7: Calculate Time Per Topic Statistics
# ==============================================================================
print("\n" + "="*80)
print("[7/8] Calculating time spent per topic...")
print("="*80)

# Overall statistics per topic
time_stats = df[df['topic'] != -1].groupby(['topic', 'topic_keywords']).agg({
    'speech_duration_minutes': ['sum', 'mean', 'count'],
    'transcript_speaker': lambda x: ', '.join(x.unique()[:3])  # Show first 3 speakers
}).round(2)

time_stats.columns = ['Total_Minutes', 'Avg_Minutes_Per_Speech', 'Num_Speeches', 'Sample_Speakers']
time_stats = time_stats.sort_values('Total_Minutes', ascending=False)

print("\nTime spent per topic (excluding outliers):")
print(time_stats.to_string())

# Calculate percentage of total time per topic
total_time = df[df['topic'] != -1]['speech_duration_minutes'].sum()
time_stats['Percentage_of_Total_Time'] = (time_stats['Total_Minutes'] / total_time * 100).round(2)

print(f"\nTotal speech time analyzed: {total_time:.2f} minutes ({total_time/60:.2f} hours)")

# ==============================================================================
# STEP 8: Save Results
# ==============================================================================
print("\n" + "="*80)
print("[8/8] Saving results...")
print("="*80)

# Ensure output directory exists
output_dir = os.path.dirname(OUTPUT_FILE)
os.makedirs(output_dir, exist_ok=True)

# Save main results with topics
df.to_csv(OUTPUT_FILE, index=False)
print(f" Saved: {OUTPUT_FILE}")

# Save topic statistics
stats_file = OUTPUT_FILE.replace('.csv', '_topic_stats.csv')
time_stats.to_csv(stats_file)
print(f" Saved: {stats_file}")

# Create visualizations
print("\nCreating visualizations...")

# 1. Topic visualization
try:
    fig = topic_model.visualize_topics()
    viz_path = os.path.join(output_dir, "topic_visualization.html")
    fig.write_html(viz_path)
    print(f"Saved: {viz_path}")
except Exception as e:
    print(f"Could not create topic visualization: {e}")

# 2. Topic barchart
try:
    fig = topic_model.visualize_barchart(top_n_topics=min(10, len(set(topics))-1))
    viz_path = os.path.join(output_dir, "topic_barchart.html")
    fig.write_html(viz_path)
    print(f" Saved: {viz_path}")
except Exception as e:
    print(f"Could not create barchart: {e}")

# 3. Topic hierarchy
try:
    hierarchical_topics = topic_model.hierarchical_topics(docs)
    fig = topic_model.visualize_hierarchy(hierarchical_topics=hierarchical_topics)
    viz_path = os.path.join(output_dir, "topic_hierarchy.html")
    fig.write_html(viz_path)
    print(f" Saved: {viz_path}")
except Exception as e:
    print(f" Could not create hierarchy visualization: {e}")

# 4. Document clusters
try:
    fig = topic_model.visualize_documents(docs, embeddings=embeddings)
    viz_path = os.path.join(output_dir, "document_clusters.html")
    fig.write_html(viz_path)
    print(f" Saved: {viz_path}")
except Exception as e:
    print(f"Could not create document visualization: {e}")

# Save the model
model_path = os.path.join(output_dir, "bertopic_model")
topic_model.save(model_path, serialization="safetensors", save_ctfidf=True, save_embedding_model=embedding_model)
print(f" Saved model: {model_path}")

# ==============================================================================
# FINAL SUMMARY
# ==============================================================================
print("\n" + "="*80)
print("ANALYSIS COMPLETE GOOD JOB!")
print("="*80)

print(f"\nDataset Summary:")
print(f"   Total speeches analyzed: {len(df)}")
print(f"   Topics discovered: {len(set(topics)) - 1} (excluding outliers)")
print(f"   Outliers: {sum(df['topic'] == -1)}")
print(f"   Total speech time: {df['speech_duration_minutes'].sum():.2f} minutes ({df['speech_duration_minutes'].sum()/60:.2f} hours)")
print(f"   Average speech duration: {df['speech_duration_minutes'].mean():.2f} minutes")

print(f"\nOutput Files (saved to {output_dir}):")
print(f"   26-09-2025_matched_topics.csv - Main output with topic assignments")
print(f"   26-09-2025_matched_topics_topic_stats.csv - Time statistics per topic")

