import time
import random
import base64
import requests
import json
import os
import hashlib

# --- Configuration ---
GITHUB_TOKEN = "your_github_token_here"  # GitHub Personal Access Token
REPO_OWNER = "your_github_username"      # Repository owner
REPO_NAME = "your_repository_name"       # Repository name
FILE_PATH = "README.md"                   # File to modify
BRANCH = "main"                           # Target branch
PHRASES_FILE = "phrases.txt"              # File containing phrases

LINE_TO_MODIFY = 3                         # Line number to modify (1-indexed)
INTERVAL_HOURS = 12                        # Update interval in hours
COMMIT_MESSAGE = "Automated update"       # Commit message

PREFERE_GITHUB = True                      # Prioritize GitHub version if different

API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

interval_seconds = INTERVAL_HOURS * 3600

# Fetches the file content from GitHub
def get_github_file():
    response = requests.get(API_URL, headers=HEADERS, params={"ref": BRANCH})
    if response.status_code != 200:
        print("Error fetching file from GitHub:", response.text)
        return None, None
    file_info = response.json()
    content_b64 = file_info.get("content", "")
    if not content_b64:
        print("No content found in GitHub response.")
        return None, None
    content_decoded = base64.b64decode(content_b64).decode("utf-8")
    return content_decoded.splitlines(keepends=True), file_info["sha"]

# Hashes file content to check for changes
def hash_file_content(content):
    return hashlib.sha256("".join(content).encode("utf-8")).hexdigest()

# Checks if local file matches GitHub version
def get_file_lines():
    github_lines, github_sha = get_github_file()
    
    if not os.path.exists(FILE_PATH):
        print(f"Local file {FILE_PATH} not found, retrieving from GitHub...")
        return github_lines, github_sha

    with open(FILE_PATH, "r", encoding="utf-8") as f:
        local_lines = f.readlines()

    if github_lines and hash_file_content(local_lines) != hash_file_content(github_lines):
        print("Local file differs from GitHub version.")
        if PREFERE_GITHUB:
            print("Prioritizing GitHub version...")
            return github_lines, github_sha
        else:
            print("Keeping local version...")
            return local_lines, github_sha

    return local_lines, github_sha

while True:
    try:
        # Load phrases from PHRASES_FILE
        with open(PHRASES_FILE, "r", encoding="utf-8") as f:
            phrases = [line.strip() for line in f if line.strip()]

        if not phrases:
            print(f"No phrases found in {PHRASES_FILE}.")
            time.sleep(interval_seconds)
            continue

        lines, current_sha = get_file_lines()
        if lines is None or current_sha is None:
            time.sleep(interval_seconds)
            continue

        if len(lines) < LINE_TO_MODIFY:
            print(f"The file {FILE_PATH} does not contain at least {LINE_TO_MODIFY} lines.")
        else:
            old_phrase = lines[LINE_TO_MODIFY - 1].strip()
            possible_phrases = [phrase for phrase in phrases if phrase != old_phrase]
            new_phrase = old_phrase if not possible_phrases else random.choice(possible_phrases)
            lines[LINE_TO_MODIFY - 1] = new_phrase + "\n"
            new_content = "".join(lines)
            print(f"Modified line {LINE_TO_MODIFY} (old: {old_phrase}) to: {new_phrase}")

            # Encode new content in base64
            new_content_b64 = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")

            # Prepare data for GitHub update
            data = {
                "message": COMMIT_MESSAGE,
                "content": new_content_b64,
                "sha": current_sha,
                "branch": BRANCH
            }

            # Send PUT request to update the file
            put_response = requests.put(API_URL, headers=HEADERS, data=json.dumps(data))
            if put_response.status_code in [200, 201]:
                print("Successfully pushed update to GitHub.")
                with open(FILE_PATH, "w", encoding="utf-8") as f:
                    f.write(new_content)
            else:
                print("Error pushing update to GitHub:", put_response.text)
    except Exception as e:
        print("Error processing update:", e)

    # Wait for the next update interval
    time.sleep(interval_seconds)
