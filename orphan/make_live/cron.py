from crontab import CronTab
import os

# 1. Setup paths (Absolute & Dynamic)
# Location of THIS script: .../dashboard/orphan/make_live/cron.py
current_script_path = os.path.abspath(__file__)
make_live_dir = os.path.dirname(current_script_path)
orphan_dir = os.path.dirname(make_live_dir)  # .../dashboard/orphan
project_root = os.path.dirname(orphan_dir)    # .../dashboard

# Path to .venv python
python_executable = os.path.join(project_root, ".venv", "bin", "python")

# Path to hello.py (It is in 'orphan/make_live' based on your screenshot)
# IF hello.py IS IN 'orphan', CHANGE THIS TO: os.path.join(orphan_dir, "hello.py")
file_to_run = os.path.join(make_live_dir, "pipeline.py")

# Path for the log file
log_file = os.path.join(make_live_dir, "cron_log.txt")

# 2. Access cron
cron = CronTab(user=True)

# 3. Define the command (The Robust Fix)
# We wrap everything in "sh -c" so we catch shell errors (like 'cd' failing)
# We add "-u" to python for unbuffered output
command_string = f"cd {project_root} && {python_executable} -u {file_to_run}"
full_command = f"/bin/sh -c '{command_string}' >> {log_file} 2>&1"

# 4. Create job
cron.remove_all(comment="My daily hello job") 
job = cron.new(command=full_command, comment="My daily hello job")

# 5. Schedule ("minute hour day week year"
job.setall("27 14 * * *")

# 6. Save
cron.write()

print("Job created!")
print(f"Log file will be at: {log_file}")
print("Wait 5 minutes, then run: cat " + log_file)

# check if job ran: sudo service cron status
# check output: cat and output_dir







