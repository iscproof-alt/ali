
import sys
import time
import schedule
from datetime import datetime
sys.path.insert(0, "/data/data/com.termux/files/home/ali")
from memory.db import init_db, get_conn
from scanner.github_scanner import run_github_scanner as run_scanner
from mailer.mailer import contact_project

DRY_RUN = "--dry-run" in sys.argv
DAILY_MAIL_LIMIT = 10

def get_todays_sent_count():
    conn = get_conn()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    row = conn.execute("""
        SELECT COUNT(*) FROM interactions
        WHERE sent_at LIKE ? AND channel = 'email'
    """, (f"{today}%",)).fetchone()
    conn.close()
    return row[0] if row else 0

def run_outreach():
    print(f"\n[{datetime.utcnow().isoformat()}] Starting outreach cycle")
    
    sent_today = get_todays_sent_count()
    remaining = DAILY_MAIL_LIMIT - sent_today
    
    if remaining <= 0:
        print(f"Daily limit reached ({DAILY_MAIL_LIMIT}). Skipping.")
        return
    
    print(f"Sent today: {sent_today}, remaining: {remaining}")
    
    # Scanner calistir
    candidates = run_scanner()
    
    sent = 0
    for candidate in candidates:
        if sent >= remaining:
            break
        
        if not candidate.get("email"):
            continue
        
        success = contact_project(
            project_id=candidate["project_id"],
            project_name=candidate["full_name"].split("/")[-1],
            repo_url=candidate["url"],
            language=candidate.get("language"),
            email=candidate["email"],
            owner_name=candidate["owner"],
            dry_run=DRY_RUN
        )
        
        if success:
            sent += 1
            time.sleep(60)  # maillar arasinda 1 dakika bekle
    
    print(f"Cycle complete. Sent: {sent}")

def run_report():
    conn = get_conn()
    print(f"\n=== ALI DAILY REPORT {datetime.utcnow().strftime('%Y-%m-%d')} ===")
    
    total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    qualified = conn.execute("SELECT COUNT(*) FROM projects WHERE project_status='qualified'").fetchone()[0]
    contacted = conn.execute("SELECT COUNT(*) FROM contacts WHERE contact_status='sent'").fetchone()[0]
    replied = conn.execute("SELECT COUNT(*) FROM contacts WHERE reply_state='replied'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM contacts WHERE contact_status='rejected'").fetchone()[0]
    success = conn.execute("SELECT COUNT(*) FROM projects WHERE success_state=1").fetchone()[0]
    
    print(f"Projects scanned:   {total_projects}")
    print(f"Qualified:          {qualified}")
    print(f"Contacted:          {contacted}")
    print(f"Replied:            {replied}")
    print(f"Rejected:           {rejected}")
    print(f"Success:            {success}")
    print("=" * 40)
    conn.close()

if __name__ == "__main__":
    print("ALI v1 starting...")
    init_db()
    
    if "--once" in sys.argv:
        run_outreach()
        run_report()
        sys.exit(0)
    else:
        # Her gece 02:00 UTC tarama
        schedule.every().day.at("02:00").do(run_outreach)
        # Her sabah 07:00 UTC rapor
        schedule.every().day.at("07:00").do(run_report)
        
        print("Scheduler running. Press Ctrl+C to stop.")
        print("Next scan: 02:00 UTC")
        
        # Ilk raporu hemen ver
        run_report()
        print("Entering loop...")
        while True:
            schedule.run_pending()
            time.sleep(60)
            print("Ali tick")
