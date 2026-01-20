import os
from bert_utils import get_gemini_labels
print(api_key)
output_path = "data/raw_topics"
get_gemini_labels((os.path.join(output_path, "topic_info_2025.csv")),language="german")
