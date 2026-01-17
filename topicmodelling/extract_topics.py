from bert_utils import extract_topics
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--talkshow-path", type=str, default="../youtube/data/clustered/talkshow_clustered/*.csv",
                    help="path to talkshow data")
parser.add_argument("--bundestag-path", type=str, default="../matching/data/matched/*.csv",
                    help="path to bundestag data")
parser.add_argument("--output-path", type=str, default="data/raw_topics",
                    help="path to output")
parser.add_argument("--model-path", type=str, default="models",
                    help="path to models")                   
parser.add_argument("--new", action="store_true",
                    help="new model will be run, otherwise model will be merged to last model")
args = parser.parse_args()
talkshow_path = args.talkshow_path
bundestag_path = args.bundestag_path
output_path = args.output_path
model_path = args.model_path
merge = not args.new
speeches, info = extract_topics(talkshow_path=talkshow_path,
                                bundestag_path=bundestag_path,
                                output_path=output_path,
                                model_path=model_path,
                                merge=merge
                                )
logfile = {"speeches_file": speeches,
           "info_file": info}
with open("data/latest_files_bert.json", "w", encoding="utf-8") as f:
    json.dump(logfile, f, ensure_ascii=False, indent=4)
print("Wrote names of new files to 'data/latest_files_bert.json'")
