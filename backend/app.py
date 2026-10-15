import os
import json
import random
from datetime import datetime, timezone
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import desc

from backend.config import Config
from backend.database import SessionLocal, active_db_type
from backend.models import Bin, Worker, SensorData, CollectionHistory, RoutePlan, ActivityLog
from backend.triggers import (
    calculate_status,
    execute_live_status_sync_trigger,
    execute_collection_audit_and_reset_trigger
)
from backend.route_optimizer import solve_tsp_route, calculate_upi

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Ensure database is initialized
from backend.seed_data import seed_database
try:
    seed_database()
except Exception as e:
    print(f"[App Init Warning] Could not auto-seed database: {e}")

# =========================================================
# STATIC FILE SERVING
# =========================================================
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    if os.path.exists(os.path.join(BASE_DIR, path)):
        return send_from_directory(BASE_DIR, path)
    return send_from_directory(BASE_DIR, "index.html")

# =========================================================
# API HEALTH & STATUS
# =========================================================
@app.route("/api/health", methods=["GET"])
def health_check():
    db = SessionLocal()
    try:
        bin_count = db.query(Bin).count()
        coll_count = db.query(CollectionHistory).count()
        return jsonify({
            "status": "online",
            "database_engine": active_db_type,
            "total_bins": bin_count,
            "total_collections": coll_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    finally:
        db.close()

# =========================================================
# DASHBOARD API
# =========================================================
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    db = SessionLocal()
    try:
        all_bins = db.query(Bin).all()
        active_bins = [b for b in all_bins if not b.collected]
        urgent_count = len([b for b in active_bins if b.status == "urgent"])
        warning_count = len([b for b in active_bins if b.status == "warning"])
        total_collections = db.query(CollectionHistory).count()

        # Top 7 bins for dashboard table
        sorted_active = sorted(active_bins, key=lambda x: x.fill, reverse=True)
        dashboard_table = [b.to_dict() for b in sorted_active[:7]]

        # Top 5 priority bins
        priority_bins = [
            b.to_dict() for b in sorted_active
            if b.status in ("urgent", "warning")
        ][:5]

        # Area status distribution
        zones = ["Zone A", "Zone B", "Zone C", "Zone D"]
        area_status = []
        for z in zones:
            z_bins = [b for b in all_bins if b.zone == z]
            avg_fill = round(sum(b.fill for b in z_bins) / len(z_bins)) if z_bins else 0
            area_status.append({
                "zone": z,
                "average": avg_fill,
                "count": len(z_bins)
            })

        # Recent activities
        recent_acts = (
            db.query(ActivityLog)
            .order_by(desc(ActivityLog.created_at))
            .limit(5)
            .all()
        )

        return jsonify({
            "stats": {
                "total": len(all_bins),
                "urgent": urgent_count,
                "warning": warning_count,
                "collected": total_collections
            },
            "dashboardTable": dashboard_table,
            "priority": priority_bins,
            "areaStatus": area_status,
            "activities": [a.to_dict() for a in recent_acts]
        })
    finally:
        db.close()

# =========================================================
# BINS API
# =========================================================
@app.route("/api/bins", methods=["GET"])
def get_bins():
    db = SessionLocal()
    try:
        search = request.args.get("search", "").lower().strip()
        status_filter = request.args.get("status", "all")
        area_filter = request.args.get("area", "all")

        query = db.query(Bin)
        bins = query.all()

        filtered = []
        for b in bins:
            # Search filter
            if search:
                match_id = search in b.id.lower()
                match_loc = search in b.location.lower()
                if not (match_id or match_loc):
                    continue

            # Status filter
            if status_filter != "all":
                if status_filter == "collected":
                    if not b.collected:
                        continue
                elif b.collected or b.status != status_filter:
                    continue

            # Area filter
            if area_filter != "all" and b.zone != area_filter:
                continue

            filtered.append(b.to_dict())

        return jsonify(filtered)
    finally:
        db.close()

@app.route("/api/bins/<bin_id>", methods=["GET"])
def get_bin_details(bin_id):
    db = SessionLocal()
    try:
        bin_obj = db.query(Bin).filter_by(id=bin_id).first()
        if not bin_obj:
            return jsonify({"error": "Bin not found"}), 404

        # Recent telemetry
        telemetry = (
            db.query(SensorData)
            .filter_by(bin_id=bin_id)
            .order_by(desc(SensorData.timestamp))
            .limit(10)
            .all()
        )

        data = bin_obj.to_dict()
        data["telemetry_history"] = [t.to_dict() for t in telemetry]
        return jsonify(data)
    finally:
        db.close()

@app.route("/api/bins/<bin_id>/collect", methods=["POST"])
def collect_bin(bin_id):
    db = SessionLocal()
    try:
        bin_obj = db.query(Bin).filter_by(id=bin_id).first()
        if not bin_obj:
            return jsonify({"error": "Bin not found"}), 404

        if bin_obj.collected:
            return jsonify({"message": "Bin already collected", "bin": bin_obj.to_dict()})

        # Worker who collected (default Worker 01 or specified)
        payload = request.get_json(silent=True) or {}
        worker_id = payload.get("worker", "Worker 01")
        notes = payload.get("notes", "Routine collection completed")

        # Execute Trigger 2: Collection Audit and Reset
        bin_obj, fill_before = execute_collection_audit_and_reset_trigger(
            db, bin_obj, worker_id, bin_obj.location, notes
        )

        # Generate collection ID
        coll_count = db.query(CollectionHistory).count()
        coll_id = f"C{coll_count + 1:03d}"

        # Insert immutable Collection History record
        new_coll = CollectionHistory(
            id=coll_id,
            bin_id=bin_obj.id,
            worker_id=worker_id,
            location=bin_obj.location,
            collection_timestamp=datetime.utcnow(),
            fill_level_before=fill_before,
            fill_level_after=0.0,
            waste_weight_kg=round(fill_before * 0.45, 1),
            notes=notes,
            status="Complete"
        )
        db.add(new_coll)
        db.commit()

        return jsonify({
            "success": True,
            "message": f"{bin_obj.id} collected successfully",
            "bin": bin_obj.to_dict(),
            "collection": new_coll.to_dict()
        })
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# =========================================================
# SENSOR SIMULATION & TELEMETRY API
# =========================================================
@app.route("/api/sensors/simulate", methods=["POST"])
def simulate_sensor_readings():
    db = SessionLocal()
    try:
        active_bins = db.query(Bin).filter_by(collected=False).all()
        updated_count = 0
        now = datetime.utcnow()

        for b in active_bins:
            # Simulate realistic delta between -2% and +6%
            delta = random.randint(-2, 6)
            new_fill = max(0.0, min(100.0, b.fill + delta))
            
            # Execute Trigger 1: Live Status Synchronization
            execute_live_status_sync_trigger(db, b, new_fill)

            # Insert into SENSOR_DATA Telemetry Stream
            raw_distance = max(5.0, 100.0 - new_fill)
            reading = SensorData(
                bin_id=b.id,
                raw_distance_cm=raw_distance,
                calculated_fill_pct=new_fill,
                battery_voltage=round(3.7 + (random.random() * 0.25), 2),
                temperature_celsius=round(24.0 + (random.random() * 5.0), 1),
                timestamp=now
            )
            db.add(reading)
            updated_count += 1

        # Activity log
        act = ActivityLog(
            icon="◉",
            title="Sensor update",
            detail=f"{updated_count} bins synchronized with telemetry",
            created_at=now
        )
        db.add(act)

        db.commit()
        return jsonify({
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully synchronized {updated_count} sensors."
        })
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# =========================================================
# ROUTE OPTIMIZATION API (TSP & UPI)
# =========================================================
@app.route("/api/routes", methods=["GET"])
def get_current_route():
    """Read-only: calculates/returns current TSP sequence without altering database."""
    db = SessionLocal()
    try:
        active_bins = (
            db.query(Bin)
            .filter_by(collected=False)
            .filter(Bin.status.in_(["urgent", "warning"]))
            .order_by(desc(Bin.fill))
            .limit(10)
            .all()
        )
        tsp_result = solve_tsp_route(active_bins)
        return jsonify(tsp_result)
    finally:
        db.close()

@app.route("/api/routes/generate", methods=["POST"])
def generate_new_route():
    """Writes a new route optimization plan record only on explicit user request."""
    db = SessionLocal()
    try:
        active_bins = (
            db.query(Bin)
            .filter_by(collected=False)
            .filter(Bin.status.in_(["urgent", "warning"]))
            .order_by(desc(Bin.fill))
            .limit(10)
            .all()
        )
        tsp_result = solve_tsp_route(active_bins)

        if tsp_result["stops"]:
            route_count = db.query(RoutePlan).count()
            r_id = f"R{1000 + route_count + 1}"
            stop_ids = [s["id"] for s in tsp_result["stops"]]

            plan = RoutePlan(
                id=r_id,
                route_name=f"Dynamic Priority Route #{route_count + 1}",
                worker_id="Worker 01",
                generation_time=datetime.utcnow(),
                total_distance_km=tsp_result["total_distance_km"],
                estimated_time_min=tsp_result["estimated_time_min"],
                fuel_consumed_liters=tsp_result["fuel_consumed_liters"],
                co2_emissions_kg=tsp_result["co2_emissions_kg"],
                status="Pending",
                waypoint_sequence=json.dumps(stop_ids)
            )
            db.add(plan)

            act = ActivityLog(
                icon="↗",
                title="Route generated",
                detail=f"{len(tsp_result['stops'])} priority collection stops optimized",
                created_at=datetime.utcnow()
            )
            db.add(act)
            db.commit()
            res = dict(tsp_result)
            res["plan_id"] = r_id
            res["route_name"] = plan.route_name
            res["saved_at"] = datetime.utcnow().strftime("%I:%M %p")
            return jsonify(res)

        return jsonify(tsp_result)
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# =========================================================
# WORKER DISPATCH API
# =========================================================
@app.route("/api/workers", methods=["GET"])
def get_workers():
    db = SessionLocal()
    try:
        worker_id = request.args.get("id", "Worker 01")
        # Assigned priority bins
        assigned_bins = (
            db.query(Bin)
            .filter_by(collected=False)
            .filter(Bin.status.in_(["urgent", "warning"]))
            .order_by(desc(Bin.fill))
            .limit(5)
            .all()
        )

        completed_today = (
            db.query(CollectionHistory)
            .filter_by(worker_id=worker_id)
            .count()
        )

        return jsonify({
            "worker_id": worker_id,
            "metrics": {
                "assigned": len(assigned_bins) + completed_today,
                "completed": completed_today,
                "remaining": len(assigned_bins)
            },
            "tasks": [b.to_dict() for b in assigned_bins]
        })
    finally:
        db.close()

@app.route("/api/workers/list", methods=["GET"])
def get_all_workers():
    db = SessionLocal()
    try:
        workers = db.query(Worker).order_by(Worker.id).all()
        return jsonify([w.to_dict() for w in workers])
    finally:
        db.close()

@app.route("/api/workers", methods=["POST"])
def register_worker():
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        full_name = data.get("name", "").strip()
        if not full_name:
            return jsonify({"error": "Worker full name is required"}), 400

        count = db.query(Worker).count()
        worker_id = data.get("id", "").strip()
        if not worker_id:
            worker_id = f"Worker {count + 1:02d}"

        existing = db.query(Worker).filter_by(id=worker_id).first()
        if existing:
            worker_id = f"Worker {count + 1:02d}"

        new_worker = Worker(
            id=worker_id,
            badge_number=data.get("badge_number") or f"BDG-{1000 + count + 1}",
            full_name=full_name,
            phone_number=data.get("phone") or "+1 (555) 019-2834",
            assigned_zone=data.get("zone", "Zone A"),
            assigned_truck_id=data.get("truck") or f"Truck T-{count % 8 + 1:02d}",
            vehicle_type=data.get("vehicle_type", "diesel"),
            truck_capacity_tons=float(data.get("truck_capacity_tons", 2.5)),
            shift_status=data.get("status", "On Shift"),
            created_at=datetime.utcnow()
        )
        db.add(new_worker)

        act = ActivityLog(
            icon="♙",
            title="Worker Registered",
            detail=f"{new_worker.full_name} ({new_worker.id}) added to {new_worker.assigned_zone}",
            created_at=datetime.utcnow()
        )
        db.add(act)
        db.commit()

        return jsonify({
            "success": True,
            "message": f"Worker {new_worker.full_name} ({new_worker.id}) registered successfully",
            "worker": new_worker.to_dict()
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# =========================================================
# HISTORY API
# =========================================================
@app.route("/api/history", methods=["GET"])
def get_history():
    db = SessionLocal()
    try:
        limit = int(request.args.get("limit", 100))
        records = (
            db.query(CollectionHistory)
            .order_by(desc(CollectionHistory.collection_timestamp))
            .limit(limit)
            .all()
        )
        total_count = db.query(CollectionHistory).count()
        return jsonify({
            "total": total_count,
            "records": [r.to_dict() for r in records]
        })
    finally:
        db.close()

# =========================================================
# ACTIVITIES API
# =========================================================
@app.route("/api/activities", methods=["GET"])
def get_activities():
    db = SessionLocal()
    try:
        activities = (
            db.query(ActivityLog)
            .order_by(desc(ActivityLog.created_at))
            .limit(10)
            .all()
        )
        return jsonify([a.to_dict() for a in activities])
    finally:
        db.close()

if __name__ == "__main__":
    print(f"[*] Starting SmartWaste Flask Backend on port {Config.PORT}...")
    print(f"[*] Active Database Engine: {active_db_type}")
    print(f"[*] Open http://localhost:{Config.PORT} in your browser to view the live application.")
    app.run(host="0.0.0.0", port=Config.PORT, debug=False, use_reloader=False)
