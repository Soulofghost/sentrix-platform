import math
from typing import Dict, Any, List

def evaluate_seismic_pga(pga_g: float) -> Dict[str, Any]:
    """
    Evaluates Peak Ground Acceleration (PGA in units of g) into Modified Mercalli Intensity
    and structural integrity threat level.
    """
    if pga_g < 0.005:
        mmi = "I"
        desc = "Not felt except by very few under especially favorable conditions."
        alert_level = "NORMAL"
        richter_est = round(max(1.0, pga_g * 100), 1)
    elif pga_g < 0.02:
        mmi = "II-III"
        desc = "Felt by persons at rest, especially on upper floors of buildings."
        alert_level = "NORMAL"
        richter_est = 3.2
    elif pga_g < 0.05:
        mmi = "IV"
        desc = "Felt indoors by many. Dishes and doors disturbed."
        alert_level = "NORMAL"
        richter_est = 4.1
    elif pga_g < 0.15:
        mmi = "V-VI"
        desc = "Felt by all. Structural tremor noticeable, plaster cracked, chimneys broken."
        alert_level = "WARNING"
        richter_est = 5.2
    elif pga_g < 0.35:
        mmi = "VII-VIII"
        desc = "Damage slight in specially designed structures; considerable in ordinary substantial buildings."
        alert_level = "CRITICAL"
        richter_est = 6.4
    else:
        mmi = "IX-XII"
        desc = "Disastrous. Ground cracked, pipes ruptured, structural frame distortion or collapse imminent."
        alert_level = "CRITICAL"
        richter_est = 7.5

    return {
        "pga_g": pga_g,
        "mmi_intensity": mmi,
        "description": desc,
        "alert_level": alert_level,
        "estimated_magnitude": richter_est,
        "requires_evacuation": pga_g >= 0.20
    }

def evaluate_flood_level(current_meters: float, warning_m: float, critical_m: float) -> Dict[str, Any]:
    """
    Evaluates water level telematics against hydraulic thresholds.
    """
    if current_meters >= critical_m:
        alert_level = "CRITICAL"
        risk_desc = "Reservoir / Flume Overflow Imminent or Active"
        requires_evac = True
    elif current_meters >= warning_m:
        alert_level = "WARNING"
        risk_desc = "Hydraulic Stage Warning — Bankfull Discharge Imminent"
        requires_evac = False
    else:
        alert_level = "NORMAL"
        risk_desc = "Channel capacity nominal"
        requires_evac = False

    capacity_pct = round((current_meters / critical_m) * 100, 1) if critical_m > 0 else 0.0

    return {
        "current_meters": current_meters,
        "warning_threshold_m": warning_m,
        "critical_threshold_m": critical_m,
        "capacity_percentage": min(capacity_pct, 150.0),
        "alert_level": alert_level,
        "description": risk_desc,
        "requires_evacuation": requires_evac
    }

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two decimal coordinates in kilometers.
    """
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def rank_dispatch_units(incident_lat: float, incident_lon: float, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks available emergency units by geographical proximity to incident coordinates.
    """
    ranked = []
    for u in units:
        dist = haversine_distance_km(incident_lat, incident_lon, u["latitude"], u["longitude"])
        ranked.append({
            **u,
            "distance_km": dist,
            "estimated_eta_min": max(2, int(dist * 2.5)) # approx 2.5 min per km urban transit
        })

    return sorted(ranked, key=lambda x: x["distance_km"])
