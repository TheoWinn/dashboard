import argparse
import subprocess
import sys
import os
from pathlib import Path
import json
from datetime import date


STATE_PATH = Path("orphan/make_live/pipeline_state.json")


def run_step(description, command, cwd=None, env=None):
    print("\n" + "=" * 60)
    print(f"### Running: {description} ###")
    print("=" * 60 + "\n")

    cmd_str = " ".join(map(str, command))
    print(f"Command: {cmd_str}")

    if cwd:
        print(f"Working Directory: {cwd}")

    try:
        subprocess.run(command, check=True, cwd=cwd, env=env)
        print(f"\n[SUCCESS] {description} completed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {description} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred during {description}: {e}")
        return False


def load_cutoff(default_cutoff: str) -> str:
    if STATE_PATH.exists():
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data.get("cutoff", default_cutoff)
    return default_cutoff


def save_cutoff(new_cutoff: str) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"cutoff": new_cutoff}, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Full Processing Pipeline: Download -> Transcribe -> Cluster -> Match"
    )

    parser.add_argument("--cutoff", type=str, default="2025-01-01",
                        help="Cutoff date in YYYY-MM-DD format")
    parser.add_argument("--test-mode", action="store_true")
    parser.add_argument("--many-videos", action="store_true")
    parser.add_argument("--skip-download-videos", action="store_true")
    parser.add_argument("--skip-download-protocols", action="store_true")
    parser.add_argument("--skip-transcribe", action="store_true")
    parser.add_argument("--skip-cluster", action="store_true")
    parser.add_argument("--skip-match", action="store_true")
    parser.add_argument("--skip-bert", action="store_true")
    parser.add_argument("--skip-database", action="store_true")

    args = parser.parse_args()

    # Use stored cutoff (unless you override by passing --cutoff explicitly)
    cutoff_str = load_cutoff(args.cutoff)
    # validate format early
    _ = date.fromisoformat(cutoff_str)

    project_root = os.getcwd()

    # 1. Download YouTube Videos
    if not args.skip_download_videos:
        cmd = [sys.executable, "download_youtube.py", "--cutoff", cutoff_str]
        if args.test_mode:
            cmd.append("--test-mode")
        if args.many_videos:
            cmd.append("--many-videos")
        if not run_step("YouTube Download", cmd, cwd=os.path.join(project_root, "youtube", "src")):
            sys.exit(1)

    # 2. Download Bundestag Protocols
    if not args.skip_download_protocols:
        cmd = [sys.executable, "download_cut.py", "--start", cutoff_str]
        if not run_step("Bundestag Protocol Download", cmd, cwd=os.path.join(project_root, "bundestag", "src")):
            sys.exit(1)

    # 3. Transcribe Audio
    if not args.skip_transcribe:
        if not run_step("Transcribe Talkshows", ["bash", "run_whisperx.sh"], cwd=project_root):
            sys.exit(1)
        if not run_step("Transcribe Bundestag", ["bash", "run_whisperx.sh", "--bundestag"], cwd=project_root):
            sys.exit(1)

    # 4. Cluster/Clean Transcripts
    if not args.skip_cluster:
        if not run_step("Cluster Talkshow Transcripts",
                        [sys.executable, "clean_aligned_transcripts.py"],
                        cwd=os.path.join(project_root, "youtube", "src")):
            sys.exit(1)
        if not run_step("Cluster Bundestag Transcripts",
                        [sys.executable, "clean_aligned_transcripts.py", "--bundestag"],
                        cwd=os.path.join(project_root, "youtube", "src")):
            sys.exit(1)

    # 5. Match Transcripts to Protocols
    if not args.skip_match:
        if not run_step("Matching Pipeline",
                        [sys.executable, "ma_utils.py"],
                        cwd=os.path.join(project_root, "matching", "src")):
            sys.exit(1)

    # 6. Bert
    if not args.skip_bert:
        if not run_step("Bert with Gemini Labels",
                        [sys.executable, "extract_topics.py"],
                        cwd=os.path.join(project_root, "topicmodelling")):
            sys.exit(1)

    # 7. Write to Database
    if not args.skip_database:
        log_path = Path("topicmodelling/data/latest_files_bert.json")
        if not log_path.exists():
            raise FileNotFoundError(f"Log file not found: {log_path}")

        log_file = json.loads(log_path.read_text(encoding="utf-8"))
        if log_file.get("inserted"):
            print("Log file says files are inserted already. Stopping.")
            sys.exit(1)

        while log_file["speeches_file"]:
            speech = log_file["speeches_file"][0]
            info = log_file["info_file"][0]

            if info != "none":
                p = Path(info)
                labeled_info = f"{p.stem}_gemini_labeled{p.suffix}"
                info_path = f"../topicmodelling/data/raw_topics/{labeled_info}"
            else:
                info_path = "none"

            if speech != "none":
                speech_path = f"../topicmodelling/data/raw_topics/{speech}"
            else:
                speech_path = "none"

            cmd = [sys.executable, "insert.py",
                   "--input-path", speech_path,
                   "--label-path", info_path,
                   "--youtube"]

            if not run_step("Insert into DB", cmd, cwd=os.path.join(project_root, "database")):
                sys.exit(1)

            log_file["speeches_file"].pop(0)
            log_file["info_file"].pop(0)
            log_file["inserted"] = (len(log_file["speeches_file"]) == 0)
            log_path.write_text(json.dumps(log_file, ensure_ascii=False, indent=4), encoding="utf-8")

        print("Everything inserted successfully")

    print("DONE!!")

    # Update cutoff only if everything above succeeded
    save_cutoff(date.today().isoformat())


if __name__ == "__main__":
    main()
