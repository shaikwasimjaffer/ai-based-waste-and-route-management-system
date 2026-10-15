import os
import json
from datetime import datetime, timedelta
import pandas as pd
from backend.database import engine, SessionLocal, Base
from backend.models import Bin, Worker, SensorData, CollectionHistory, RoutePlan, ActivityLog
from backend.triggers import calculate_status

DEFAULT_BINS_JS = [
    {"id": "B001", "sensor": "S001", "location": "Market Road", "zone": "Zone A", "fill": 94, "status": "urgent"},
    {"id": "B002", "sensor": "S002", "location": "College Road", "zone": "Zone A", "fill": 87, "status": "urgent"},
    {"id": "B003", "sensor": "S003", "location": "Bus Station", "zone": "Zone B", "fill": 76, "status": "warning"},
    {"id": "B004", "sensor": "S004", "location": "Main Street", "zone": "Zone B", "fill": 68, "status": "warning"},
    {"id": "B005", "sensor": "S005", "location": "Park Avenue", "zone": "Zone C", "fill": 91, "status": "urgent"},
    {"id": "B006", "sensor": "S006", "location": "Railway Road", "zone": "Zone C", "fill": 52, "status": "normal"},
    {"id": "B007", "sensor": "S007", "location": "Hospital Road", "zone": "Zone D", "fill": 89, "status": "urgent"},
    {"id": "B008", "sensor": "S008", "location": "Temple Street", "zone": "Zone D", "fill": 42, "status": "normal"},
    {"id": "B009", "sensor": "S009", "location": "City Center", "zone": "Zone A", "fill": 71, "status": "warning"},
    {"id": "B010", "sensor": "S010", "location": "Lake Road", "zone": "Zone B", "fill": 29, "status": "normal"},
    {"id": "B011", "sensor": "S011", "location": "Stadium Road", "zone": "Zone C", "fill": 63, "status": "normal"},
    {"id": "B012", "sensor": "S012", "location": "Residential Block", "zone": "Zone D", "fill": 82, "status": "warning"},
    {"id": "B013", "sensor": "S013", "location": "Central Market", "zone": "Zone A", "fill": 47, "status": "normal"},
    {"id": "B014", "sensor": "S014", "location": "Library Road", "zone": "Zone B", "fill": 38, "status": "normal"},
    {"id": "B015", "sensor": "S015", "location": "Industrial Area", "zone": "Zone C", "fill": 73, "status": "warning"},
    {"id": "B016", "sensor": "S016", "location": "Old Town", "zone": "Zone D", "fill": 56, "status": "normal"},
    {"id": "B017", "sensor": "S017", "location": "Shopping Complex", "zone": "Zone A", "fill": 96, "status": "urgent"},
    {"id": "B018", "sensor": "S018", "location": "School Road", "zone": "Zone B", "fill": 61, "status": "normal"},
    {"id": "B019", "sensor": "S019", "location": "Green Park", "zone": "Zone C", "fill": 34, "status": "normal"},
    {"id": "B020", "sensor": "S020", "location": "Bus Depot", "zone": "Zone D", "fill": 79, "status": "warning"},
    {"id": "B021", "sensor": "S021", "location": "Food Street", "zone": "Zone A", "fill": 58, "status": "normal"},
    {"id": "B022", "sensor": "S022", "location": "University Road", "zone": "Zone B", "fill": 86, "status": "urgent"},
    {"id": "B023", "sensor": "S023", "location": "Garden Road", "zone": "Zone C", "fill": 44, "status": "normal"},
    {"id": "B024", "sensor": "S024", "location": "Town Hall", "zone": "Zone D", "fill": 69, "status": "warning"}
]

DEFAULT_HISTORY_JS = [
    {"id": "C008", "bin": "B030", "worker": "Worker 02", "location": "Market Area", "time": "09:20 AM", "status": "Complete"},
    {"id": "C007", "bin": "B029", "worker": "Worker 01", "location": "Station Road", "time": "09:05 AM", "status": "Complete"},
    {"id": "C006", "bin": "B027", "worker": "Worker 03", "location": "City Center", "time": "08:48 AM", "status": "Complete"},
    {"id": "C005", "bin": "B026", "worker": "Worker 04", "location": "Park Road", "time": "08:32 AM", "status": "Complete"},
    {"id": "C004", "bin": "B025", "worker": "Worker 01", "location": "Hospital Road", "time": "08:15 AM", "status": "Complete"},
    {"id": "C003", "bin": "B024", "worker": "Worker 02", "location": "Town Hall", "time": "08:02 AM", "status": "Complete"},
    {"id": "C002", "bin": "B023", "worker": "Worker 03", "location": "Garden Road", "time": "07:45 AM", "status": "Complete"},
    {"id": "C001", "bin": "B022", "worker": "Worker 04", "location": "University Road", "time": "07:30 AM", "status": "Complete"}
]

