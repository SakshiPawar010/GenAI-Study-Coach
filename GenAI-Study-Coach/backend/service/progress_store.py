import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'study_coach.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS quiz_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL DEFAULT 'default',
                topic      TEXT    NOT NULL,
                score      INTEGER NOT NULL,
                total      INTEGER NOT NULL,
                pct        INTEGER NOT NULL,
                difficulty TEXT    NOT NULL,
                date       TEXT    NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS weak_areas (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        TEXT    NOT NULL DEFAULT 'default',
                question       TEXT    NOT NULL,
                correct_answer TEXT    NOT NULL,
                topic          TEXT    NOT NULL,
                wrong_count    INTEGER NOT NULL DEFAULT 1,
                UNIQUE(user_id, question)
            )
        ''')
        # Migrate existing tables that don't have user_id column yet
        try:
            conn.execute("ALTER TABLE quiz_history ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE weak_areas ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
        except Exception:
            pass
        conn.commit()


# ── Quiz History ──────────────────────────────────────────────────────────────

def record_quiz(user_id, topic, score, total, difficulty):
    init_db()
    pct = round(score / total * 100)
    with _conn() as conn:
        conn.execute(
            'INSERT INTO quiz_history (user_id, topic, score, total, pct, difficulty, date) VALUES (?,?,?,?,?,?,?)',
            (user_id, topic, score, total, pct, difficulty, datetime.now().strftime('%Y-%m-%d %H:%M'))
        )
        conn.commit()


def get_history(user_id):
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            'SELECT topic, score, total, pct, difficulty, date FROM quiz_history WHERE user_id=? ORDER BY id ASC',
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def clear_history(user_id):
    init_db()
    with _conn() as conn:
        conn.execute('DELETE FROM quiz_history WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM weak_areas WHERE user_id=?', (user_id,))
        conn.commit()


# ── Weak Areas ────────────────────────────────────────────────────────────────

def record_wrong_answer(user_id, question, correct_answer, topic):
    init_db()
    key = question[:120]
    with _conn() as conn:
        existing = conn.execute(
            'SELECT id FROM weak_areas WHERE user_id=? AND question=?', (user_id, key)
        ).fetchone()
        if existing:
            conn.execute(
                'UPDATE weak_areas SET wrong_count = wrong_count + 1 WHERE user_id=? AND question=?',
                (user_id, key)
            )
        else:
            conn.execute(
                'INSERT INTO weak_areas (user_id, question, correct_answer, topic, wrong_count) VALUES (?,?,?,?,1)',
                (user_id, key, correct_answer, topic)
            )
        conn.commit()


def get_weak_areas(user_id, top_n=10):
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            'SELECT question, correct_answer, topic, wrong_count FROM weak_areas WHERE user_id=? ORDER BY wrong_count DESC LIMIT ?',
            (user_id, top_n)
        ).fetchall()
    return [dict(r) for r in rows]
