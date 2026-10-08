import sqlite3, time

conn = sqlite3.connect("chocobot.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS customers (
    session_id TEXT PRIMARY KEY, name TEXT, email TEXT, allergies TEXT, children_ages TEXT, created_at REAL)""")
conn.execute("""CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, created_at REAL)""")
conn.execute("""CREATE TABLE IF NOT EXISTS llm_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    latency_seconds REAL,
    status TEXT,
    error_message TEXT,
    created_at REAL)""")
conn.commit()


def save_customer(session_id, name, email, allergies, children_ages):
    conn.execute("INSERT OR REPLACE INTO customers VALUES (?,?,?,?,?,?)",
                 (session_id, name, email, allergies, children_ages, time.time()))
    conn.commit()


def get_customer(session_id):
    row = conn.execute("SELECT name, email, allergies, children_ages FROM customers WHERE session_id=?",
                       (session_id,)).fetchone()
    return dict(zip(["name", "email", "allergies", "children_ages"], row)) if row else {}


def save_message(session_id, role, content):
    conn.execute("INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
                 (session_id, role, content, time.time()))
    conn.commit()


def get_history(session_id):
    rows = conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
    return [{"role": r, "content": c} for r, c in rows]


def save_metric(session_id, model, prompt_tokens, completion_tokens, total_tokens, latency, status="ok", error=None):
    conn.execute(
        "INSERT INTO llm_metrics (session_id, model, prompt_tokens, completion_tokens, total_tokens, latency_seconds, status, error_message, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (session_id, model, prompt_tokens, completion_tokens, total_tokens, latency, status, error, time.time())
    )
    conn.commit()


def get_stats():
    row = conn.execute("""
        SELECT 
            COALESCE(SUM(total_tokens), 0),
            COALESCE(COUNT(CASE WHEN status != 'ok' THEN 1 END), 0),
            COALESCE(AVG(CASE WHEN status = 'ok' THEN latency_seconds END), 0),
            COUNT(*)
        FROM llm_metrics
    """).fetchone()
    total_tokens, errors_count, avg_latency, total_calls = row if row else (0, 0, 0, 0)
    return {
        "total_tokens": int(total_tokens),
        "errors_count": int(errors_count),
        "avg_latency": round(float(avg_latency), 2),
        "total_calls": int(total_calls),
        "cost_eur": 0.0
    }


def get_all():
    cust = conn.execute("SELECT session_id, name, email, allergies, children_ages, created_at FROM customers ORDER BY created_at DESC").fetchall()
    msgs = conn.execute("SELECT id, session_id, role, content, created_at FROM messages ORDER BY id DESC LIMIT 200").fetchall()
    metrics = conn.execute("SELECT id, session_id, model, total_tokens, latency_seconds, status, created_at FROM llm_metrics ORDER BY id DESC LIMIT 50").fetchall()
    return {
        "customers": [dict(zip(["session_id", "name", "email", "allergies", "children_ages", "created_at"], r)) for r in cust],
        "messages": [dict(zip(["id", "session_id", "role", "content", "created_at"], r)) for r in msgs],
        "metrics": [dict(zip(["id", "session_id", "model", "total_tokens", "latency_seconds", "status", "created_at"], r)) for r in metrics],
        "stats": get_stats()
    }

