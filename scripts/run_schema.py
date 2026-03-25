#!/usr/bin/env python3
"""Run initial schema (sql/001_initial_schema.sql). Requires DATABASE_URL in .env."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection

def main():
    schema_path = os.path.join(ROOT, "sql", "001_initial_schema.sql")
    if not os.path.isfile(schema_path):
        print("Schema file not found:", schema_path)
        sys.exit(1)
    with open(schema_path, "r") as f:
        sql = f.read()
    init_db()
    conn = get_connection()
    conn.cursor().execute(sql)
    conn.commit()
    conn.cursor().close()
    print("Schema applied: 001_initial_schema.sql")

if __name__ == "__main__":
    main()
