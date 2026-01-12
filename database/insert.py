from db_utils import fill_db
from dotenv import load_dotenv
import os
import argparse

load_dotenv()
DB_URL = os.environ["DATABASE_URL"]

parser = argparse.ArgumentParser()
parser.add_argument("--input-path", type=str, default="../topicmodelling/data/raw_topics/topics_representations_2025_youtube.csv",
                    help="Path to csv file")
parser.add_argument("--youtube", action="store_true",
                    help="Use if the BERT model was run using only transcriptions from youtube videos.")
args = parser.parse_args()

input_path = args.input_path
youtube = args.youtube

fill_db(DB_URL, input_path, youtube)
