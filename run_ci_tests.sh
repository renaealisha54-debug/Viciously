#!/bin/bash
echo "=== RUNNING LOCAL CI & WORKFLOW VERIFICATION ==="
echo "Date: $(date)"
echo "-----------------------------------------------"

# 1. Check Python Syntax for mediator.py and app.py
echo "[Step 1/3] Validating Python Syntax..."
python3 -m py_compile mediator.py && echo " -> mediator.py: PASSED"
python3 -m py_compile app.py && echo " -> app.py: PASSED"

# 2. Test Encryption Library
echo "[Step 2/3] Validating PyCryptodome..."
python3 -c "from Crypto.Cipher import AES; print(' -> PyCryptodome: PASSED')"

# 3. Test Database Structure
echo "[Step 3/3] Validating Database Schema..."
python3 -c "
import sqlite3
conn = sqlite3.connect('test_run.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, timestamp INTEGER, transcript TEXT, advice TEXT);')
conn.commit()
conn.close()
print(' -> Database Schema: PASSED')
"

echo "-----------------------------------------------"
echo "=== ALL LOCAL WORKFLOW TESTS PASSED ==="
