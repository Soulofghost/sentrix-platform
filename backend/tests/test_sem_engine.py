from app.engine.sem import evaluate_seismic_pga, evaluate_flood_level, haversine_distance_km, rank_dispatch_units

def test_evaluate_seismic_pga_normal():
    res = evaluate_seismic_pga(0.01)
    assert res["alert_level"] == "NORMAL"
    assert res["requires_evacuation"] is False
    assert "II-III" in res["mmi_intensity"]

def test_evaluate_seismic_pga_warning():
    res = evaluate_seismic_pga(0.10)
    assert res["alert_level"] == "WARNING"
    assert res["requires_evacuation"] is False
    assert res["mmi_intensity"] == "V-VI"

def test_evaluate_seismic_pga_critical():
    res = evaluate_seismic_pga(0.40)
    assert res["alert_level"] == "CRITICAL"
    assert res["requires_evacuation"] is True
    assert res["mmi_intensity"] == "IX-XII"
    assert res["estimated_magnitude"] >= 7.0

def test_evaluate_flood_level():
    # Nominal
    nom = evaluate_flood_level(2.0, 5.0, 8.0)
    assert nom["alert_level"] == "NORMAL"
    assert nom["requires_evacuation"] is False

    # Warning
    warn = evaluate_flood_level(6.0, 5.0, 8.0)
    assert warn["alert_level"] == "WARNING"
    assert warn["requires_evacuation"] is False

    # Critical
    crit = evaluate_flood_level(8.5, 5.0, 8.0)
    assert crit["alert_level"] == "CRITICAL"
    assert crit["requires_evacuation"] is True

def test_haversine_distance():
    # San Francisco (37.7749, -122.4194) to Oakland (37.8044, -122.2712) ~ 13.5 km
    dist = haversine_distance_km(37.7749, -122.4194, 37.8044, -122.2712)
    assert 11.0 <= dist <= 16.0

def test_rank_dispatch_units():
    incident_lat = 37.7749
    incident_lon = -122.4194

    units = [
        {"id": "U1", "unit_name": "Far Unit", "latitude": 38.5000, "longitude": -121.5000},
        {"id": "U2", "unit_name": "Close Unit", "latitude": 37.7800, "longitude": -122.4100}
    ]

    ranked = rank_dispatch_units(incident_lat, incident_lon, units)
    assert ranked[0]["id"] == "U2"
    assert ranked[1]["id"] == "U1"
    assert ranked[0]["distance_km"] < ranked[1]["distance_km"]
