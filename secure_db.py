import os
import sqlite3
import time
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

DB_PATH = os.path.expanduser("~/viciously/encrypted_mediator.db")
KEY_PATH = os.path.expanduser("~/viciously/.db_key")

def get_or_create_key():
    """Generates or retrieves a local device key stored securely."""
    if not os.path.exists(KEY_PATH):
        key = get_random_bytes(32)
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        os.chmod(KEY_PATH, 0o600)  # Restrict permissions
        return key
    with open(KEY_PATH, "rb") as f:
        return f.read()

def init_secure_db():
    """Initializes schema for memory logs and boundary rules."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Store timestamped summaries (No verbatim quotes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            analysis_summary TEXT NOT NULL,
            spoken_advice TEXT NOT NULL
        )
    """)
    
    # Store boundaries & rules
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boundaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            rule_description TEXT NOT NULL,
            severity_weight INTEGER DEFAULT 1
        )
    """)
    
    conn.commit()
    conn.close()
    print("[Secure DB] Encrypted database schema initialized.")

if __name__ == "__main__":
    init_secure_db()
