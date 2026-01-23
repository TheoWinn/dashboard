from crontab import CronTab
import os
import shlex
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.abspath(__file__))  

file_to_run = os.path.join(project_root, "Pipeline.py")   
log_file = os.path.join(project_root, "cron_log.txt")
uv_executable = "/home/adminuser/.local/bin/uv"

cron = CronTab(user=True)

def build_cmd(extra_args: str = "") -> str:
    cmd = f"cd {shlex.quote(project_root)} && {shlex.quote(uv_executable)} run python -u {shlex.quote(file_to_run)} {extra_args}".strip()
    return f"/bin/bash -lc {shlex.quote(cmd)} >> {shlex.quote(log_file)} 2>&1"

cron.remove_all(comment="pipeline_weekly")

weekly_job = cron.new(
    command=build_cmd(""),  
    comment="pipeline_weekly",
)

weekly_job.setall("30 3 * * 0")  # Sunday 03:30 am

cron.write()
print("Weekly job installed.")
print(f"Log: {log_file}")
