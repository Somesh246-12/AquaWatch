"""AquaWatch Task 5 Manual Verification Script.

Executes all verification steps against the live data/aquawatch.db database:
1. Verifies all API routes and OpenAPI schema.
2. Calls GET /zones.
3. Calls GET /readings.
4. Calls GET /summary.
5. Calls GET /alerts.
6. Calls POST /detection/run.
7. Verifies alerts are stored.
8. Calls POST /detection/run again (verifies no duplicates).
9. Resolves one alert and verifies it disappears from active alerts.
"""

import json
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.alert import Alert

def run_verification():
    print("=" * 60)
    print("AQUAWATCH TASK 5 VERIFICATION ON LIVE DATABASE")
    print("=" * 60)

    with TestClient(app) as client:
        # 1. Verify OpenAPI routes
        openapi_resp = client.get("/openapi.json")
        assert openapi_resp.status_code == 200, f"OpenAPI failed: {openapi_resp.status_code}"
        routes = list(openapi_resp.json()["paths"].keys())
        print(f"\n[1] Registered API Routes ({len(routes)}):")
        for r in sorted(routes):
            methods = list(openapi_resp.json()["paths"][r].keys())
            print(f"    - {', '.join(m.upper() for m in methods)} {r}")

        # 2. GET /zones
        zones_resp = client.get("/zones")
        assert zones_resp.status_code == 200
        zones = zones_resp.json()
        print(f"\n[2] GET /zones: Retrieved {len(zones)} zones:")
        for z in zones:
            print(f"    Zone {z['id']}: {z['name']} ({z['type']}) - Budget: {z['daily_budget_litres']} L/day")

        # 3. GET /readings (Hourly sample + Daily sample)
        readings_resp = client.get("/readings?limit=5")
        assert readings_resp.status_code == 200
        readings = readings_resp.json()
        print(f"\n[3] GET /readings (hourly limit=5):")
        for r in readings:
            print(f"    Reading #{r['id']}: Zone {r['zone_id']} @ {r['timestamp']} = {r['litres']} L")

        daily_resp = client.get("/readings?aggregation=daily&limit=5")
        assert daily_resp.status_code == 200
        daily_readings = daily_resp.json()
        print(f"\n    GET /readings (daily limit=5):")
        for dr in daily_readings:
            print(f"    Date {dr['date']}: Zone {dr['zone_id']} ({dr.get('zone_name')}) = {dr['litres']} L")

        # 4. GET /summary
        summary_resp = client.get("/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        print(f"\n[4] GET /summary:")
        print(f"    Today's Usage:     {summary['today_usage_litres']} L")
        print(f"    Yesterday's Usage: {summary['yesterday_usage_litres']} L")
        print(f"    Change %:          {summary['change_percent']}%")
        print(f"    Weekly Usage:      {summary['weekly_usage_litres']} L")
        print(f"    Active Alerts:     {summary['active_alerts']}")
        if summary.get('top_zone'):
            print(f"    Top Zone:          Zone {summary['top_zone']['id']} ({summary['top_zone']['name']}) with {summary['top_zone']['litres']} L")

        # 5. GET /alerts (initial state)
        alerts_resp = client.get("/alerts")
        assert alerts_resp.status_code == 200
        initial_alerts = alerts_resp.json()
        print(f"\n[5] GET /alerts (Initial): {len(initial_alerts)} alerts present")

        # 6. POST /detection/run (First execution)
        print(f"\n[6] Calling POST /detection/run (First Run)...")
        det_resp_1 = client.post("/detection/run")
        assert det_resp_1.status_code == 200
        det_data_1 = det_resp_1.json()
        print(f"    Status:          {det_data_1['status']}")
        print(f"    Alerts Created:  {det_data_1['alerts_created']}")
        print(f"    Alerts Existing: {det_data_1['alerts_existing']}")
        print(f"    Detector Summary:")
        for det_name, det_info in det_data_1['detectors'].items():
            print(f"      - {det_name}: {det_info['events_detected']} events, mapped to '{det_info['mapped_alert_type']}'")
        print(f"    Evaluations Benchmark:")
        for det_name, ev_info in det_data_1['evaluation'].items():
            print(f"      - {det_name}: Precision={ev_info['precision']}, Recall={ev_info['recall']}, F1={ev_info['f1_score']}, TP={ev_info['true_positives']}, FP={ev_info['false_positives']}, FN={ev_info['false_negatives']}")

        # 7. Verify Alerts in Database
        db = SessionLocal()
        count_in_db = db.query(Alert).count()
        db.close()
        print(f"\n[7] Database Alert Count: {count_in_db} alerts persisted in SQLite.")

        # 8. POST /detection/run (Second execution - Duplicate check)
        print(f"\n[8] Calling POST /detection/run (Second Run - Duplicate Prevention)...")
        det_resp_2 = client.post("/detection/run")
        assert det_resp_2.status_code == 200
        det_data_2 = det_resp_2.json()
        print(f"    Alerts Created:  {det_data_2['alerts_created']} (Expected: 0)")
        print(f"    Alerts Existing: {det_data_2['alerts_existing']} (Expected: {det_data_1['alerts_created']})")
        assert det_data_2['alerts_created'] == 0, "Duplicate alerts were created!"
        print("    SUCCESS: Duplicate prevention verified.")

        # 9. Resolve one alert
        active_before_resp = client.get("/alerts?resolved=false")
        active_before = active_before_resp.json()
        assert len(active_before) > 0, "No active alerts to resolve!"
        alert_to_resolve = active_before[0]
        alert_id = alert_to_resolve["id"]

        print(f"\n[9] Resolving Alert ID #{alert_id} (Type: {alert_to_resolve['alert_type']}, Zone: {alert_to_resolve['zone_id']})...")
        resolve_resp = client.patch(f"/alerts/{alert_id}/resolve")
        assert resolve_resp.status_code == 200
        resolved_alert = resolve_resp.json()
        assert resolved_alert["resolved"] is True
        print(f"    Alert #{alert_id} resolved: {resolved_alert['resolved']}")

        # 10. Verify it disappears from active alerts
        active_after_resp = client.get("/alerts?resolved=false")
        active_after = active_after_resp.json()
        print(f"\n[10] Active Alerts Before: {len(active_before)} -> Active Alerts After: {len(active_after)}")
        assert len(active_after) == len(active_before) - 1
        assert not any(a["id"] == alert_id for a in active_after)
        print("     SUCCESS: Resolved alert removed from active alert list.")

        # 11. Re-check summary active alert count
        summary_after = client.get("/summary").json()
        print(f"\n[11] Updated /summary active_alerts: {summary_after['active_alerts']}")
        assert summary_after['active_alerts'] == len(active_after)

    print("\n" + "=" * 60)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
