from crontab import CronTab
import os
import shlex

project_root = os.path.dirname(os.path.abspath(__file__))

# Your deploy script (adjust name/path if different)
script_to_run = os.path.join(project_root, "deploy-gh-pages.sh")

# Log file for cron output
log_file = os.path.join(project_root, "gh-pages-deploy.log")

cron = CronTab(user=True)

def build_cmd() -> str:
    # Run script from project root so relative paths (if any) work
    cmd = f"cd {shlex.quote(project_root)} && /bin/bash {shlex.quote(script_to_run)}"
    return f"/bin/bash -lc {shlex.quote(cmd)} >> {shlex.quote(log_file)} 2>&1"

# Remove any previous jobs with same comment
cron.remove_all(comment="deploy_gh_pages_weekly")

job = cron.new(
    command=build_cmd(),
    comment="deploy_gh_pages_weekly",
)

# Every Monday 03:30
job.setall("30 3 * * 1")

cron.write()

print("Deploy job installed.")
print(f"Script: {script_to_run}")
print(f"Log: {log_file}")
