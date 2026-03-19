
import smtplib
import sys
from email.mime.text import MIMEText
from datetime import datetime
sys.path.insert(0, "/data/data/com.termux/files/home/ali")
from memory.db import can_contact, save_contact, mark_sent

GMAIL_USER = "iscproof@gmail.com"
GMAIL_PASS = ""  # set via env  # App password buraya

def build_subject(project_name):
    return f"question about {project_name} releases?"

def build_message(project_name, repo_url, language=None):
    lang_note = ""
    if language and language.lower() in ["rust", "go", "c", "c++", "zig"]:
        lang_note = f" ({language})"
    
    msg = f"""Hello,

I was looking at {project_name}{lang_note} and noticed that binaries are published without a verifiable integrity proof.

With BuildSeal it is possible to generate an offline-verifiable evidence pack for each release — binding the artifact to the exact repo and commit, signed with Ed25519.

Here is an example for a similar project: https://buildseal.io/demo-rust.html

Let me know if you would like a CI snippet for {project_name}.

Ali"""
    return msg

def send_mail(to_address, subject, body, dry_run=False):
    if dry_run:
        print(f"[DRY RUN] To: {to_address}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        return True, "dry_run_id"
    
    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = to_address
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, to_address, msg.as_string())
        
        message_id = f"msg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        return True, message_id
    except Exception as e:
        print(f"Mail error: {e}")
        return False, None

def contact_project(project_id, project_name, repo_url, language, email, owner_name, dry_run=False):
    if not email:
        print(f"  SKIP: no email for {project_name}")
        return False
    
    if not can_contact(email, "email"):
        print(f"  SKIP: cannot contact {email}")
        return False
    
    subject = build_subject(project_name)
    body = build_message(project_name, repo_url, language)
    
    contact_id = save_contact(project_id, owner_name, "email", email)
    
    success, message_id = send_mail(email, subject, body, dry_run=dry_run)
    
    if success:
        mark_sent(contact_id, project_id, "email", subject, body, message_id or "")
        print(f"  SENT: {email} ({project_name})")
        return True
    
    return False

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    print(f"Mailer ready. dry_run={dry_run}")
    print(f"From: {GMAIL_USER}")
    
    test_subject = build_subject("example-rust-cli")
    test_body = build_message("example-rust-cli", "https://codeberg.org/Buildseal/example-rust-cli", "Rust")
    print(f"\nTest message:\n{test_subject}\n{test_body}")
