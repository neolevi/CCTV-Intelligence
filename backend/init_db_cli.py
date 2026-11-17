"""Script to initialize the database."""
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialization completed successfully.")
