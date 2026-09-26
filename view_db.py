"""
Database Viewer Utility
Run with: py -3.13 view_db.py
Or pass table name: py -3.13 view_db.py tenders
"""
import sqlite3
import json
import sys

DB_PATH = "tender_platform.db"

def inspect_db(selected_table=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [r[0] for r in cursor.fetchall()]

    if selected_table:
        matched = [t for t in tables if t.lower() == selected_table.lower()]
        if not matched:
            print(f"Table '{selected_table}' not found. Available tables:")
            print(", ".join(tables))
            conn.close()
            return
        tables = matched

    print("=" * 70)
    print(f"DATABASE: {DB_PATH}")
    print(f"TABLES FOUND: {len(tables)}")
    print("=" * 70)

    for table in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"\nTABLE: {table.upper()} ({count} records)")
        print("-" * 70)

        cursor.execute(f"SELECT * FROM {table} LIMIT 10")
        rows = cursor.fetchall()
        if not rows:
            print("  (Empty table)")
            continue

        columns = [d[0] for d in cursor.description]
        display_cols = [c for c in columns if c not in ["metadata_json", "hashed_password"]]
        print("  Columns: " + ", ".join(display_cols))
        
        for idx, row in enumerate(rows, 1):
            row_dict = {c: row[c] for c in display_cols[:8]}
            print(f"  [{idx}] {json.dumps(row_dict, default=str)}")

        if count > 10:
            print(f"  ... and {count - 10} more records (run 'py -3.13 view_db.py {table}' to view table directly)")

    conn.close()
    print("\n" + "=" * 70)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    inspect_db(target)
