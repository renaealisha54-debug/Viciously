import os
import time
import sqlite3
import requests

DB_FILE = "encrypted_memory.db"
PASSPHRASE = "SuperSecretMediatorKey2026!"
RETENTION_DAYS = 7

# --- Database & Context Fetching ---

def fetch_knowledge_context():
    """Queries active rules, boundaries, and history from knowledge_base."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
        
        # Select rules ordered by priority weight
        cursor.execute("""
            SELECT category, subject, fact_or_rule, weight 
            FROM knowledge_base 
            WHERE weight >= 2 
            ORDER BY weight DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return ""
            
        context_str = "\n[KNOWN BACKGROUND & AGREED BOUNDARIES]:\n"
        for row in rows:
            cat, subject, rule, weight = row
            context_str += f"- ({cat.upper()} - {subject}): {rule}\n"
        return context_str
    except Exception as e:
        print(f"[DB Warning] Could not fetch knowledge context: {e}")
        return ""

def save_encrypted_memory(transcript, advice):
    """Saves transcript/advice and enforces the 7-day retention policy."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = '{PASSPHRASE}';")
        
        current_time = int(time.time())
        cursor.execute(
            "INSERT INTO memories (timestamp, transcript, advice) VALUES (?, ?, ?)",
            (current_time, transcript, advice)
        )
        
        # Auto-prune logs older than 7 days
        cutoff_time = current_time - (RETENTION_DAYS * 86400)
        cursor.execute("DELETE FROM memories WHERE timestamp < ?", (cutoff_time,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB Error] Failed to save memory: {e}")

# --- Hybrid Intelligence Pipeline ---

def generate_deescalation_advice(transcript):
    """Constructs prompt using active knowledge base context and queries LLM."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    # 1. Fetch live rules/history
    background_context = fetch_knowledge_context()
    
    # 2. Build contextual system prompt
    system_prompt = (
        "You are an objective conflict mediator monitoring a live conversation. "
        "Provide a calm, neutral 1-sentence de-escalation suggestion. "
        "If a spoken point conflicts with an agreed boundary below, gently mention it.\n"
        f"{background_context}"
    )
    
    # 3. Primary Path: Groq API Cloud Inference
    if groq_api_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f'Current Transcript: "{transcript}"'}
                ],
                "temperature": 0.3
            }
            res = requests.post(url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"[Cloud Fallback] Groq unavailable: {e}")

    # 4. Fallback Path: Local Ollama Inference
    try:
        ollama_url = "http://localhost:11434/api/generate"
        prompt = f"{system_prompt}\n\nTranscript: \"{transcript}\"\nAdvice:"
        payload = {"model": "llama3.2:1b", "prompt": prompt, "stream": False}
        res = requests.post(ollama_url, json=payload, timeout=10)
        if res.status_code == 200:
            return res.json()['response'].strip()
    except Exception:
        pass

    return "Take a slow breath before responding to maintain calm."

# --- Engine Loop Simulation ---

if __name__ == "__main__":
    print("=== Viciously Engine Active ===")
    sample_transcript = "We never discussed this budget item!"
    
    print(f"\nProcessing Audio Input: '{sample_transcript}'")
    advice = generate_deescalation_advice(sample_transcript)
    
    print(f"Generated Advice: {advice}")
    save_encrypted_memory(sample_transcript, advice)
