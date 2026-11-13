import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from app.config import SQLITE_DB_PATH

_memory_conn = None

def get_db_connection() -> sqlite3.Connection:
    global _memory_conn
    if SQLITE_DB_PATH == ":memory:":
        if _memory_conn is None:
            _memory_conn = sqlite3.connect("file:sentrix_mem?mode=memory&cache=shared", uri=True, check_same_thread=False)
            _memory_conn.row_factory = sqlite3.Row
        return _memory_conn

    db_path = Path(SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                location_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ONLINE',
                warning_threshold REAL NOT NULL,
                critical_threshold REAL NOT NULL,
                unit TEXT NOT NULL,
                last_reading REAL,
                updated_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id TEXT PRIMARY KEY,
                sensor_id TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                is_alert INTEGER NOT NULL DEFAULT 0,
                alert_level TEXT NOT NULL DEFAULT 'NORMAL',
                created_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                disaster_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                affected_radius_km REAL NOT NULL DEFAULT 5.0,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                evacuation_ordered INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_units (
                id TEXT PRIMARY KEY,
                unit_name TEXT NOT NULL,
                unit_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'AVAILABLE',
                assigned_incident_id TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 10,
                updated_at TEXT NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_broadcasts (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                alert_level TEXT NOT NULL,
                headline TEXT NOT NULL,
                instructions TEXT NOT NULL,
                broadcast_channel TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_created ON telemetry_logs (created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_sensor ON telemetry_logs (sensor_id);")

        # Seed initial sensors if empty
        sensor_cnt = cursor.execute("SELECT count(*) FROM sensors").fetchone()[0]
        now_iso = datetime.now(timezone.utc).isoformat()

        if sensor_cnt == 0:
            initial_sensors = [
                ("SNS-SEISMIC-01", "Bay Bridge North Pier Accelerometer", "SEISMIC", 37.7983, -122.3778, "San Francisco Bay Pier 3", "ONLINE", 0.15, 0.35, "g", 0.02, now_iso),
                ("SNS-SEISMIC-02", "Transamerica Pyramid Core Triaxial", "SEISMIC", 37.7952, -122.4028, "Financial District", "ONLINE", 0.12, 0.30, "g", 0.015, now_iso),
                ("SNS-FLOOD-01", "Delta Basin River Level Telematics", "FLOOD", 37.8200, -122.2500, "Oakland Estuary Canal", "ONLINE", 4.5, 6.2, "m", 2.8, now_iso),
                ("SNS-FLOOD-02", "Crystal Springs Reservoir Stage Gauge", "FLOOD", 37.5250, -122.3600, "Lower Dam Flume", "ONLINE", 12.0, 15.5, "m", 8.4, now_iso),
                ("SNS-FIRE-01", "Diablo Ridge Wildfire Thermal Scanner", "WILDFIRE", 37.8816, -121.9142, "Mount Diablo Sector 4", "ONLINE", 48.0, 65.0, "C", 26.5, now_iso),
            ]

            cursor.executemany("""
                INSERT INTO sensors (id, name, sensor_type, latitude, longitude, location_name, status, warning_threshold, critical_threshold, unit, last_reading, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, initial_sensors)

        # Seed initial dispatch units if empty
        unit_cnt = cursor.execute("SELECT count(*) FROM dispatch_units").fetchone()[0]
        if unit_cnt == 0:
            initial_units = [
                ("UNIT-USAR-ALPHA", "Urban Search & Rescue Alpha", "SAR", "AVAILABLE", None, 37.7749, -122.4194, 25, now_iso),
                ("UNIT-MEDEVAC-1", "Rapid Air Medical Evac 1", "MEDICAL", "AVAILABLE", None, 37.7833, -122.4167, 4, now_iso),
                ("UNIT-HAZMAT-4", "Industrial Containment Hazmat 4", "HAZMAT", "AVAILABLE", None, 37.8044, -122.2712, 12, now_iso),
                ("UNIT-FIRE-TOWER-7", "Structural Collapse Fire Battalion 7", "FIRE", "AVAILABLE", None, 37.7690, -122.4467, 18, now_iso)
            ]
            cursor.executemany("""
                INSERT INTO dispatch_units (id, unit_name, unit_type, status, assigned_incident_id, latitude, longitude, capacity, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, initial_units)

        # Seed initial sample incident
        inc_cnt = cursor.execute("SELECT count(*) FROM incidents").fetchone()[0]
        if inc_cnt == 0:
            cursor.execute("""
                INSERT INTO incidents (id, title, disaster_type, severity, latitude, longitude, affected_radius_km, status, evacuation_ordered, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "INC-SEIS-001",
                "Seismic Tremor & Pier Vibration Anomaly",
                "EARTHQUAKE",
                "HIGH",
                37.7983,
                -122.3778,
                7.5,
                "ACTIVE",
                1,
                now_iso
            ))

        conn.commit()
