import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from src.config import Config

try:
    import libsql_client
    TURSO_AVAILABLE = True
except ImportError:
    TURSO_AVAILABLE = False

DB_PATH = "data/chatbot_history.db"

class MemoryTools:
    def __init__(self):
        self.turso_client = None
        self.sqlite_conn = None
        self.mode = "none"
        if TURSO_AVAILABLE:
            try:
                self.turso_client = libsql_client.create_client_sync(
                    url=Config.TURSO_DATABASE_URL,
                    auth_token=Config.TURSO_AUTH_TOKEN
                )
                self._initialize_turso()
                self.mode = "turso"
                print("✅ Memory: Turso cloud DB")
                return
            except Exception as e:
                print(f"⚠️ Turso failed: {e}")
        Path(DB_PATH).parent.mkdir(exist_ok=True)
        try:
            self.sqlite_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._initialize_sqlite()
            self.mode = "sqlite"
            print(f"✅ Memory: Local SQLite ({DB_PATH})")
        except Exception as e:
            print(f"⚠️ SQLite setup failed: {e}")

    def _initialize_turso(self):
        self.turso_client.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.turso_client.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _initialize_sqlite(self):
        cur = self.sqlite_conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        """)
        self.sqlite_conn.commit()

    def create_new_conversation(self, title: str = "New Chat") -> int:
        now = datetime.now()
        if self.mode == "turso":
            self.turso_client.execute(
                "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
                [title, now, now]
            )
            result = self.turso_client.execute("SELECT max(id) FROM conversations")
            return result.rows[0][0]
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute(
                "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
                (title, now, now)
            )
            self.sqlite_conn.commit()
            return cur.lastrowid

    def save_message(self, conversation_id: int, role: str, content: str):
        now = datetime.now()
        if self.mode == "turso":
            self.turso_client.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                [conversation_id, role, content, now]
            )
            self.turso_client.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", [now, conversation_id]
            )
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, now)
            )
            cur.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
            )
            self.sqlite_conn.commit()

    def get_all_conversations(self, search_term: str = "") -> List[Dict]:
        if self.mode == "turso":
            if search_term:
                result = self.turso_client.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations WHERE title LIKE ? ORDER BY updated_at DESC",
                    [f"%{search_term}%"]
                )
            else:
                result = self.turso_client.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
                )
            return [
                {'id': row[0], 'title': row[1], 'created_at': row[2], 'updated_at': row[3]}
                for row in result.rows
            ]
        else:
            cur = self.sqlite_conn.cursor()
            if search_term:
                cur.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations WHERE title LIKE ? ORDER BY updated_at DESC",
                    (f"%{search_term}%",)
                )
            else:
                cur.execute(
                    "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
                )
            return [{'id': r[0], 'title': r[1], 'created_at': r[2], 'updated_at': r[3]} for r in cur.fetchall()]

    def get_messages_for_conversation(self, conversation_id: int) -> List[Dict]:
        if self.mode == "turso":
            result = self.turso_client.execute(
                "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                [conversation_id]
            )
            return [{'role': r[0], 'content': r[1], 'timestamp': r[2]} for r in result.rows]
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute(
                "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
                (conversation_id,)
            )
            return [{'role': r[0], 'content': r[1], 'timestamp': r[2]} for r in cur.fetchall()]

    def delete_conversation(self, conversation_id: int):
        if self.mode == "turso":
            self.turso_client.execute("DELETE FROM messages WHERE conversation_id = ?", [conversation_id])
            self.turso_client.execute("DELETE FROM conversations WHERE id = ?", [conversation_id])
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cur.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            self.sqlite_conn.commit()

    def update_conversation_title(self, conversation_id: int, new_title: str):
        if self.mode == "turso":
            self.turso_client.execute(
                "UPDATE conversations SET title = ? WHERE id = ?", [new_title, conversation_id]
            )
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute(
                "UPDATE conversations SET title = ? WHERE id = ?", (new_title, conversation_id)
            )
            self.sqlite_conn.commit()

    def delete_all_conversations(self):
        if self.mode == "turso":
            self.turso_client.execute("DELETE FROM messages")
            self.turso_client.execute("DELETE FROM conversations")
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute("DELETE FROM messages")
            cur.execute("DELETE FROM conversations")
            self.sqlite_conn.commit()

_memory_tools_instance = None

def get_memory_tools():
    global _memory_tools_instance
    if _memory_tools_instance is None:
        _memory_tools_instance = MemoryTools()
    return _memory_tools_instance
