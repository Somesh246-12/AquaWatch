"""AquaWatch CLI Database Initialization Script.

Creates all database tables and seeds the five default monitoring zones.
Idempotent: safe to run multiple times.
"""

import sys
from pathlib import Path

# Add backend directory to path if executed standalone
sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
from app.services.init_db import init_db

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
    print("=" * 65)
    print(" AquaWatch: Initializing Database & Seeding Default Zones")
    print("=" * 65)
    db_zones = init_db()
    print(f"\nTotal Zones in Database: {len(db_zones)}")
    for z in db_zones:
        print(f" - [{z.id}] {z.name:<16} | Type: {z.type:<22} | Budget: {z.daily_budget_litres:,.1f} L/day")
    print("=" * 65)
