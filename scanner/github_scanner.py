
import httpx
import time
import hashlib
import sys
sys.path.insert(0, "/data/data/com.termux/files/home/ali")
from memory.db import save_project, save_claim, init_db

import os
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

def get_headers():
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}"
    }

def search_github(query, per_page=20):
    url = "https://api.github.com/search/repositories"
    params = {
        "q": query + " language:rust language:go stars:>50",
        "sort": "stars",
        "order": "desc",
        "per_page": per_page
    }
    try:
        r = httpx.get(url, headers=get_headers(), params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("items", [])
        print(f"GitHub search error: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    return []

def check_releases(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=10)
        if r.status_code != 200:
            return False, False, None
        releases = r.json()
        if not releases:
            return False, False, None
        has_binary = False
        binary_src = None
        for release in releases[:3]:
            for asset in release.get("assets", []):
                name = asset["name"].lower()
                if not any(name.endswith(x) for x in [".sha256",".sig",".asc",".txt",".md"]):
                    has_binary = True
                    binary_src = f"release asset: {asset['name']}"
                    break
        return True, has_binary, binary_src
    except Exception as e:
        print(f"Release error: {e}")
        return False, False, None

def check_integrity_proof(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=10)
        if r.status_code != 200:
            return False
        for release in r.json()[:3]:
            for asset in release.get("assets", []):
                name = asset["name"].lower()
                if any(name.endswith(x) for x in [".sig",".asc","_evidence","_pack",".pem"]):
                    return True
    except:
        pass
    return False

def get_owner_email(owner):
    url = f"https://api.github.com/users/{owner}"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()
            email = data.get("email") or ""
            if email and "noreply" not in email:
                return email, data.get("name") or owner
    except:
        pass
    return None, owner

def run_github_scanner():
    init_db()
    queries = ["cli tool release", "binary cli rust", "command line tool go"]
    found = []
    
    for query in queries:
        print(f"GitHub scanning: {query}")
        repos = search_github(query)
        
        for repo in repos:
            full_name = repo.get("full_name", "")
            owner = repo.get("owner", {}).get("login", "")
            name = repo.get("name", "")
            stars = repo.get("stargazers_count", 0)
            
            if repo.get("archived") or repo.get("fork"):
                continue
            
            time.sleep(0.5)
            has_releases, has_binary, binary_src = check_releases(owner, name)
            already_proof = check_integrity_proof(owner, name)
            
            if not has_binary or already_proof:
                continue
            
            project_id = hashlib.md5(full_name.encode()).hexdigest()[:12]
            save_project(project_id, full_name, repo.get("html_url"), "qualified")
            
            if has_releases:
                save_claim(project_id, "has_release", "Project publishes releases", True, "GitHub releases page")
            if has_binary:
                save_claim(project_id, "has_binary", "Project distributes binaries", True, binary_src or "release assets")
            if not already_proof:
                save_claim(project_id, "no_integrity_proof", "No integrity proof detected", True, "release asset scan")
            
            email, contact_name = get_owner_email(owner)
            
            found.append({
                "project_id": project_id,
                "full_name": full_name,
                "url": repo.get("html_url"),
                "stars": stars,
                "language": repo.get("language"),
                "email": email,
                "owner": contact_name
            })
            
            print(f"  QUALIFIED: {full_name} stars={stars} email={email}")
        
        time.sleep(2)
    
    print(f"\nTotal qualified: {len(found)}")
    for r in found[:10]:
        print(f"  {r['full_name']} | email={r['email']}")
    
    return found

if __name__ == "__main__":
    run_github_scanner()
