import pandas as pd

# df = pd.read_csv("gemini_labeled_topic_info_2025_leonie2.csv")
# df = pd.read_csv("data/gemini_labeled_topic_info_2025.csv")
# df = pd.read_csv("data/raw_topics/topic_info_2025_leonie3_gemini_labeled.csv")
dfnew = pd.read_csv("data/raw_topics/topic_info_2025_leonie5.csv")
print(dfnew.head(20))
dfold = pd.read_csv("data/raw_topics/topic_info_2025_leonie4.csv")
print(dfold.head(20))
new = set(dfnew["topic"])
old = set(dfold["topic"])
print(old-new)
print(new-old)