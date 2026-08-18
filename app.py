import os
import time
import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)
DB_FILE = "encrypted_memory.db"
PASSPHRASE = "SuperSecretMediatorKey2026!"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
    # Initialize knowledge base table if not present
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
        button { background: #4caf50; color: white; padding: 10px 15px; border: none; border-radius: 4px; font-weight: bold; width: 100%; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #333; font-size: 0.9em; }
        th { color: #888; }
        .tag { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
    </style>
</head>
<body>
    <h2>Viciously Mediator Web Admin</h2>
    
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
