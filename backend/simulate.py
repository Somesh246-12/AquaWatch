"""AquaWatch CLI Simulator Script.

Generates deterministic synthetic water consumption datasets with ground-truth anomalies.

Usage:
    python backend/simulate.py --days 60 --seed 42 --reset --export-csv
"""

import argparse
import logging
from pathlib import Path
import sys

# Ensure backend root is on sys.path when executed standalone
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.simulator import (
    simulate_dataset,
    reset_simulation_data,
    export_readings_to_csv,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("aquawatch.cli")


def main():
    parser = argparse.ArgumentParser(
        description="AquaWatch Deterministic Water Consumption Simulator"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Number of days to simulate (default: 60)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset existing readings and anomalies before simulating",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Export generated readings to a CSV file",
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        default="data/readings.csv",
        help="Output file path for CSV export (default: data/readings.csv)",
    )

    args = parser.parse_args()

    print("=" * 65)
    print(" AquaWatch: Deterministic Water Consumption Simulator")
    print("=" * 65)
    print(f"Configuration:")
    print(f" - Days:       {args.days}")
    print(f" - Seed:       {args.seed}")
    print(f" - Reset:      {args.reset}")
    print(f" - Export CSV: {args.export_csv}")
    print("=" * 65)

    if args.reset:
        logger.info("Resetting existing simulation readings and anomalies...")
        reset_simulation_data()

    logger.info("Running simulation...")
    summary = simulate_dataset(days=args.days, seed=args.seed, persist=True)

    print("\nSimulation Summary")
    print("-" * 35)
    print(f"Zones:             {summary['zones_count']}")
    print(f"Days:              {summary['days_count']}")
    print(f"Total readings:    {summary['total_readings']}")
    print("Readings per zone:")
    for zone_name, count in summary["readings_per_zone"].items():
        print(f" - {zone_name:<16}: {count}")

    print("\nConsumption Statistics (Litres):")
    print(f" - Min litres:     {summary['min_litres']:,.2f} L")
    print(f" - Max litres:     {summary['max_litres']:,.2f} L")
    print(f" - Avg litres:     {summary['avg_litres']:,.2f} L")

    print("\nGround Truth Anomaly Events:")
    print(f" - Slow leaks:     {summary['slow_leaks_count']}")
    print(f" - Bursts:         {summary['bursts_count']}")
    print(f" - Wastage days:   {summary['wastage_days_count']}")
    print(f" - Total events:   {summary['total_anomalies_count']}")
    print("=" * 65)

    if args.export_csv:
        csv_file = export_readings_to_csv(output_path=args.csv_path)
        print(f"\n[OK] CSV exported successfully to: {csv_file}")
        print("=" * 65)


if __name__ == "__main__":
    main()
