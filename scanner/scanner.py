
import httpx
import time
import hashlib
from datetime import datetime
import sys
sys.path.insert(0, "/data/data/com.termux/files/home/ali")
from memory.db import save_project, save_claim, can_contact

CODEBERG_TOKEN = ""

def get_headers():
    h = {"Accept": "application/json"}
    if CODEBERG_TOKEN:
        h["Authorization"] = f"token {CODEBERG_TOKEN}"
    return h

def search_repos(query, limit=50):
    url = "https://codeberg.org/api/v1/repos/search"
    params = {"q": query, "limit": limit, "sort": "stars", "order": "desc"}
    try:
        r = httpx.get(url, headers=get_headers(), params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", [])
    except Exception as e:
        print(f"Search error: {e}")
    return []

def check_releases(full_name):
    url = f"https://codeberg.org/api/v1/repos/{full_name}/releases"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=10)
        if r.status_code != 200:
            return False, False, None
        releases = r.json()
        if not releases:
            return False, False, None
        has_binary = False
        binary_source = None
        for release in releases[:3]:
            for asset in release.get("assets", []):
                name = asset["name"].lower()
                if not any(name.endswith(x) for x in [".sha256", ".sig", ".asc", ".pem", ".txt"]):
                    has_binary = True
                    binary_source = f"release asset: {asset['name']}"
                    break
        return True, has_binary, binary_source
    except Exception as e:
        print(f"Release check error: {e}")
        return False, False, None

def check_ci(full_name):
    paths = [".gitea/workflows", ".github/workflows", ".woodpecker.yml", ".woodpecker"]
    for path in paths:
        url = f"https://codeberg.org/api/v1/repos/{full_name}/contents/{path}"
        try:
            r = httpx.get(url, headers=get_headers(), timeout=5)
            if r.status_code == 200:
                return True, path
        except:
            pass
    return False, None

def check_integrity_proof(full_name):
    url = f"https://codeberg.org/api/v1/repos/{full_name}/releases"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=10)
        if r.status_code != 200:
            return False
        releases = r.json()
        for release in releases[:3]:
            for asset in release.get("assets", []):
                name = asset["name"].lower()
                if any(name.endswith(x) for x in [".sig", ".asc", ".pem", "_evidence", "_pack"]):
                    return True
    except:
        pass
    return False

def get_owner_email(owner):
    url = f"https://codeberg.org/api/v1/users/{owner}"
    try:
        r = httpx.get(url, headers=get_headers(), timeout=5)
        if r.status_code == 200:
            data = r.json()
            email = data.get("email", "")
            if email and "noreply" not in email:
                return email, data.get("full_name", owner)
    except:
        pass
    return None, owner

def score_repo(repo, has_releases, has_binary, has_ci, already_has_proof):
    score = 0
    if already_has_proof:
        return 0
    if has_releases:
        score += 3
    if has_binary:
        score += 3
    if has_ci:
        score += 2
    stars = repo.get("stars_count", 0)
    if stars >= 50:
        score += 2
    elif stars >= 20:
        score += 1
    lang = (repo.get("language") or "").lower()
    if lang in ["rust", "go", "c", "c++", "zig"]:
        score += 1
    return score

def run_scanner():
    from memory.db import init_db
    init_db()
    
    queries = ["rust cli", "go cli tool", "command line", "binary release", "cli utility"]
    found = []
    
    for query in queries:
        print(f"Scanning: {query}")
        repos = search_repos(query)
        
        for repo in repos:
            full_name = repo.get("full_name", "")
            stars = repo.get("stars_count", 0)
            owner = repo.get("owner", {}).get("login", "")
            
            if stars < 5:
                continue
            
            if repo.get("archived") or repo.get("fork"):
                continue
            
            time.sleep(0.3)
            has_releases, has_binary, binary_src = check_releases(full_name)
            has_ci, ci_path = check_ci(full_name)
            already_has_proof = check_integrity_proof(full_name)
            
            score = score_repo(repo, has_releases, has_binary, has_ci, already_has_proof)
            
            if score < 3:
                continue
            
            project_id = hashlib.md5(full_name.encode()).hexdigest()[:12]
            save_project(project_id, full_name, repo.get("html_url", ""), "qualified")
            
            if has_releases:
                save_claim(project_id, "has_release", "Project publishes releases", True, "release page")
            if has_binary:
                save_claim(project_id, "has_binary", "Project distributes binary artifacts", True, binary_src or "release assets")
            if has_ci:
                save_claim(project_id, "has_ci", "Project uses CI", True, ci_path)
            if not already_has_proof:
                save_claim(project_id, "no_integrity_proof", "No integrity proof detected in releases", True, "release asset scan")
            
            email, name = get_owner_email(owner)
            
            found.append({
                "project_id": project_id,
                "full_name": full_name,
                "url": repo.get("html_url"),
                "stars": stars,
                "language": repo.get("language"),
                "score": score,
                "email": email,
                "owner": name
            })
            
            print(f"  QUALIFIED: {full_name} score={score} email={email}")
        
        time.sleep(1)
    
    found.sort(key=lambda x: x["score"], reverse=True)
    print(f"\nTotal qualified: {len(found)}")
    for r in found[:20]:
        print(f"  {r['full_name']} | score={r['score']} | email={r['email']}")
    
    return found

if __name__ == "__main__":
    run_scanner()
