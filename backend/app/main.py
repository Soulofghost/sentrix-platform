from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.database import init_db
from app.routers import telemetry, operations

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="SENTRIX — Disaster Response & SEM Platform",
    description="Structural & Environmental Monitoring, Seismic PGA Telemetry, and Autonomous Emergency Dispatch Orchestration.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(operations.router, prefix="/api/v1")

@app.get("/api/v1/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "SENTRIX SEM Disaster Platform",
        "version": "1.0.0",
        "capabilities": ["SEISMIC_PGA", "FLOOD_HYDRAULICS", "EVACUATION_ZONING", "EMERGENCY_DISPATCH"]
    }

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
