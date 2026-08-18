import os
import sqlite3
import time

DB_PATH = os.path.expanduser("~/viciously/encrypted_mediator.db")
MAX_AGE_DAYS = 7

def enforce_privacy_retention():
    """Purges encrypted entries older than 7 days and vacuums storage."""
    if not os.path.exists(DB_PATH):
        return
        
    cutoff_timestamp = int(time.time()) - (MAX_AGE_DAYS * 86400)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete old memories
        cursor.execute("DELETE FROM memories WHERE timestamp < ?", (cutoff_timestamp,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        
        # Optimize disk space
        cursor.execute("VACUUM;")
        conn.close()
        
        print(f"[Privacy Cleanup] Success. Purged {deleted_count} expired entries.")
    except Exception as e:
        print(f"[Cleanup Error]: {e}")

if __name__ == "__main__":
    enforce_privacy_retention()
