import argparse
import subprocess
import sys
import os
from pathlib import Path
import json

def venv_python(venv_dir: str) -> str:
    venv_dir = Path(venv_dir)
    if os.name == "nt":
        return str(venv_dir / "Scripts" / "python.exe")
    return str(venv_dir / "bin" / "python")

def build_cuda_env_from_venv(venv_py: str) -> dict:
    """
    Computes CUDNN_LIBDIR using the *venv python* and returns an env dict
    with CUDNN_LIBDIR and LD_LIBRARY_PATH updated.
    """
    env = os.environ.copy()

    # Equivalent to your:
    # export CUDNN_LIBDIR=$(python -c "import os, importlib.resources as ir; ...")
    cmd = [
        venv_py,
        "-c",
        "import os, importlib.resources as ir; print(os.fspath(ir.files('nvidia.cudnn')/'lib'))",
    ]
    cudnn_libdir = subprocess.check_output(cmd, text=True).strip()

    env["CUDNN_LIBDIR"] = cudnn_libdir

    old_ld = env.get("LD_LIBRARY_PATH", "")
    # prepend cudnn lib dir (avoid double colons)
    env["LD_LIBRARY_PATH"] = f"{cudnn_libdir}:{old_ld}" if old_ld else cudnn_libdir

    return env

def preflight_transcription(venv_py: str, env: dict) -> bool:
    # 1) confirm we are running the venv python
    cmd1 = [venv_py, "-c", "import sys; print('PYTHON:', sys.executable)"]
    if not run_step("Preflight: Python interpreter", cmd1, env=env):
        return False

    # 2) confirm nvidia.cudnn libs are discoverable
    cmd2 = [venv_py, "-c",
            "import os, importlib.resources as ir; "
            "p = ir.files('nvidia.cudnn')/'lib'; "
            "print('CUDNN_LIBDIR:', os.fspath(p)); "
            "print('EXISTS:', p.exists()); "
            "print('CONTENTS:', [x.name for x in p.iterdir()])"]
    if not run_step("Preflight: nvidia.cudnn lib folder", cmd2, env=env):
        return False

    # 3) confirm torch sees CUDA + cuDNN
    cmd3 = [venv_py, "-c",
            "import os, torch, glob; "
            "print('Torch:', torch.__version__); "
            "print('CUDA build:', torch.version.cuda); "
            "print('CUDA available:', torch.cuda.is_available()); "
            "print('GPU count:', torch.cuda.device_count()); "
            "print('GPU0:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else None); "
            "print('cuDNN:', torch.backends.cudnn.version()); "
            "print('CUDNN_LIBDIR env:', os.environ.get('CUDNN_LIBDIR')); "
            "print('has libcudnn_cnn:', bool(glob.glob(os.environ.get('CUDNN_LIBDIR','') + '/libcudnn_cnn.so*')))"
           ]
    return run_step("Preflight: torch CUDA/cuDNN", cmd3, env=env)


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
    parser.add_argument("--skip-bert", action="store_true", help="Skip Bert step")
    
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
        VENV_py = venv_python("/home/mlci_2025s1_group1/Dashboard/leonie-worktree/.venv")
        transcribe_env = build_cuda_env_from_venv(VENV_py)

        if not preflight_transcription(VENV_py, transcribe_env):
            sys.exit(1)

        # 3a. Talkshows
        cmd_ts = [VENV_py, "transcribe_audio.py"]
        if not run_step("Transcribe Talkshows", cmd_ts, cwd=os.path.join(os.getcwd(), "youtube", "src"), env=transcribe_env):
            sys.exit(1)
            
        # 3b. Bundestag
        cmd_bt = [VENV_py, "transcribe_audio.py", "--bundestag"]
        if not run_step("Transcribe Bundestag", cmd_bt, cwd=os.path.join(os.getcwd(), "youtube", "src"), env=transcribe_env):
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
    if not args.skip_bert:
        cmd = [sys.executable, "extract_topics"]
        if not run_step("Bert with Gemini Labels", cmd, cwd=os.path.join(os.getcwd(), "topicmodelling")):
            sys.exit(1)
    
    # 7. Schreiben in Datenbank
    # no skipping of database inserting

    # read in log file
    log_path = Path("topicmodelling/data/latest_files_bert.json")
    if not log_path.exists():
        raise FileNotFoundError(f"Log file with filenames to insert into database not found: {log_path}")
    with open(log_path, "r", encoding="utf-8") as f:
        log_file = json.load(f)

    # check whether all files are already inserted
    inserted = log_file.get("inserted")
    if inserted:
        print("Log File says files are inserted already. Stopping further proceedings. Check if files are really inserted.")
        sys.exit(1)
    else:

        # step by step insert files and remove from log file if inserted successfully
        while log_file["speeches_file"]:
            # current speech
            speech = log_file["speeches_file"][0]
            info = log_file["info_file"][0]
            print(info)
            p = Path(info)
            labeled_info = f"{p.stem}_gemini_labeled{p.suffix}"
            print(labeled_info)

            speech_path = f"../topicmodelling/data/raw_topics/{speech}"
            info_path = f"../topicmodelling/data/raw_topics/{labeled_info}"

            cmd = [sys.executable, "insert.py", "--input-path", speech_path, "--label-path", info_path, "--youtube"]
            if not run_step("Insert into DB", cmd, cwd=os.path.join(os.getcwd(), "database")):
                sys.exit(1)

            # remove from log 
            log_file["speeches_file"].pop(0)
            log_file["info_file"].pop(0)

            # update inserted flag if queue now empty
            log_file["inserted"] = (len(log_file["speeches_file"]) == 0)

            # write to file
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_file, f, ensure_ascii=False, indent=4)

        print("Everything inserted successfully")
    
    print("DONE!!")
                

if __name__ == "__main__":
    main()