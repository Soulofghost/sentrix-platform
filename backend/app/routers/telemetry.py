import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.database import get_db_connection
from app.schemas import (
    SensorCreate, SensorResponse, TelemetryIngestRequest, TelemetryIngestResponse
)
from app.engine.sem import evaluate_seismic_pga, evaluate_flood_level

router = APIRouter(prefix="/telemetry", tags=["SEM Telemetry & Ingestion"])

@router.get("/sensors", response_model=List[SensorResponse])
def get_sensors():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sensors ORDER BY id ASC")
        rows = cursor.fetchall()
        return [SensorResponse(**dict(r)) for r in rows]

@router.post("/sensors", response_model=SensorResponse, status_code=201)
def create_sensor(req: SensorCreate):
    sensor_id = f"SNS-{req.sensor_type.upper()}-{str(uuid.uuid4())[:6].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sensors (
                id, name, sensor_type, latitude, longitude, location_name,
                status, warning_threshold, critical_threshold, unit, last_reading, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sensor_id, req.name.strip(), req.sensor_type.upper(), req.latitude, req.longitude,
            req.location_name.strip(), "ONLINE", req.warning_threshold, req.critical_threshold,
            req.unit.strip(), None, now_iso
        ))
        conn.commit()

        cursor.execute("SELECT * FROM sensors WHERE id = ?", (sensor_id,))
        r = cursor.fetchone()
        return SensorResponse(**dict(r))

@router.post("", response_model=TelemetryIngestResponse)
def ingest_telemetry(req: TelemetryIngestRequest):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sensors WHERE id = ?", (req.sensor_id,))
        sensor = cursor.fetchone()

        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor not registered in SEM network.")

        sensor_type = sensor["sensor_type"]
        val = req.value
        unit = sensor["unit"]
        warn_th = sensor["warning_threshold"]
        crit_th = sensor["critical_threshold"]

        # Run SEM engine evaluation
        if sensor_type == "SEISMIC":
            assessment = evaluate_seismic_pga(val)
            alert_level = assessment["alert_level"]
        elif sensor_type == "FLOOD":
            assessment = evaluate_flood_level(val, warn_th, crit_th)
            alert_level = assessment["alert_level"]
        else: # e.g. WILDFIRE thermal or generic
            if val >= crit_th:
                alert_level = "CRITICAL"
            elif val >= warn_th:
                alert_level = "WARNING"
            else:
                alert_level = "NORMAL"
            assessment = {
                "value": val,
                "unit": unit,
                "alert_level": alert_level,
                "requires_evacuation": alert_level == "CRITICAL"
            }

        is_alert = 1 if alert_level in ["WARNING", "CRITICAL"] else 0
        log_id = "tel-" + str(uuid.uuid4())[:8]
        now_iso = datetime.now(timezone.utc).isoformat()

        # Update sensor state
        cursor.execute("""
            UPDATE sensors SET last_reading = ?, updated_at = ? WHERE id = ?
        """, (val, now_iso, req.sensor_id))

        # Log telemetry record
        cursor.execute("""
            INSERT INTO telemetry_logs (
                id, sensor_id, sensor_type, metric_name, value, unit, is_alert, alert_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, req.sensor_id, sensor_type, req.metric_name or "reading",
            val, unit, is_alert, alert_level, now_iso
        ))

        conn.commit()

        return TelemetryIngestResponse(
            log_id=log_id,
            sensor_id=req.sensor_id,
            value=val,
            unit=unit,
            is_alert=bool(is_alert),
            alert_level=alert_level,
            assessment=assessment,
            created_at=now_iso
        )

@router.get("/history", response_model=List[dict])
def get_telemetry_history(
    sensor_id: Optional[str] = None,
    alerts_only: bool = False,
    limit: int = Query(50, ge=1, le=200)
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM telemetry_logs WHERE 1=1"
        params = []

        if sensor_id:
            query += " AND sensor_id = ?"
            params.append(sensor_id)
        if alerts_only:
            query += " AND is_alert = 1"

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
