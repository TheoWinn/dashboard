import argparse
import subprocess
import sys
import os

def run_step(description, command, cwd=None, env=None):
    print("\n" + "="*60)
    print(f"### Running: {description} ###")
    print("="*60 + "\n")
    
    print(f"Command: {" ".join(command)}")
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

def main():
    parser = argparse.ArgumentParser(description="Full Processing Pipeline: Download -> Transcribe -> Cluster -> Match")
    
    # Arguments
    parser.add_argument("--cutoff", type=str, default="2025-01-01",
                        help="Cutoff date in YYYY-MM-DD format (used for both video download and protocol start date)")
    parser.add_argument("--test-mode", action="store_true",
                        help="Enable test mode (runs faster/less data)")
    parser.add_argument("--many-videos", action="store_true",
                        help="Enable many videos mode (leads to longer pauses between downloads to avoid bot detection) and goes through entire playlist instead of skipping after 20 videos were cutoff due to date.")
    parser.add_argument("--skip-download-videos", action="store_true", help="Skip YouTube video download step")
    parser.add_argument("--skip-download-protocols", action="store_true", help="Skip Bundestag protocol download step")
    parser.add_argument("--skip-transcribe", action="store_true", help="Skip transcription step")
    parser.add_argument("--skip-cluster", action="store_true", help="Skip clustering step")
    parser.add_argument("--skip-match", action="store_true", help="Skip matching step")
    
    args = parser.parse_args()
    
    # 1. Download YouTube Videos
    if not args.skip_download_videos:
        cmd = [sys.executable, "download_youtube.py", "--cutoff", args.cutoff]
        if args.test_mode:
            cmd.append("--test-mode")
        if args.many_videos:
            cmd.append("--many-videos")
        if not run_step("YouTube Download", cmd, cwd=os.path.join(os.getcwd(), "youtube", "src")):
            sys.exit(1)

    # 2. Download Bundestag Protocols
    if not args.skip_download_protocols:
        cmd = [sys.executable, "download_cut.py", "--start", args.cutoff]
        if not run_step("Bundestag Protocol Download", cmd, cwd=os.path.join(os.getcwd(), "bundestag", "src")):
            sys.exit(1)

    # 3. Transcribe Audio
    if not args.skip_transcribe:
        # 3a. Talkshows
        cmd_ts = [sys.executable, "transcribe_audio.py"]
        if not run_step("Transcribe Talkshows", cmd_ts, cwd=os.path.join(os.getcwd(), "youtube", "src")):
            sys.exit(1)
            
        # 3b. Bundestag
        cmd_bt = [sys.executable, "transcribe_audio.py", "--bundestag"]
        if not run_step("Transcribe Bundestag", cmd_bt, cwd=os.path.join(os.getcwd(), "youtube", "src")):
            sys.exit(1)

    # 4. Cluster/Clean Transcripts
    if not args.skip_cluster:
        # 4a. Talkshows
        cmd_ts = [sys.executable, "clean_aligned_transcripts.py"]
        if not run_step("Cluster Talkshow Transcripts", cmd_ts, cwd=os.path.join(os.getcwd(), "youtube", "src")):
            sys.exit(1)
            
        # 4b. Bundestag
        cmd_bt = [sys.executable, "clean_aligned_transcripts.py", "--bundestag"]
        if not run_step("Cluster Bundestag Transcripts", cmd_bt, cwd=os.path.join(os.getcwd(), "youtube", "src")):
            sys.exit(1)

    # 5. Match Transcripts to Protocols
    if not args.skip_match:
        cmd = [sys.executable, "ma_utils.py"]
        if not run_step("Matching Pipeline", cmd, cwd=os.path.join(os.getcwd(), "matching", "src")):
            sys.exit(1)

    # 6. Bert
    
    # 7. Schreiben in Datenbank


if __name__ == "__main__":
    main()