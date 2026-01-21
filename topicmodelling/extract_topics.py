from bert_utils import extract_topics
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--talkshow-path", type=str, default="../matching/data/matched/*.csv",
                    help="path to talkshow data")
parser.add_argument("--bundestag-path", type=str, default="../youtube/data/clustered/bundestag_clustered/*.csv",
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
speeches_new, info_new = extract_topics(talkshow_path=talkshow_path,
                                bundestag_path=bundestag_path,
                                output_path=output_path,
                                model_path=model_path,
                                merge=merge
                                )
if speeches_new is None:
    speeches_new = "none"
if info_new is None:
    info_new = "none"
# read in old log file is exists
log_path = Path("data/latest_files_bert.json")
old_log = None
if log_path.exists():
    with open(log_path, "r", encoding="utf-8") as f:
        old_log = json.load(f)
    if old_log.get("inserted"):
        old_log = None
# if there are still files that need to be inserted, only append new files, otherwise overwrite with new files
if old_log is not None:
    speeches_old = old_log.get("speeches_file")
    info_old = old_log.get("info_file")
    speeches_old.append(speeches_new)
    info_old.append(info_new)
    speeches = speeches_old
    info = info_old
    print("Appended new files to old files that have not been inserted to DB yet.")
else:
    speeches = [speeches_new]
    info = [info_new]
    print("Overwritten already inserted files.")
# write new log file
logfile = {"speeches_file": speeches,
           "info_file": info,
           "inserted": False}
with open(log_path, "w", encoding="utf-8") as f:
    json.dump(logfile, f, ensure_ascii=False, indent=4)
print(f"Wrote names of new files to {log_path}")
