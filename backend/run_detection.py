"""AquaWatch CLI Detection & Evaluation Runner.

Executes all three anomaly detectors against the SQLite database and prints
an event-level benchmark report comparing predictions to ground truth.

Usage:
    python backend/run_detection.py
"""

from pathlib import Path
import sys

# Ensure backend directory is in python search path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.detection import run_all_detectors


def main():
    print("=" * 68)
    print("        AQUAWATCH ANOMALY DETECTION ENGINE & EVALUATION")
    print("=" * 68)

    results = run_all_detectors()
    readings_count = results["readings_count"]
    gt_count = results["ground_truth_count"]
    evals = results["evaluations"]

    print(f"\nDataset Statistics:")
    print(f" - Readings analyzed:   {readings_count:,}")
    print(f" - Ground-truth events: {gt_count}")
    print("-" * 68)

    method_titles = {
        "rule_based": "1. Rule-Based Night-Flow Detector",
        "z_score": "2. Statistical Z-Score Detector",
        "isolation_forest": "3. Machine-Learning Isolation Forest Detector",
    }

    for key, title in method_titles.items():
        em = evals.get(key)
        if not em:
            continue

        print(f"\n{title}")
        print("~" * len(title))
        print(f"True Positives (TP):   {em.true_positives}")
        print(f"False Positives (FP):  {em.false_positives}")
        print(f"False Negatives (FN):  {em.false_negatives}")
        print(f"Precision:             {em.precision:.4f} ({em.precision * 100:.1f}%)")
        print(f"Recall:                {em.recall:.4f} ({em.recall * 100:.1f}%)")
        print(f"F1 Score:              {em.f1_score:.4f}")

        print("\n  Per-Anomaly-Type Breakdown:")
        print(f"  {'Anomaly Type':<15} {'Total GT':<10} {'Detected (TP)':<15} {'Recall':<10}")
        print(f"  {'-'*15} {'-'*10} {'-'*15} {'-'*10}")
        for atype, stats in em.per_type_metrics.items():
            print(
                f"  {atype:<15} {stats['ground_truth_total']:<10} "
                f"{stats['true_positives']:<15} {stats['recall']*100:.1f}%"
            )

    print("\n" + "=" * 68)


if __name__ == "__main__":
    main()
