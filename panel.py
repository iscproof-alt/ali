from flask import Flask, render_template_string
import sqlite3

app = Flask(__name__)
DB = "/data/data/com.termux/files/home/ali/memory/ali.sqlite"

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ali Panel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#080808;color:#c8c8c8;font-family:monospace;padding:20px}
h1{color:#fff;font-size:18px;margin-bottom:24px;letter-spacing:2px}
h2{color:#4caf50;font-size:12px;letter-spacing:3px;margin:24px 0 12px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}
.stat{background:#0a0a0a;border:1px solid #1a1a1a;padding:16px;border-radius:4px}
.stat-num{font-size:28px;color:#fff;font-weight:700}
.stat-label{font-size:11px;color:#444;letter-spacing:2px;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{color:#333;letter-spacing:2px;padding:8px;border-bottom:1px solid #111;text-align:left}
td{padding:8px;border-bottom:1px solid #0d0d0d;color:#555}
td:first-child{color:#888}
a{color:#4caf50;text-decoration:none}
</style>
</head>
<body>
<h1>ALI CONTROL PANEL</h1>
<div class="stats">
<div class="stat"><div class="stat-num">{{ s.scanned }}</div><div class="stat-label">SCANNED</div></div>
<div class="stat"><div class="stat-num">{{ s.qualified }}</div><div class="stat-label">QUALIFIED</div></div>
<div class="stat"><div class="stat-num">{{ s.contacted }}</div><div class="stat-label">CONTACTED</div></div>
<div class="stat"><div class="stat-num">{{ s.replied }}</div><div class="stat-label">REPLIED</div></div>
<div class="stat"><div class="stat-num">{{ s.rejected }}</div><div class="stat-label">REJECTED</div></div>
<div class="stat"><div class="stat-num">{{ s.success }}</div><div class="stat-label">SUCCESS</div></div>
</div>
<h2>SENT MAILS</h2>
<table>
<tr><th>TO</th><th>SUBJECT</th><th>DATE</th></tr>
{% for r in mails %}
<tr><td>{{ r.addr }}</td><td>{{ r.subj }}</td><td>{{ r.date }}</td></tr>
{% endfor %}
</table>
<h2>PROJECTS</h2>
<table>
<tr><th>PROJECT</th><th>STATUS</th><th>LINK</th></tr>
{% for r in projects %}
<tr><td>{{ r.name }}</td><td>{{ r.status }}</td><td><a href="{{ r.url }}">open</a></td></tr>
{% endfor %}
</table>
</body>
</html>"""

@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    s = {
        "scanned": conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
        "qualified": conn.execute("SELECT COUNT(*) FROM projects WHERE project_status='qualified'").fetchone()[0],
        "contacted": conn.execute("SELECT COUNT(*) FROM contacts WHERE contact_status='sent'").fetchone()[0],
        "replied": conn.execute("SELECT COUNT(*) FROM contacts WHERE reply_state='replied'").fetchone()[0],
        "rejected": conn.execute("SELECT COUNT(*) FROM contacts WHERE contact_status='rejected'").fetchone()[0],
        "success": conn.execute("SELECT COUNT(*) FROM projects WHERE success_state=1").fetchone()[0],
    }
    mails = [{"addr":r[0],"subj":r[1],"date":r[2][:16]} for r in conn.execute("SELECT c.contact_address,i.subject,i.sent_at FROM interactions i JOIN contacts c ON i.contact_id=c.contact_id ORDER BY i.sent_at DESC LIMIT 50").fetchall()]
    projects = [{"name":r[0],"status":r[1],"url":r[2]} for r in conn.execute("SELECT project_name,project_status,project_url FROM projects ORDER BY updated_at DESC LIMIT 50").fetchall()]
    conn.close()
    return render_template_string(HTML, s=s, mails=mails, projects=projects)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
