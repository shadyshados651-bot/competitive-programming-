#!/usr/bin/env python3
"""
Sync Codeforces solutions to GitHub repository.
Automatically fetches accepted solutions from Codeforces and commits them.
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
import subprocess
import sys

# Configuration
CF_HANDLE = os.getenv('CF_HANDLE')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_DIR = os.getcwd()

def get_cf_submissions(handle):
    """Fetch all accepted submissions from Codeforces API."""
    url = f"https://codeforces.com/api/user.status?handle={handle}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK':
            print(f"Error from Codeforces API: {data.get('comment', 'Unknown error')}")
            return []
        
        # Filter only accepted submissions
        accepted = [sub for sub in data['result'] 
                   if sub.get('verdict') == 'OK']
        return accepted
    
    except requests.RequestException as e:
        print(f"Error fetching from Codeforces: {e}")
        return []

def organize_solutions(submissions):
    """Organize submissions by contest and problem."""
    solutions = {}
    
    for sub in submissions:
        contest_id = sub['contestId']
        problem_idx = sub['problem']['index']
        problem_name = sub['problem']['name']
        
        contest_key = f"{contest_id}"
        
        if contest_key not in solutions:
            solutions[contest_key] = {}
        
        if problem_idx not in solutions[contest_key]:
            solutions[contest_key][problem_idx] = {
                'name': problem_name,
                'submissions': []
            }
        
        solutions[contest_key][problem_idx]['submissions'].append(sub)
    
    return solutions

def save_solution(contest_id, problem_idx, submission):
    """Save a solution to the repository."""
    source_code = submission.get('sourceCode', '')
    language = submission['programmingLanguage']
    
    # Determine file extension
    extensions = {
        'GNU C++': '.cpp',
        'GNU C++11': '.cpp',
        'GNU C++14': '.cpp',
        'GNU C++17': '.cpp',
        'GNU C++20': '.cpp',
        'Python': '.py',
        'Python 3': '.py',
        'Java': '.java',
        'C#': '.cs',
        'JavaScript': '.js',
    }
    
    ext = extensions.get(language, '.txt')
    
    # Create directory structure: solutions/contestId/problemIdx/
    solution_dir = Path(REPO_DIR) / 'solutions' / str(contest_id) / problem_idx
    solution_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    filename = f"solution{ext}"
    filepath = solution_dir / filename
    
    if filepath.exists():
        return False  # Already exists, skip
    
    filepath.write_text(source_code)
    return True

def commit_changes(message):
    """Commit changes to git."""
    try:
        subprocess.run(['git', 'add', '.'], cwd=REPO_DIR, check=True, 
                      capture_output=True)
        subprocess.run(['git', 'commit', '-m', message], cwd=REPO_DIR, 
                      check=True, capture_output=True)
        subprocess.run(['git', 'push'], cwd=REPO_DIR, check=True, 
                      capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")
        return False

def main():
    """Main sync function."""
    if not CF_HANDLE:
        print("Error: CF_HANDLE environment variable not set")
        sys.exit(1)
    
    print(f"Syncing Codeforces solutions for {CF_HANDLE}...")
    
    # Fetch submissions
    submissions = get_cf_submissions(CF_HANDLE)
    if not submissions:
        print("No accepted submissions found or API error occurred")
        return
    
    print(f"Found {len(submissions)} accepted submissions")
    
    # Organize solutions
    solutions = organize_solutions(submissions)
    
    # Save solutions
    new_files = 0
    for contest_id, problems in solutions.items():
        for problem_idx, problem_data in problems.items():
            # Use the most recent submission for each problem
            latest_sub = max(problem_data['submissions'], 
                           key=lambda x: x['creationTimeSeconds'])
            if save_solution(contest_id, problem_idx, latest_sub):
                new_files += 1
    
    if new_files > 0:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Sync Codeforces solutions: {new_files} new file(s) added ({timestamp})"
        
        if commit_changes(message):
            print(f"Successfully synced {new_files} new solutions!")
        else:
            print("Sync completed but git commit failed")
    else:
        print("No new solutions to sync")

if __name__ == '__main__':
    main()
