from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SensorCreate(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Bay Bridge South Pier Accelerometer"})
    sensor_type: str = Field(..., json_schema_extra={"example": "SEISMIC"})
    latitude: float = Field(..., json_schema_extra={"example": 37.7983})
    longitude: float = Field(..., json_schema_extra={"example": -122.3778})
    location_name: str = Field(..., json_schema_extra={"example": "Pier 4 Foundation"})
    warning_threshold: float = Field(..., json_schema_extra={"example": 0.15})
    critical_threshold: float = Field(..., json_schema_extra={"example": 0.35})
    unit: str = Field(..., json_schema_extra={"example": "g"})

class SensorResponse(BaseModel):
    id: str
    name: str
    sensor_type: str
    latitude: float
    longitude: float
    location_name: str
    status: str
    warning_threshold: float
    critical_threshold: float
    unit: str
    last_reading: Optional[float] = None
    updated_at: str

class TelemetryIngestRequest(BaseModel):
    sensor_id: str
    value: float
    metric_name: Optional[str] = "reading"

class TelemetryIngestResponse(BaseModel):
    log_id: str
    sensor_id: str
    value: float
    unit: str
    is_alert: bool
    alert_level: str
    assessment: Dict[str, Any]
    created_at: str

class IncidentCreate(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Structural Shift at North Spire"})
    disaster_type: str = Field(..., json_schema_extra={"example": "EARTHQUAKE"})
    severity: str = Field("HIGH", json_schema_extra={"example": "HIGH"})
    latitude: float
    longitude: float
    affected_radius_km: float = 5.0
    evacuation_ordered: bool = False

class IncidentResponse(BaseModel):
    id: str
    title: str
    disaster_type: str
    severity: str
    latitude: float
    longitude: float
    affected_radius_km: float
    status: str
    evacuation_ordered: bool
    created_at: str

class DispatchUnitResponse(BaseModel):
    id: str
    unit_name: str
    unit_type: str
    status: str
    assigned_incident_id: Optional[str] = None
    latitude: float
    longitude: float
    capacity: int
    distance_km: Optional[float] = None
    estimated_eta_min: Optional[int] = None
    updated_at: str

class DispatchAssignRequest(BaseModel):
    incident_id: str
    unit_id: str

class BroadcastCreate(BaseModel):
    incident_id: str
    alert_level: str
    headline: str
    instructions: str
    broadcast_channel: str = "ALL_CIVIL_CHANNELS"

class BroadcastResponse(BaseModel):
    id: str
    incident_id: str
    alert_level: str
    headline: str
    instructions: str
    broadcast_channel: str
    created_at: str

class SituationalOverviewResponse(BaseModel):
    active_incidents: int
    online_sensors: int
    total_telemetry_events: int
    available_dispatch_units: int
    critical_alerts_count: int
    evacuation_zones_active: int
