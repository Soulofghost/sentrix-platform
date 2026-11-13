import os
import pytest
from fastapi.testclient import TestClient

# Set in-memory DB for tests
os.environ["SQLITE_DB_PATH"] = ":memory:"

from app.main import app
from app.database import init_db

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()

client = TestClient(app)

def test_health_check():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "SEISMIC_PGA" in data["capabilities"]

def test_situational_overview():
    res = client.get("/api/v1/operations/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["online_sensors"] >= 5
    assert data["available_dispatch_units"] >= 4

def test_sensors_lifecycle_and_telemetry_ingest():
    # 1. List pre-seeded sensors
    res = client.get("/api/v1/telemetry/sensors")
    assert res.status_code == 200
    sensors = res.json()
    assert len(sensors) >= 5

    target_sensor = next(s for s in sensors if s["sensor_type"] == "SEISMIC")
    sensor_id = target_sensor["id"]

    # 2. Ingest normal telemetry
    t_res1 = client.post("/api/v1/telemetry", json={
        "sensor_id": sensor_id,
        "value": 0.02,
        "metric_name": "pga_vibration"
    })
    assert t_res1.status_code == 200
    t_data1 = t_res1.json()
    assert t_data1["is_alert"] is False
    assert t_data1["alert_level"] == "NORMAL"

    # 3. Ingest severe seismic tremor exceeding critical threshold
    t_res2 = client.post("/api/v1/telemetry", json={
        "sensor_id": sensor_id,
        "value": 0.42,
        "metric_name": "pga_vibration"
    })
    assert t_res2.status_code == 200
    t_data2 = t_res2.json()
    assert t_data2["is_alert"] is True
    assert t_data2["alert_level"] == "CRITICAL"
    assert t_data2["assessment"]["requires_evacuation"] is True

    # 4. Check telemetry history
    h_res = client.get(f"/api/v1/telemetry/history?sensor_id={sensor_id}")
    assert h_res.status_code == 200
    history = h_res.json()
    assert len(history) >= 2

def test_incident_and_dispatch_assignment():
    # 1. Create Incident
    inc_res = client.post("/api/v1/operations/incidents", json={
        "title": "East Flume Dam Structural Crack",
        "disaster_type": "FLOOD",
        "severity": "CRITICAL",
        "latitude": 37.8200,
        "longitude": -122.2500,
        "affected_radius_km": 10.0,
        "evacuation_ordered": True
    })
    assert inc_res.status_code == 201
    incident = inc_res.json()
    inc_id = incident["id"]
    assert incident["evacuation_ordered"] is True

    # 2. Query dispatch units ranked by distance
    units_res = client.get(f"/api/v1/operations/dispatch/units?incident_id={inc_id}")
    assert units_res.status_code == 200
    ranked_units = units_res.json()
    assert len(ranked_units) >= 1
    nearest = ranked_units[0]
    assert nearest["distance_km"] is not None

    # 3. Assign nearest unit
    assign_res = client.post("/api/v1/operations/dispatch/assign", json={
        "incident_id": inc_id,
        "unit_id": nearest["id"]
    })
    assert assign_res.status_code == 200
    assigned = assign_res.json()
    assert assigned["status"] == "DEPLOYED"
    assert assigned["assigned_incident_id"] == inc_id

def test_emergency_broadcast():
    # 1. Post emergency broadcast
    b_res = client.post("/api/v1/operations/broadcasts", json={
        "incident_id": "INC-SEIS-001",
        "alert_level": "LEVEL_3_CRITICAL",
        "headline": "MANDATORY EVACUATION: BAY BRIDGE SECTOR 3",
        "instructions": "Seek high ground immediately. Avoid low-lying embankments.",
        "broadcast_channel": "EAS_CIVIL_MOBILE"
    })
    assert b_res.status_code == 201
    broadcast = b_res.json()
    assert broadcast["id"].startswith("BRD-")

    # 2. Get broadcasts
    list_res = client.get("/api/v1/operations/broadcasts")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