DEFAULT_ACTIVITIES_JS = [
    {"icon": "!", "title": "High fill detected", "detail": "B017 reached 96% fill level", "time_min_ago": 2},
    {"icon": "↗", "title": "Route generated", "detail": "5 priority collection stops", "time_min_ago": 8},
    {"icon": "✓", "title": "Collection completed", "detail": "B030 collected by Worker 02", "time_min_ago": 18},
    {"icon": "◉", "title": "Sensor update", "detail": "24 bins synchronized", "time_min_ago": 25}
]

def parse_iso_or_default(dt_str, default=None):
    if pd.isna(dt_str) or not str(dt_str).strip():
        return default
    try:
        return datetime.fromisoformat(str(dt_str))
    except Exception:
        return default

def seed_database():
    print("[Seed] Creating database tables if not existing...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_bins_count = db.query(Bin).count()
        if existing_bins_count > 0:
            print(f"[Seed] Database already contains {existing_bins_count} bins. Skipping re-seed.")
            return

        print("[Seed] Seeding municipal workers...")
        # 1. Seed standard workers
        workers_data = [
            Worker(id="Worker 01", badge_number="EMP-0101", full_name="Rajesh Kumar", phone_number="+91 98480 12341", assigned_truck_id="TRUCK-A1", vehicle_type="electric", shift_status="On Shift"),
            Worker(id="Worker 02", badge_number="EMP-0102", full_name="Suresh Rao", phone_number="+91 98480 12342", assigned_truck_id="TRUCK-B2", vehicle_type="hybrid", shift_status="On Shift"),
            Worker(id="Worker 03", badge_number="EMP-0103", full_name="Anil Reddy", phone_number="+91 98480 12343", assigned_truck_id="TRUCK-C3", vehicle_type="diesel", shift_status="On Shift"),
            Worker(id="Worker 04", badge_number="EMP-0104", full_name="Mohan Lal", phone_number="+91 98480 12344", assigned_truck_id="TRUCK-D4", vehicle_type="diesel", shift_status="On Shift"),
        ]
        for w in workers_data:
            db.merge(w)

        # 2. Seed Default 24 Bins (B001 - B024)
        print("[Seed] Seeding default 24 prototype bins (B001 - B024)...")
        now = datetime.utcnow()
        for i, item in enumerate(DEFAULT_BINS_JS):
            # assign spread coordinates around municipal center
            lat = 40.7128 + ((i % 5) * 0.015)
            lon = -74.0060 + (((i // 5) % 5) * 0.015)
            b = Bin(
                id=item["id"],
                sensor_id=item["sensor"],
                location=item["location"],
                zone=item["zone"],
                fill=float(item["fill"]),
                status=item["status"],
                latitude=lat,
                longitude=lon,
                capacity_liters=240,
                height_cm=100.0,
                battery_level=round(92.0 - (i * 1.5), 1),
                collected=False,
                updated_at=now - timedelta(minutes=(i * 3))
            )
            db.add(b)

            # Add sensor telemetry log
            raw_dist = 100.0 - (item["fill"] * 0.95)
            s_log = SensorData(
                bin_id=item["id"],
                raw_distance_cm=raw_dist,
                calculated_fill_pct=item["fill"],
                battery_voltage=3.85,
                temperature_celsius=26.5,
                timestamp=now - timedelta(minutes=(i * 3))
            )
            db.add(s_log)

        # 3. Read and Ingest Excel Dataset
        excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "smart-waste-collection-route-optimizer.xlsx")
        if os.path.exists(excel_path):
            print(f"[Seed] Loading Excel dataset from {excel_path}...")
            df = pd.read_excel(excel_path)
            print(f"[Seed] Ingesting {len(df)} records from Excel dataset...")

            zones_cycle = ["Zone A", "Zone B", "Zone C", "Zone D"]

            for idx, row in df.iterrows():
                driver_id = str(row["driver_id"]).strip()
                # Create worker if not exists
                worker = db.query(Worker).filter_by(id=driver_id).first()
                if not worker:
                    worker = Worker(
                        id=driver_id,
                        badge_number=f"EMP-{driver_id}",
                        full_name=f"Driver {driver_id}",
                        phone_number="+91 98000 00000",
                        assigned_truck_id=str(row["vehicle_id"]).strip(),
                        vehicle_type=str(row["vehicle_type"]).strip(),
                        shift_status="On Shift"
                    )
                    db.add(worker)
                    db.flush()

                # Bin
                b_id = str(row["bin_id"]).strip()
                fill_pct = float(row["bin_fill_level_percent"]) if not pd.isna(row["bin_fill_level_percent"]) else 50.0
                status = calculate_status(fill_pct)
                assigned_zone = zones_cycle[idx % len(zones_cycle)]

                bin_obj = db.query(Bin).filter_by(id=b_id).first()
                if not bin_obj:
                    bin_obj = Bin(
                        id=b_id,
                        sensor_id=f"S{b_id[1:] if len(b_id) > 1 else '00'}",
                        location=str(row["bin_address_street"]).strip(),
                        street_address=str(row["bin_address_street"]).strip(),
                        city=str(row["bin_address_city"]).strip(),
                        state=str(row["bin_address_state"]).strip(),
                        postal_code=str(row["bin_address_postal_code"]).strip(),
                        country=str(row["bin_address_country"]).strip(),
                        zone=assigned_zone,
                        bin_type=str(row["bin_type"]).strip(),
                        latitude=float(row["bin_location_latitude"]),
                        longitude=float(row["bin_location_longitude"]),
                        fill=fill_pct,
                        status=status,
                        capacity_liters=240,
                        height_cm=100.0,
                        battery_level=88.5,
                        collected=False,
                        updated_at=parse_iso_or_default(row["bin_last_collected_datetime"], now)
                    )
                    db.add(bin_obj)
                    db.flush()

                # Sensor Data Telemetry
                s_reading = SensorData(
                    bin_id=b_id,
                    raw_distance_cm=max(5.0, 100.0 - fill_pct),
                    calculated_fill_pct=fill_pct,
                    battery_voltage=3.75,
                    temperature_celsius=27.0,
                    timestamp=parse_iso_or_default(row["bin_last_collected_datetime"], now)
                )
                db.add(s_reading)

                # Route Plan
                r_id = str(row["route_id"]).strip()
                route_obj = db.query(RoutePlan).filter_by(id=r_id).first()
                if not route_obj:
                    route_obj = RoutePlan(
                        id=r_id,
                        route_name=str(row["route_name"]).strip(),
                        worker_id=driver_id,
                        generation_time=parse_iso_or_default(row["optimization_timestamp"], now),
                        total_distance_km=float(row["route_distance_km"]) if not pd.isna(row["route_distance_km"]) else 10.0,
                        estimated_time_min=float(row["route_duration_minutes"]) if not pd.isna(row["route_duration_minutes"]) else 45.0,
                        fuel_consumed_liters=float(row["fuel_consumed_liters"]) if not pd.isna(row["fuel_consumed_liters"]) else 3.5,
                        co2_emissions_kg=float(row["co2_emissions_kg"]) if not pd.isna(row["co2_emissions_kg"]) else 9.5,
                        status="Completed" if pd.notna(row["actual_collection_datetime"]) else "Pending",
                        traffic_condition=str(row["traffic_condition"]).strip(),
                        traffic_delay_minutes=float(row["traffic_delay_minutes"]) if not pd.isna(row["traffic_delay_minutes"]) else 0.0,
                        optimized=bool(row["optimized"]) if not pd.isna(row["optimized"]) else True,
                        waypoint_sequence=json.dumps([b_id])
                    )
                    db.add(route_obj)

                # Collection History (if completed in dataset)
                if pd.notna(row["actual_collection_datetime"]):
                    coll_dt = parse_iso_or_default(row["actual_collection_datetime"], now)
                    c_id = f"C{idx+100:04d}"
                    coll_hist = CollectionHistory(
                        id=c_id,
                        bin_id=b_id,
                        worker_id=driver_id,
                        location=str(row["bin_address_street"]).strip(),
                        collection_timestamp=coll_dt,
                        fill_level_before=fill_pct,
                        fill_level_after=0.0,
                        waste_weight_kg=round(fill_pct * 0.45, 1),
                        notes=str(row["notes"]).strip() if pd.notna(row["notes"]) else "Routine collection completed",
                        status="Complete"
                    )
                    db.add(coll_hist)

        # 4. Add UI default collection history records (C001-C008)
        for h in DEFAULT_HISTORY_JS:
            c_hist = CollectionHistory(
                id=h["id"],
                bin_id=h["bin"],
                worker_id=h["worker"],
                location=h["location"],
                collection_timestamp=now - timedelta(hours=int(h["id"][-1])),
                fill_level_before=85.0,
                fill_level_after=0.0,
                waste_weight_kg=35.0,
                notes="Morning scheduled collection",
                status=h["status"]
            )
            db.merge(c_hist)

        # 5. Add Activities
        for a in DEFAULT_ACTIVITIES_JS:
            act = ActivityLog(
                icon=a["icon"],
                title=a["title"],
                detail=a["detail"],
                created_at=now - timedelta(minutes=a["time_min_ago"])
            )
            db.add(act)

        db.commit()
        print(f"[Seed] Successfully seeded database! Bins: {db.query(Bin).count()}, Collections: {db.query(CollectionHistory).count()}, Routes: {db.query(RoutePlan).count()}")

    except Exception as e:
        db.rollback()
        print(f"[Seed Error] Failed to seed database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
