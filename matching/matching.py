import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher

def preprocess_text(text):
    """
    Cleans and standardizes text for comparison.
    
    - Converts text to lowercase.
    - Removes punctuation and numbers.
    - Strips extra whitespace.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Removes anything that is not a letter or whitespace
    text = re.sub(r'[^a-z\s]', '', text)
    # Replaces multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def find_best_speech_match(transcript, speeches, top_n=3):
    """
    Finds the best speech match for a given transcript using a two-step process.

    Args:
        transcript (str): The transcribed text from a video.
        speeches (list[str]): A list of the official speech texts.
        top_n (int): The number of top candidates to check with the detailed comparison.
                       A smaller number is faster.

    Returns:
        tuple: A tuple containing the best matching speech text and its
               similarity score (from 0.0 to 1.0). Returns (None, 0.0) if no match is found.
    """
    if not transcript or not speeches:
        return None, 0.0

    # === Step 1: Preprocessing ===
    # Clean the input transcript and all official speeches.
    processed_transcript = preprocess_text(transcript)
    processed_speeches = [preprocess_text(s) for s in speeches]
    
    # Add the transcript to the list for vectorization
    all_texts = processed_speeches + [processed_transcript]

    # === Step 2: Indexing and Candidate Search (TF-IDF) ===
    # Create TF-IDF vector representations (the "fingerprints") for all texts.
    # We use German stop words to improve relevance.
    try:
        tfidf_vectorizer = TfidfVectorizer(stop_words='german')
        tfidf_matrix = tfidf_vectorizer.fit_transform(all_texts)
    except ValueError:
        # This can happen if all texts are empty after preprocessing (e.g., only stop words)
        return None, 0.0

    # Separate the speeches' matrix from the transcript's vector
    speeches_matrix = tfidf_matrix[:-1]
    transcript_vector = tfidf_matrix[-1]

    # Calculate the cosine similarity between the transcript and all speeches.
    # This is a very fast way to find texts with similar important words.
    similarities = cosine_similarity(transcript_vector, speeches_matrix)

    # Get the indices of the 'top_n' most similar speeches.
    # argsort() gives the indices from least to most similar, so we reverse it with [::-1]
    candidate_indices = similarities[0].argsort()[::-1][:top_n]

    # === Step 3: Detailed Comparison (SequenceMatcher) ===
    # Now, we only compare the transcript against the best few candidates.
    best_match = None
    best_score = 0.0

    for index in candidate_indices:
        candidate_speech = speeches[index]
        # We use the *original* (unprocessed) texts here for the most accurate score.
        score = SequenceMatcher(None, transcript, candidate_speech).ratio()
        
        print(f"Checking candidate #{index+1}... SequenceMatcher Score: {score:.4f}")

        if score > best_score:
            best_score = score
            best_match = candidate_speech
            
    return best_match, best_score

# === How to Use It ===
    # 3. Find the best match!
    #matched_speech, similarity_score = find_best_speech_match(video_transcript, official_speeches)

    # 4. Display the results
    #if matched_speech:
    #     print("\n--- Match Found! ---")
    #     print(f"Best match score: {similarity_score:.4f}")
    #     print(f"\nTranscript:\n'{video_transcript}'")
    #     print(f"\nMatched Official Speech:\n'{matched_speech}'")
    # else:
    #     print("No suitable match was found.")