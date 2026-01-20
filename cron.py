from crontab import CronTab
import os

# 1. Setup paths
current_script_path = os.path.abspath(__file__)
make_live_dir = os.path.dirname(current_script_path)
orphan_dir = os.path.dirname(make_live_dir)    
project_root = os.path.dirname(orphan_dir)    

python_executable = os.path.join(project_root, ".venv", "bin", "python")
file_to_run = os.path.join(make_live_dir, "pipeline.py")
log_file = os.path.join(make_live_dir, "cron_log.txt")

cron = CronTab(user=True)

# Build the shell command
def build_cmd(extra_args: str = "") -> str:
    # Added .strip() to ensure clean command
    command_string = f"cd {project_root} && {python_executable} -u {file_to_run} {extra_args}".strip()
    return f"/bin/sh -c '{command_string}' >> {log_file} 2>&1"

# 2. Cleanup existing jobs to avoid duplicates
cron.remove_all(comment="pipeline_daily")
cron.remove_all(comment="pipeline_weekly_including_bert")
cron.remove_all(comment="pipeline_test_manual")  # Remove old test jobs

# ---------------------------------------------------------
# 3. YOUR TEST JOB (16.01.2026, No BERT, No DB)
# ---------------------------------------------------------
test_job = cron.new(
    # Add the specific cutoff date here
    command=build_cmd("--cutoff 2025-01-16 --skip-bert --skip-database"),
    comment="pipeline_test_manual",
)
# Set to run EVERY MINUTE for immediate testing
# ⚠️ Delete this job or comment it out after you verify it works!
test_job.setall("* * * * *") 

# ---------------------------------------------------------
# Standard Jobs (Kept as requested, but currently inactive if testing)
# ---------------------------------------------------------
daily_job = cron.new(
    command=build_cmd("--skip-bert --skip-database"),
    comment="pipeline_daily",
)
daily_job.setall("30 3 * * *")

weekly_job = cron.new(
    command=build_cmd(""),
    comment="pipeline_weekly_including_bert",
)
weekly_job.setall("30 3 * * 0")

cron.write()

print("Jobs updated!")
print(f"Test job created. Check log file in 1 minute: {log_file}")


# check if job ran: sudo service cron status
# check output: cat and output_dir








# from crontab import CronTab
# import os

# # 1. Setup paths (Absolute & Dynamic)
# current_script_path = os.path.abspath(__file__)
# make_live_dir = os.path.dirname(current_script_path)
# orphan_dir = os.path.dirname(make_live_dir)   
# project_root = os.path.dirname(orphan_dir)    

# python_executable = os.path.join(project_root, ".venv", "bin", "python")
# file_to_run = os.path.join(make_live_dir, "pipeline.py")
# log_file = os.path.join(make_live_dir, "cron_log.txt")

# cron = CronTab(user=True)

# # Build the shell command
# def build_cmd(extra_args: str = "") -> str:
#     command_string = f"cd {project_root} && {python_executable} -u {file_to_run} {extra_args}".strip()
#     return f"/bin/sh -c '{command_string}' >> {log_file} 2>&1"

# # Remove old jobs (no dublicates )
# cron.remove_all(comment="pipeline_daily")
# cron.remove_all(comment="pipeline_weekly_including_bert")


# # 1) Daily job: skip BERT, skip writing into pipeline
# daily_job = cron.new(
#     command=build_cmd("--skip-bert --skip-database"),
#     comment="pipeline_daily",
# )
# daily_job.setall("30 3 * * *")


# # 2) Weekly job: run with BERT
# weekly_job = cron.new(
#     command=build_cmd(""),        # no --skip-bert => BERT runs
#     comment="pipeline_weekly_including_bert",
# )
# weekly_job.setall("30 3 * * 0")   # every Sunday at 03:30 

# cron.write()

# print("Jobs created!")
# print(f"Log file: {log_file}")

# # check if job ran: sudo service cron status
# # check output: cat and output_dir







