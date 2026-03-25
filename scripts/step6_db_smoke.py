#!/usr/bin/env python3
"""Step 6: PostgreSQL connection layer. Connects and runs SELECT 1."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection

def main():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    row = cur.fetchone()
    cur.close()
    print("postgres connection OK")
    print("SELECT 1 =>", row)

if __name__ == "__main__":
    main()
