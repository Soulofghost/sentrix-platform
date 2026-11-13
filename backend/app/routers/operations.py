import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.database import get_db_connection
from app.schemas import (
    IncidentCreate, IncidentResponse, DispatchUnitResponse, DispatchAssignRequest,
    BroadcastCreate, BroadcastResponse, SituationalOverviewResponse
)
from app.engine.sem import rank_dispatch_units

router = APIRouter(prefix="/operations", tags=["Disaster Operations & Dispatch"])

@router.get("/overview", response_model=SituationalOverviewResponse)
def get_situational_overview():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        active_inc = cursor.execute("SELECT count(*) FROM incidents WHERE status = 'ACTIVE'").fetchone()[0]
        online_sns = cursor.execute("SELECT count(*) FROM sensors WHERE status = 'ONLINE'").fetchone()[0]
        total_events = cursor.execute("SELECT count(*) FROM telemetry_logs").fetchone()[0]
        avail_units = cursor.execute("SELECT count(*) FROM dispatch_units WHERE status = 'AVAILABLE'").fetchone()[0]
        crit_alerts = cursor.execute("SELECT count(*) FROM telemetry_logs WHERE alert_level = 'CRITICAL'").fetchone()[0]
        evac_zones = cursor.execute("SELECT count(*) FROM incidents WHERE evacuation_ordered = 1 AND status = 'ACTIVE'").fetchone()[0]

        return SituationalOverviewResponse(
            active_incidents=active_inc,
            online_sensors=online_sns,
            total_telemetry_events=total_events,
            available_dispatch_units=avail_units,
            critical_alerts_count=crit_alerts,
            evacuation_zones_active=evac_zones
        )

@router.get("/incidents", response_model=List[IncidentResponse])
def get_incidents():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [
            IncidentResponse(
                id=r["id"],
                title=r["title"],
                disaster_type=r["disaster_type"],
                severity=r["severity"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                affected_radius_km=r["affected_radius_km"],
                status=r["status"],
                evacuation_ordered=bool(r["evacuation_ordered"]),
                created_at=r["created_at"]
            )
            for r in rows
        ]

@router.post("/incidents", response_model=IncidentResponse, status_code=201)
def create_incident(req: IncidentCreate):
    inc_id = f"INC-{req.disaster_type[:4].upper()}-{str(uuid.uuid4())[:6].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO incidents (
                id, title, disaster_type, severity, latitude, longitude,
                affected_radius_km, status, evacuation_ordered, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inc_id, req.title.strip(), req.disaster_type.upper(), req.severity.upper(),
            req.latitude, req.longitude, req.affected_radius_km, "ACTIVE",
            1 if req.evacuation_ordered else 0, now_iso
        ))
        conn.commit()

        cursor.execute("SELECT * FROM incidents WHERE id = ?", (inc_id,))
        r = cursor.fetchone()
        return IncidentResponse(
            id=r["id"],
            title=r["title"],
            disaster_type=r["disaster_type"],
            severity=r["severity"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            affected_radius_km=r["affected_radius_km"],
            status=r["status"],
            evacuation_ordered=bool(r["evacuation_ordered"]),
            created_at=r["created_at"]
        )

@router.patch("/incidents/{incident_id}/evacuate", response_model=IncidentResponse)
def toggle_evacuation_order(incident_id: str, order: bool = True):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE incidents SET evacuation_ordered = ? WHERE id = ?", (1 if order else 0, incident_id))
        conn.commit()

        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Incident not found")
        return IncidentResponse(
            id=r["id"],
            title=r["title"],
            disaster_type=r["disaster_type"],
            severity=r["severity"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            affected_radius_km=r["affected_radius_km"],
            status=r["status"],
            evacuation_ordered=bool(r["evacuation_ordered"]),
            created_at=r["created_at"]
        )

@router.get("/dispatch/units", response_model=List[DispatchUnitResponse])
def get_dispatch_units(incident_id: Optional[str] = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dispatch_units ORDER BY status ASC, id ASC")
        units = [dict(r) for r in cursor.fetchall()]

        if incident_id:
            cursor.execute("SELECT latitude, longitude FROM incidents WHERE id = ?", (incident_id,))
            inc = cursor.fetchone()
            if inc:
                ranked = rank_dispatch_units(inc["latitude"], inc["longitude"], units)
                return [DispatchUnitResponse(**u) for u in ranked]

        return [DispatchUnitResponse(**u) for u in units]

@router.post("/dispatch/assign", response_model=DispatchUnitResponse)
def assign_dispatch_unit(req: DispatchAssignRequest):
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dispatch_units WHERE id = ?", (req.unit_id,))
        unit = cursor.fetchone()
        if not unit:
            raise HTTPException(status_code=404, detail="Dispatch unit not found")

        cursor.execute("SELECT * FROM incidents WHERE id = ?", (req.incident_id,))
        inc = cursor.fetchone()
        if not inc:
            raise HTTPException(status_code=404, detail="Incident not found")

        cursor.execute("""
            UPDATE dispatch_units
            SET status = 'DEPLOYED', assigned_incident_id = ?, updated_at = ?
            WHERE id = ?
        """, (req.incident_id, now_iso, req.unit_id))
        conn.commit()

        cursor.execute("SELECT * FROM dispatch_units WHERE id = ?", (req.unit_id,))
        updated = cursor.fetchone()
        return DispatchUnitResponse(**dict(updated))

@router.get("/broadcasts", response_model=List[BroadcastResponse])
def get_broadcasts():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM emergency_broadcasts ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [BroadcastResponse(**dict(r)) for r in rows]

@router.post("/broadcasts", response_model=BroadcastResponse, status_code=201)
def create_broadcast(req: BroadcastCreate):
    b_id = "BRD-" + str(uuid.uuid4())[:8].upper()
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO emergency_broadcasts (id, incident_id, alert_level, headline, instructions, broadcast_channel, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (b_id, req.incident_id, req.alert_level.upper(), req.headline.strip(), req.instructions.strip(), req.broadcast_channel.strip(), now_iso))
        conn.commit()

        cursor.execute("SELECT * FROM emergency_broadcasts WHERE id = ?", (b_id,))
        r = cursor.fetchone()
        return BroadcastResponse(**dict(r))
