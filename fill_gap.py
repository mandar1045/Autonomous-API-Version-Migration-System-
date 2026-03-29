import os
import random
import subprocess
from datetime import datetime, timedelta

def run_cmd(cmd, env=None):
    res = subprocess.run(cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return res.stdout.strip()

# Git config
run_cmd("git config user.name 'mandar1045'")
run_cmd("git config user.email 'mandar1045@users.noreply.github.com'")

# Get existing commit dates
existing_dates_str = run_cmd("git log --since='2025-12-01' --until='2025-12-20' --date=short --format='%ad' | sort | uniq")
existing_dates = set([d.strip() for d in existing_dates_str.split("\n") if d.strip()])

print(f"Existing dates with commits in range: {existing_dates}")

start_date = datetime(2025, 12, 1, 10, 0, 0)
end_date = datetime(2025, 12, 20, 10, 0, 0)

current_date = start_date
total_commits = 0
env = os.environ.copy()

print(f"Generating random commits from {start_date.date()} to {end_date.date()}...")

with open("contribution_history.log", "a") as f:
    f.write(f"\nGap filler initialized on {datetime.now()}.\n")

while current_date <= end_date:
    date_str = current_date.strftime("%Y-%m-%d")
    
    if date_str in existing_dates:
        print(f"Skipping {date_str} (already has commits)")
        current_date += timedelta(days=1)
        continue
        
    commits_today = random.randint(10, 19)
    
    for i in range(commits_today):
        minute_offset = random.randint(0, 10 * 60)
        commit_time = current_date + timedelta(minutes=minute_offset)
        iso_time = str(commit_time)
        
        env['GIT_AUTHOR_DATE'] = iso_time
        env['GIT_COMMITTER_DATE'] = iso_time
        
        with open("contribution_history.log", "a") as f:
            f.write(f"System gap fill entry for {iso_time}\n")
            
        run_cmd("git add contribution_history.log", env)
        run_cmd(f"git commit -m \"System history fill for {current_date.date()} #{i+1}\"", env)
        
        total_commits += 1
        
    print(f"Generated {commits_today} commits for {current_date.date()} (Total so far: {total_commits})")
            
    current_date += timedelta(days=1)

print(f"Finished generating {total_commits} commits. Pushing to remote...")
res_main = subprocess.run("git push -uf origin main", shell=True)
print("Push complete.")
