#!/usr/bin/env python3
"""Conversation-archive exporter from Hermes state.db snapshots (class tool).

Proven on VM906 (2026-09-24): 186 sessions / 20,867 messages exported to a
searchable MD+JSONL archive. Scrubs secrets at export time (see
references/secret-scrub-and-push-protection.md for the incident that shaped
the pattern list).

Copy into a workspace, adjust the CONFIG paths, run:
    python3 export_conversations.py

Outputs (under OUT):
  sessions.jsonl        one row per session (no system_prompt blob; hashed)
  messages.jsonl        all messages, normalized + scrubbed
  memory_records.jsonl  memory_store.db facts (flat; facts has NO bank_id)
  sessions/<id>.md      human-readable per-session transcript
  INDEX.md              chronological session index
"""
import sqlite3
import json
import os
import re
import datetime
import hashlib

# ---- CONFIG -----------------------------------------------------------------
EXPORT = "/home/jordatech/hermes-portable-export"
DB = f"{EXPORT}/metadata/vm906-profile-state.db"          # snapshot, not the live DB
MEMDB = f"{EXPORT}/metadata/vm906-memory-store.db"
# ------------------------------------------------------------------------------
OUT = f"{EXPORT}/conversation_exports"
SESS_DIR = f"{OUT}/sessions"
os.makedirs(SESS_DIR, exist_ok=True)

SECRET_SUBS = [
    (re.compile(r'sk-[A-Za-z0-9_\-]{20,}'), 'sk-***REDACTED***'),
    (re.compile(r'ghp_[A-Za-z0-9]{30,}'), 'ghp_***REDACTED***'),
    (re.compile(r'gho_[A-Za-z0-9]{30,}'), 'gho_***REDACTED***'),
    (re.compile(r'github_pat_[A-Za-z0-9_]{20,}'), 'github_pat_***REDACTED***'),
    (re.compile(r'xox[bpars]-[A-Za-z0-9\-]{10,}'), 'xox-***REDACTED***'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'AKIA***REDACTED***'),
    (re.compile(r'Bearer [A-Za-z0-9_\-\.]{25,}'), 'Bearer ***REDACTED***'),
    # Proven-needed patterns (GitHub Push Protection incidents, 2026-09-24):
    (re.compile(r'vck_[A-Za-z0-9]{20,}'), 'vck_***REDACTED***'),   # Vercel token
    (re.compile(r'vcp_[A-Za-z0-9]{20,}'), 'vcp_***REDACTED***'),   # Vercel PAT variant
    (re.compile(r'VERCEL_TOKEN[="\\s]+[A-Za-z0-9]{20,}'), 'VERCEL_TOKEN=***REDACTED***'),
    (re.compile(r'[0-9]{10,}[a-z0-9_\-]*\.apps\.googleusercontent\.com'),
     '***REDACTED***.apps.googleusercontent.com'),
    (re.compile(r'GOCSPX-[A-Za-z0-9_\-]{5,}'), 'GOCSPX-***REDACTED***'),
    (re.compile(r'"token"\s*:\s*"[A-Za-z0-9_\-]{20,}"'), '"token": "***REDACTED***"'),
]


def scrub(text):
    if not text:
        return text
    for pat, sub in SECRET_SUBS:
        text = pat.sub(sub, text)
    return text


def iso(ts):
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat()


def slug(s):
    return re.sub(r'[^A-Za-z0-9_.\-]+', '_', s)[:120]


# ---------------------------------------------------------------- sessions
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
sessions = con.execute("SELECT * FROM sessions ORDER BY started_at ASC").fetchall()

index_rows = []
n_msgs = 0

for s in sessions:
    sid = s["id"]
    started = iso(s["started_at"])
    msgs = con.execute(
        "SELECT id, role, content, tool_name, tool_calls, timestamp, token_count "
        "FROM messages WHERE session_id = ? ORDER BY id ASC", (sid,)).fetchall()
    n_msgs += len(msgs)

    index_rows.append({
        "file": f"sessions/{slug(sid)}.md",
        "session_id": sid,
        "title": s["title"],
        "source": s["source"],
        "model": s["model"],
        "started": started,
        "messages": s["message_count"],
    })

    lines = [
        f"# Session {sid}", "",
        f"- **Title:** {s['title'] or '(untitled)'}",
        f"- **Source:** {s['source']}",
        f"- **Model:** {s['model']}",
        f"- **Started:** {started}",
        f"- **Ended:** {iso(s['ended_at'])} ({s['end_reason']})",
        f"- **Messages:** {s['message_count']}  |  Tool calls: {s['tool_call_count']}",
        "", "---", "",
    ]
    for m in msgs:
        ts = iso(m["timestamp"]) or ""
        role = m["role"] or "?"
        content = m["content"] or ""
        lines.append(f"### [{ts}] {role}" +
                     (f" · tool: {m['tool_name']}" if m["tool_name"] else ""))
        if content:
            lines += ["", scrub(content[:20000])]
            if len(content) > 20000:
                lines += ["", f"*(truncated, {len(content)} chars total)*"]
        lines += ["", "---", ""]

    with open(f"{SESS_DIR}/{slug(sid)}.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# ---------------------------------------------------------------- messages.jsonl
with open(f"{OUT}/messages.jsonl", "w", encoding="utf-8") as f:
    for m in con.execute(
            "SELECT m.id, m.session_id, m.role, m.content, m.tool_name, "
            "       m.timestamp, m.token_count, s.source, s.model, s.title "
            "FROM messages m JOIN sessions s ON s.id = m.session_id "
            "ORDER BY m.id ASC"):
        rec = {
            "id": m[0], "session_id": m[1], "role": m[2],
            "content": scrub(m[3])[:40000] if m[3] else m[3],
            "tool_name": m[4], "timestamp": iso(m[5]), "token_count": m[6],
            "session_source": m[7], "session_model": m[8], "session_title": m[9],
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------- memory records
n_facts = 0
with open(f"{OUT}/memory_records.jsonl", "w", encoding="utf-8") as f:
    mcon = sqlite3.connect(MEMDB)
    # facts has NO bank_id column — export flat, no memory_banks join
    for row in mcon.execute(
            "SELECT fact_id, content, category, tags, trust_score, created_at, updated_at "
            "FROM facts ORDER BY fact_id ASC"):
        f.write(json.dumps({
            "id": row[0], "content": scrub(row[1]), "category": row[2],
            "tags": row[3], "trust_score": row[4],
            "created_at": str(row[5]), "updated_at": str(row[6]),
        }, ensure_ascii=False) + "\n")
        n_facts += 1
    mcon.close()

# ---------------------------------------------------------------- INDEX.md
index_rows.sort(key=lambda r: r["started"] or "")
with open(f"{OUT}/INDEX.md", "w", encoding="utf-8") as f:
    f.write("# Conversation History Index\n\n")
    f.write(f"Exported: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n\n")
    f.write(f"Sessions: {len(index_rows)} | Messages: {n_msgs}\n\n")
    f.write("| # | Started | Source | Title | Msgs | File |\n")
    f.write("|---|---------|--------|-------|------|------|\n")
    for i, r in enumerate(index_rows, 1):
        started = (r["started"] or "?")[:16]
        title = (r["title"] or "(untitled)").replace("|", "\\|")
        f.write(f"| {i} | {started} | {r['source']} | {title} | "
                f"{r['messages']} | {r['file']} |\n")

con.close()
print(f"sessions exported: {len(index_rows)}")
print(f"messages exported: {n_msgs}")
print(f"memory facts:      {n_facts}")
print(f"session files:     {len(os.listdir(SESS_DIR))}")
