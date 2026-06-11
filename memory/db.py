import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "buddy.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            deadline TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS learning_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            summary TEXT DEFAULT '',
            resource TEXT DEFAULT '',
            time_spent INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);
    """)
    conn.commit()
    conn.close()


# --- Notes ---

def save_note(title: str, content: str, tags: str = "") -> int:
    now = datetime.now().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO notes (title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (title, content, tags, now, now),
    )
    note_id = cur.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_all_notes() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM notes ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_notes(query: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? ORDER BY updated_at DESC",
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_note(note_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# --- Tasks ---

def add_task(title: str, description: str = "", deadline: str = "", priority: str = "medium") -> int:
    now = datetime.now().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, deadline, priority, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (title, description, deadline, priority, now),
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id


def list_tasks(status: str = "") -> list[dict]:
    conn = get_conn()
    if status:
        rows = conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,))
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY status ASC, deadline ASC")
    results = [dict(r) for r in rows.fetchall()]
    conn.close()
    return results


def complete_task(task_id: int) -> bool:
    now = datetime.now().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?",
        (now, task_id),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def delete_task(task_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# --- Learning Log ---

def log_learning(topic: str, summary: str = "", resource: str = "", time_spent: int = 0) -> int:
    now = datetime.now().isoformat()
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO learning_log (topic, summary, resource, time_spent, created_at) VALUES (?, ?, ?, ?, ?)",
        (topic, summary, resource, time_spent, now),
    )
    log_id = cur.lastrowid
    conn.commit()
    conn.close()
    return log_id


def get_learning_progress() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM learning_log ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Chat History ---

def save_chat_message(session_id: str, role: str, content: str):
    now = datetime.now().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO chat_history (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, now),
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id: str, limit: int = 20) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()