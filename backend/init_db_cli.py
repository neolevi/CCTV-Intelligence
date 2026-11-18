"""Script to initialize the database."""
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db

if __name__ == "__main__":
    try:
        init_db()
        print("Database initialization completed successfully.")
        sys.exit(0)
    except Exception as e:
        print(f"[FATAL] Database initialization error: {e}", file=sys.stderr)
        sys.exit(1)
