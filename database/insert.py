from db_utils import fill_db, rebuild_db
from dotenv import load_dotenv
import os
import argparse

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

parser = argparse.ArgumentParser()
parser.add_argument("--input-path", type=str, default="../topicmodelling/data/raw_topics/topics_representations_2025.csv",
                    help="Path to csv file with speeches")
parser.add_argument("--label-path", type=str, default="../topicmodelling/data/raw_topics/gemini_labeled_topic_info_2025.csv",
                    help="Path to csv file with topics")                   
parser.add_argument("--youtube", action="store_true",
                    help="Use if the BERT model was run using only transcriptions from youtube videos.")
parser.add_argument("--rebuild", action="store_true",
                    help="Use if database should be rebuild from scratch (just for testing)")
args = parser.parse_args()

input_path = args.input_path
label_path = args.label_path
youtube = args.youtube

if args.rebuild:
    rebuild_db(DB_URL, input_path, label_path, youtube)
else:
    fill_db(DB_URL, input_path, label_path, youtube)
