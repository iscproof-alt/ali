import os
import sqlite3

DB_PATH = "/tmp/ali.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT,
            project_url TEXT,
            project_status TEXT DEFAULT 'new',
            last_analyzed_at TEXT,
            success_state INTEGER DEFAULT 0,
            failure_state INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS contacts (
            contact_id TEXT PRIMARY KEY,
            project_id TEXT,
            contact_name TEXT,
            contact_channel TEXT,
            contact_address TEXT,
            contact_status TEXT DEFAULT 'not_contacted',
            first_contact_at TEXT,
            last_contact_at TEXT,
            followup_sent INTEGER DEFAULT 0,
            do_not_contact INTEGER DEFAULT 0,
            bounce_type TEXT,
            reply_state TEXT DEFAULT 'none',
            attempt_count INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            project_id TEXT,
            claim_type TEXT,
            claim_text TEXT,
            observed_value INTEGER,
            evidence_source TEXT,
            evidence_time TEXT,
            verified INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id TEXT PRIMARY KEY,
            contact_id TEXT,
            project_id TEXT,
            channel TEXT,
            subject TEXT,
            message_body TEXT,
            message_id TEXT,
            sent_at TEXT,
            reply_received INTEGER DEFAULT 0,
            reply_at TEXT,
            followup_allowed INTEGER DEFAULT 1,
            followup_sent INTEGER DEFAULT 0,
            last_outcome TEXT DEFAULT 'sent'
        );
    """)
    conn.commit()
    conn.close()
    print('DB initialized')

def can_contact(contact_address, channel):
    conn = get_conn()
    row = conn.execute("""
        SELECT do_not_contact, contact_status, attempt_count
        FROM contacts
        WHERE contact_address = ? AND contact_channel = ?
    """, (contact_address, channel)).fetchone()
    conn.close()
    if not row:
        return True
    do_not_contact, status, attempts = row
    if do_not_contact:
        return False
    if status in ('rejected', 'do_not_contact', 'completed'):
        return False
    if attempts >= 2:
        return False
    return True

def save_project(project_id, name, url, status='new'):
    from datetime import datetime
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT OR IGNORE INTO projects
        (project_id, project_name, project_url, project_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (project_id, name, url, status, now, now))
    conn.execute("UPDATE projects SET project_status=?, updated_at=? WHERE project_id=?", (status, now, project_id))
    conn.commit()
    conn.close()

def save_claim(project_id, claim_type, claim_text, observed, source, verified=True):
    import uuid
    from datetime import datetime
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO claims
        (claim_id, project_id, claim_type, claim_text, observed_value, evidence_source, evidence_time, verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), project_id, claim_type, claim_text, int(observed), source, now, int(verified)))
    conn.commit()
    conn.close()

def save_contact(project_id, name, channel, address):
    import uuid
    from datetime import datetime
    conn = get_conn()
    contact_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT OR IGNORE INTO contacts
        (contact_id, project_id, contact_name, contact_channel, contact_address, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (contact_id, project_id, name, channel, address, now))
    conn.commit()
    row = conn.execute('SELECT contact_id FROM contacts WHERE contact_address=? AND contact_channel=?', (address, channel)).fetchone()
    conn.close()
    return row[0] if row else contact_id

def mark_sent(contact_id, project_id, channel, subject, body, message_id):
    import uuid
    from datetime import datetime
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO interactions
        (interaction_id, contact_id, project_id, channel, subject, message_body, message_id, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), contact_id, project_id, channel, subject, body, message_id, now))
    conn.execute("""
        UPDATE contacts SET contact_status='sent', last_contact_at=?,
        attempt_count=attempt_count+1,
        first_contact_at=COALESCE(first_contact_at, ?)
        WHERE contact_id=?
    """, (now, now, contact_id))
    conn.commit()
    conn.close()

def mark_rejected(contact_address, channel):
    conn = get_conn()
    conn.execute("UPDATE contacts SET contact_status='rejected', do_not_contact=1 WHERE contact_address=? AND contact_channel=?", (contact_address, channel))
    conn.commit()
    conn.close()

def get_conn_public():
    return get_conn()
