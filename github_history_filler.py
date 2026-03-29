import os
import random
import subprocess
from datetime import datetime, timedelta

def run_cmd(cmd, env=None):
    subprocess.run(cmd, shell=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Git config
run_cmd("git config user.name 'mandar1045'")
run_cmd("git config user.email 'mandar1045@users.noreply.github.com'")

# User requested from Feb 22 to today
start_date = datetime(2026, 2, 22, 10, 0, 0)
end_date = datetime(2026, 3, 12, 10, 0, 0)

current_date = start_date
total_commits = 0
env = os.environ.copy()

print("Starting to generate random commits from {} to {}...".format(start_date.date(), end_date.date()))

with open("contribution_history.log", "w") as f:
    f.write("Feb 22+ contribution history log initialized.\n")

while current_date <= end_date:
    # User requested 30-40 commits per day
    commits_today = random.randint(30, 40)
    
    for i in range(commits_today):
        minute_offset = random.randint(0, 10 * 60)
        commit_time = current_date + timedelta(minutes=minute_offset)
        iso_time = str(commit_time)
        
        env['GIT_AUTHOR_DATE'] = iso_time
        env['GIT_COMMITTER_DATE'] = iso_time
        
        with open("contribution_history.log", "a") as f:
            f.write(f"Daily update entry for {iso_time}\n")
            
        run_cmd("git add contribution_history.log", env)
        run_cmd(f"git commit -m \"System update for {current_date.date()} #{i+1}\"", env)
        
        total_commits += 1
        
    print(f"Generated {commits_today} commits for {current_date.date()} (Total so far: {total_commits})")
            
    current_date += timedelta(days=1)

print(f"Finished generating {total_commits} random commits. Please manually cherry-pick your latest commits and push.")
