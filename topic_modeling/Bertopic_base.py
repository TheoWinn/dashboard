from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
import pandas as pd
#Choice: Lemmatization with simple CountVectorizer and BERTopic or MMR (maximally marginal relevance)
#

docs=pd.read_csv('data/14,12 Milliarden Euro für das Bildungs- und Familienressort_clustered_matched.csv')["protokoll_text"].tolist()
initial_words=open('stp_wrds.txt', 'r', encoding='utf-8').read().splitlines()

speech_fillers = [
    # Hesitations & Interjections
    "äh", "ähm", "hm", "tja", "pff", "naja", "oh", "ah", "okay", "ok", 
    "genau", "richtig", "klar", "gut", 
    
    # Common Speech Particles (Modalpartikel) - highly frequent in speech!
    "halt", "eben", "mal", "ja", "doch", "wohl", "schon", "eigentlich", 
    "irgendwie", "sowieso", "sozusagen", "quasi", "praktisch", "buchstäblich",
    "glaube", "meine", "finde", "denke", "sagen", "gesagt", # "ich glaube", "ich sage mal"
    
    # Phrases often transcribed as single tokens or short meaningless connectors
    "ding", "sache", "zeug", "bisschen", "bissel", "paar",
    "natürlich", "selbstverständlich", "absolut", "definitiv",
    "ganz", "gar", "überhaupt", "immer", "nie", "vielleicht"
]

stop_words=set(speech_fillers+initial_words)

vectorizer_model = CountVectorizer(
    stop_words=stop_words,  # You can load a German list here (see below)
    min_df=1,             # Ignore words that appear in fewer than 10 documents
    ngram_range=(1, 2)     # Allow phrases like "Guten Morgen"
)


# 2. Initialize BERTopic
topic_model = BERTopic(
    language="german",                # Loads a multilingual model supporting German
    vectorizer_model=vectorizer_model # Applies the cleaning logic defined above
)

# 3. Fit (Feed it the raw, cased, full-sentence text)
topics, probs = topic_model.fit_transform(docs)
topic_model.get_topic_info()
topic_model.generate_topic_labels(nr_words=4,topic_prefix=False)