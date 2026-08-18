import os
import time
import json
import sqlite3
import base64
from flask import Flask, request, render_template_string, redirect, url_for, Response
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad

app = Flask(__name__)
DB_FILE = "encrypted_memory.db"
PASSPHRASE = "SuperSecretMediatorKey2026!"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            subject TEXT,
            fact_or_rule TEXT,
            weight INTEGER DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            transcript TEXT,
            advice TEXT
        )
    """)
    conn.commit()
    return conn, cursor

def encrypt_payload(data_dict, passphrase):
    # Derive a 256-bit AES key using PBKDF2
    salt = os.urandom(16)
    key = PBKDF2(passphrase, salt, dkLen=32, count=1000)
    cipher = AES.new(key, AES.MODE_CBC)
    
    # Serialize JSON and pad
    json_bytes = json.dumps(data_dict).encode('utf-8')
    padded_data = pad(json_bytes, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    
    # Combine salt + IV + ciphertext in Base64 wrapper
    backup_payload = {
        "salt": base64.b64encode(salt).decode('utf-8'),
        "iv": base64.b64encode(cipher.iv).decode('utf-8'),
        "data": base64.b64encode(ciphertext).decode('utf-8')
    }
    return json.dumps(backup_payload, indent=2)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Viciously Admin Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, sans-serif; margin: 15px; background: #121212; color: #e0e0e0; }
        h2 { color: #4caf50; border-bottom: 1px solid #333; padding-bottom: 5px; }
        .card { background: #1e1e1e; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #333; }
        input, select, textarea { width: 100%; padding: 8px; margin: 5px 0 15px; background: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 4px; box-sizing: border-box; }
        button, .btn { background: #4caf50; color: white; padding: 10px 15px; border: none; border-radius: 4px; font-weight: bold; width: 100%; display: inline-block; text-align: center; text-decoration: none; box-sizing: border-box; }
        .btn-export { background: #2196F3; margin-top: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #333; font-size: 0.9em; }
        th { color: #888; }
        .tag { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    </style>
</head>
<body>
    <h2>Viciously Mediator Web Admin</h2>
    
    <div class="card">
        <h3>Backup Options</h3>
        <p style="font-size: 0.85em; color: #aaa;">Export all recorded memories and knowledge base context into an AES-256 encrypted JSON file.</p>
        <a href="/export_backup" class="btn btn-export">🔒 Download Encrypted Backup (.json)</a>
    </div>

    <div class="card">
        <h3>Add History / Conflict Boundary</h3>
        <form action="/add_rule" method="POST">
            <label>Category</label>
            <select name="category">
                <option value="history">Historical Fact / Past Argument</option>
                <option value="boundary">Agreed Boundary / Rule</option>
                <option value="trigger">Known Trigger Word/Topic</option>
            </select>
            
            <label>Subject Topic</label>
            <input type="text" name="subject" placeholder="e.g., Finances, Chores, Schedule" required>
            
            <label>Context / Fact / Rule</label>
            <textarea name="fact_or_rule" rows="3" placeholder="e.g., Agreed on $100 max budget without prior discussion." required></textarea>
            
            <label>Priority Weight (1-5)</label>
            <input type="number" name="weight" min="1" max="5" value="3">
            
            <button type="submit">Save Context Rule</button>
        </form>
    </div>

    <div class="card">
        <h3>Active Knowledge Base Context</h3>
        <table>
            <tr><th>Subject</th><th>Rule / Fact</th><th>Weight</th><th>Action</th></tr>
            {% for rule in rules %}
            <tr>
                <td><span class="tag">{{ rule[1] }}</span><br><b>{{ rule[2] }}</b></td>
                <td>{{ rule[3] }}</td>
                <td>{{ rule[4] }}</td>
                <td><a href="/delete_rule/{{ rule[0] }}" style="color: #ff5252; text-decoration: none;">Delete</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h3>Recent Mediation Logs</h3>
        <table>
            <tr><th>Transcript</th><th>Advice Given</th></tr>
            {% for mem in memories %}
            <tr>
                <td>"{{ mem[2] }}"</td>
                <td style="color: #81c784;">{{ mem[3] }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    conn, cursor = get_db()
    cursor.execute("SELECT id, category, subject, fact_or_rule, weight FROM knowledge_base ORDER BY weight DESC")
    rules = cursor.fetchall()
    
    cursor.execute("SELECT id, timestamp, transcript, advice FROM memories ORDER BY id DESC LIMIT 10")
    memories = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, rules=rules, memories=memories)

@app.route('/add_rule', methods=['POST'])
def add_rule():
    category = request.form['category']
    subject = request.form['subject']
    fact_or_rule = request.form['fact_or_rule']
    weight = request.form['weight']
    
    conn, cursor = get_db()
    cursor.execute(
        "INSERT INTO knowledge_base (category, subject, fact_or_rule, weight) VALUES (?, ?, ?, ?)",
        (category, subject, fact_or_rule, int(weight))
    )
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_rule/<int:rule_id>')
def delete_rule(rule_id):
    conn, cursor = get_db()
    cursor.execute("DELETE FROM knowledge_base WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/export_backup')
def export_backup():
    conn, cursor = get_db()
    
    cursor.execute("SELECT id, timestamp, transcript, advice FROM memories")
    memories = [
        {"id": row[0], "timestamp": row[1], "transcript": row[2], "advice": row[3]} 
        for row in cursor.fetchall()
    ]
    
    cursor.execute("SELECT id, category, subject, fact_or_rule, weight FROM knowledge_base")
    knowledge = [
        {"id": row[0], "category": row[1], "subject": row[2], "fact_or_rule": row[3], "weight": row[4]} 
        for row in cursor.fetchall()
    ]
    conn.close()
    
    backup_data = {
        "export_timestamp": int(time.time()),
        "memories": memories,
        "knowledge_base": knowledge
    }
    
    encrypted_file = encrypt_payload(backup_data, PASSPHRASE)
    filename = f"viciously_backup_{int(time.time())}.json"
    
    return Response(
        encrypted_file,
        mimetype="application/json",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
