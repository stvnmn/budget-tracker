"""
migrate_csv.py — one-time import of your existing budget_data.csv into SQLite.

Usage:
    python migrate_csv.py \
        --csv ~/OneDrive/Projects/BudgetTrackerData/budget_data.csv \
        --db  ./data/budget.db
"""
import argparse, csv, os, sqlite3
from datetime import datetime


def yearweek(date_str: str) -> str:
    dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--db",  required=True)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, description TEXT NOT NULL,
            category TEXT NOT NULL, amount REAL NOT NULL, year_week TEXT NOT NULL
        )
    """)

    inserted = skipped = 0
    with open(args.csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                conn.execute(
                    "INSERT INTO transactions (date,description,category,amount,year_week) VALUES (?,?,?,?,?)",
                    (row["Date"].strip(), row["Description"].strip(),
                     row["Category"].strip(), float(row["Amount"]),
                     yearweek(row["Date"]))
                )
                inserted += 1
            except Exception as e:
                print(f"  Skipped: {row} → {e}")
                skipped += 1

    conn.commit()
    conn.close()
    print(f"Done — inserted: {inserted}, skipped: {skipped}")
    print(f"Database: {args.db}")


if __name__ == "__main__":
    main()
