"""Drop-in FastAPI router for the LUNA SHIFT Education section.

Mount with:
    from backend.education_missions import router as education_router
    app.include_router(education_router)

This module reads the published SQLite catalog. It never calls the professional
polar DEM or SPICE engine, because these landings are outside the polar DEM.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "education" / "lunar_missions.sqlite"
router = APIRouter(prefix="/api/education", tags=["Education - NASA Lunar Landings"])


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail="Education database not found. Copy data/education/lunar_missions.sqlite into the project.",
        )
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def dataset_info(conn: sqlite3.Connection) -> dict:
    return {
        row["key"]: json.loads(row["value_json"])
        for row in conn.execute("SELECT key, value_json FROM dataset_metadata")
    }


def mission_row_to_dict(row: sqlite3.Row, conn: sqlite3.Connection) -> dict:
    mission = dict(row)
    mission["topics"] = json.loads(mission.pop("topics_json"))
    ref_rows = conn.execute(
        """SELECT ms.fact_role, s.id, s.title, s.url, s.publisher
           FROM mission_sources ms JOIN sources s ON s.id = ms.source_id
           WHERE ms.mission_id = ? ORDER BY ms.fact_role, s.id""",
        (mission["id"],),
    ).fetchall()
    mission["sources"] = [dict(item) for item in ref_rows]
    return mission


@router.get("/metadata")
def get_missions_metadata():
    with get_connection() as conn:
        return dataset_info(conn)


@router.get("/missions")
def list_missions(mission_type: str | None = Query(None, pattern="^(robotic_lander|crewed_landing)$")):
    with get_connection() as conn:
        base = dataset_info(conn)
        if mission_type:
            rows = conn.execute(
                "SELECT * FROM missions WHERE mission_type = ? ORDER BY landing_date_utc",
                (mission_type,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM missions ORDER BY landing_date_utc").fetchall()
        items = [mission_row_to_dict(row, conn) for row in rows]
        return {
            "dataset_id": base["dataset_id"],
            "version": base["version"],
            "coordinate_convention": base["coordinate_convention"],
            "count": len(items),
            "missions": items,
        }


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="NASA lunar landing mission not found.")
        return mission_row_to_dict(row, conn)
