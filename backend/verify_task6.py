"""AquaWatch Task 6 Manual Verification Script.

Verifies Conservation Intelligence endpoints against the live data/aquawatch.db database:
1. Verifies registered API routes including /conservation/*.
2. Calls GET /conservation/budgets (default date & historical date).
3. Calls GET /conservation/tips.
4. Calls GET /conservation/savings (default and custom tariff/hours).
"""

from fastapi.testclient import TestClient
from app.main import app

def run_verification():
    print("=" * 60)
    print("AQUAWATCH TASK 6 VERIFICATION ON LIVE DATABASE")
    print("=" * 60)

    with TestClient(app) as client:
        # 1. OpenAPI routes
        openapi_resp = client.get("/openapi.json")
        assert openapi_resp.status_code == 200
        paths = openapi_resp.json()["paths"]
        print(f"\n[1] Registered API Endpoints ({len(paths)}):")
        for p in sorted(paths.keys()):
            methods = list(paths[p].keys())
            print(f"    - {', '.join(m.upper() for m in methods)} {p}")

        assert "/conservation/budgets" in paths
        assert "/conservation/tips" in paths
        assert "/conservation/savings" in paths

        # 2. GET /conservation/budgets (default date = latest reading date in db)
        budgets_resp = client.get("/conservation/budgets")
        assert budgets_resp.status_code == 200
        b_data = budgets_resp.json()
        print(f"\n[2] GET /conservation/budgets (Latest Date: {b_data['date']}):")
        print(f"    Total Budget:    {b_data['total_budget_litres']} L")
        print(f"    Total Actual:    {b_data['total_actual_litres']} L")
        print(f"    Total Remaining: {b_data['total_remaining_litres']} L")
        print(f"    Consumed:        {b_data['overall_consumed_percent']}%")
        print(f"    Overall Status:  {b_data['overall_status']}")
        for z in b_data["zones"]:
            print(f"    - Zone {z['zone_id']} ({z['zone_name']}): {z['actual_consumption_litres']} / {z['daily_budget_litres']} L ({z['consumed_percent']}%) -> [{z['status'].upper()}]")

        # Historical date
        hist_date = "2026-08-15"
        hist_resp = client.get(f"/conservation/budgets?date={hist_date}")
        assert hist_resp.status_code == 200
        h_data = hist_resp.json()
        print(f"\n    Historical Date {hist_date} Budgets:")
        print(f"    Total Actual: {h_data['total_actual_litres']} L, Status: {h_data['overall_status']}")

        # 3. GET /conservation/tips
        tips_resp = client.get("/conservation/tips")
        assert tips_resp.status_code == 200
        t_data = tips_resp.json()
        print(f"\n[3] GET /conservation/tips (Date: {t_data['date']}, Total: {t_data['total_recommendations']}):")
        for rec in t_data["recommendations"]:
            print(f"    - [{rec['priority'].upper()}] ({rec['category']}) {rec['title']}")
            print(f"      {rec['description']}")

        # 4. GET /conservation/savings (default tariff $2.50 / kL, 24h)
        savings_resp = client.get("/conservation/savings")
        assert savings_resp.status_code == 200
        s_data = savings_resp.json()
        print(f"\n[4] GET /conservation/savings (Tariff: ${s_data['tariff_per_kl']}/kL, Hours: {s_data['assumed_hours_per_day']}h/day):")
        print(f"    Total Leaks Evaluated:   {s_data['total_leaks_evaluated']}")
        print(f"    Actionable Leaks:        {s_data['actionable_leaks_count']}")
        print(f"    Total Daily Waste:       {s_data['total_daily_wasted_litres']} L")
        print(f"    Total Monthly Waste:     {s_data['total_monthly_wasted_litres']} L")
        print(f"    Estimated Monthly Savings: ${s_data['total_monthly_savings']}")
        for le in s_data["leak_estimates"][:3]:
            print(f"    - Alert #{le['alert_id']} in {le['zone_name']}: Flow={le['leak_flow_lph']} L/h, Daily={le['daily_wasted_litres']} L, Monthly Savings=${le['monthly_savings']} [{le['status']}]")

        # Custom tariff & hours
        custom_resp = client.get("/conservation/savings?tariff_per_kl=3.75&hours_per_day=12.0")
        assert custom_resp.status_code == 200
        cs_data = custom_resp.json()
        print(f"\n    Custom Config (Tariff: ${cs_data['tariff_per_kl']}/kL, Hours: {cs_data['assumed_hours_per_day']}h/day):")
        print(f"    Total Daily Waste:       {cs_data['total_daily_wasted_litres']} L")
        print(f"    Estimated Monthly Savings: ${cs_data['total_monthly_savings']}")

    print("\n" + "=" * 60)
    print("ALL TASK 6 VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
