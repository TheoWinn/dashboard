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
file_to_run = os.path.join(make_live_dir, "hello.py")

# Path for the log file
log_file = os.path.join(make_live_dir, "cron_log.txt")

# 2. Access cron
cron = CronTab(user=True)

# 3. Define the command (The Robust Fix)
# We wrap everything in "sh -c" so we catch shell errors (like 'cd' failing)
# We add "-u" to python for unbuffered output
command_string = f"cd {project_root} && {python_executable} -u {file_to_run}"
full_command = f"/bin/sh -c '{command_string}' > {log_file} 2>&1"

# 4. Create job
cron.remove_all(comment="My daily hello job") 
job = cron.new(command=full_command, comment="My daily hello job")

# 5. Schedule (Every minute for testing, change to "0 17 * * *" for 5pm later)
job.setall("2 14 * * *")

# 6. Save
cron.write()

print("Job created!")
print(f"Log file will be at: {log_file}")
print("Wait 1 minute, then run: cat " + log_file)

# check if job ran: sudo service cron status
# check output: cat and output_dir









########### Archive #######################

# from crontab import CronTab
# import os

# # 1. Setup paths relative to this script location
# # Current script is in: .../dashboard/orphan/make_live/cron.py
# script_dir = os.path.dirname(os.path.abspath(__file__))

# # Calculate path to project root (dashboard/) by going up 2 levels from script_dir
# project_root = os.path.dirname(os.path.dirname(script_dir))

# # Path to your virtual environment python
# # We join project_root with ".venv/bin/python" (Linux standard)
# python_executable = os.path.join(project_root, ".venv", "bin", "python")

# # Path to the file we want to run (next to this script)
# file_to_run = os.path.join(script_dir, "hello.py")

# # 2. Access cron
# cron = CronTab(user=True)

# # 3. Define the command
# # We added "cd {project_root} &&" so the script runs as if you were in the root folder.
# # This is helpful if your future scripts need to access other folders like 'data' or 'bundestag'.
# command = f"cd {project_root} && {python_executable} -u {file_to_run} >> {script_dir}/cron_log.txt 2>&1"

# # 4. Create job
# # Remove old job if it exists to avoid duplicates
# cron.remove_all(comment="My daily hello job") 
# job = cron.new(command=command, comment="My daily hello job")

# # 5. Schedule 0: min hour *(each day of the month) *(of every month) *(everyday of the week)
# job.setall("50 13 * * *")

# # 6. Save
# cron.write()

# print(f"Job created!")
# print(f"Python used: {python_executable}")
# print(f"Script target: {file_to_run}")
# # to check if sucsessful, run "cat orphan/make_live/cron_log.txt" in terminal