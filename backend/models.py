from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from backend.database import Base

class Bin(Base):
    """
    Table 5 from PBL Final Documentation: BINS Master Table
    Represents smart dustbins with telemetry and geographic status.
    """
    __tablename__ = "bins"

    id = Column(String(50), primary_key=True)  # e.g. "B001", "B3001"
    sensor_id = Column(String(50), nullable=True)  # e.g. "S001"
    location = Column(String(200), nullable=False)
    street_address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(50), nullable=True)
    zone = Column(String(50), nullable=False, default="Zone A")  # "Zone A", "Zone B", "Zone C", "Zone D"
    bin_type = Column(String(50), nullable=False, default="general")  # recyclable, general, organic, hazardous
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity_liters = Column(Integer, default=240)
    height_cm = Column(Float, default=100.0)
    fill = Column(Float, default=0.0)  # Current fill level percentage (0 to 100)
    status = Column(String(20), default="normal")  # "urgent", "warning", "normal", "collected"
    battery_level = Column(Float, default=100.0)
    collected = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    telemetry = relationship("SensorData", back_populates="bin", cascade="all, delete-orphan")
    collections = relationship("CollectionHistory", back_populates="bin", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "sensor": self.sensor_id or f"S{self.id[1:] if len(self.id) > 1 else '01'}",
            "location": self.location,
            "street": self.street_address or self.location,
            "city": self.city or "",
            "state": self.state or "",
            "zone": self.zone,
            "bin_type": self.bin_type,
            "fill": round(float(self.fill), 1),
            "status": self.status,
            "battery_level": round(float(self.battery_level), 1) if self.battery_level else 100.0,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "capacity_liters": self.capacity_liters,
            "height_cm": self.height_cm,
            "updated": self.updated_at.strftime("%I:%M %p") if self.updated_at else "Just now",
            "updated_iso": self.updated_at.isoformat() if self.updated_at else None,
            "collected": self.collected
        }

class Worker(Base):
    """
    Table 7 from PBL Final Documentation: WORKERS Master Table
    Represents sanitation workers and truck drivers.
    """
    __tablename__ = "workers"

    id = Column(String(50), primary_key=True)  # e.g. "Worker 01", "D405"
    badge_number = Column(String(50), unique=True, nullable=True)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(30), nullable=True)
    assigned_truck_id = Column(String(50), nullable=True)
    vehicle_type = Column(String(50), default="diesel")  # diesel, electric, hybrid
    truck_capacity_tons = Column(Float, default=2.5)
    shift_status = Column(String(20), default="On Shift")  # "On Shift", "Off Shift"
    assigned_zone = Column(String(50), default="Zone A")
    created_at = Column(DateTime, default=datetime.utcnow)

    collections = relationship("CollectionHistory", back_populates="worker")
    routes = relationship("RoutePlan", back_populates="worker")

    def to_dict(self):
        return {
            "id": self.id,
            "badge_number": self.badge_number,
            "name": self.full_name,
            "phone": self.phone_number,
            "truck": self.assigned_truck_id,
            "vehicle_type": self.vehicle_type,
            "truck_capacity_tons": self.truck_capacity_tons,
            "status": self.shift_status,
            "zone": self.assigned_zone or "Zone A"
        }

class SensorData(Base):
    """
    Table 6 from PBL Final Documentation: SENSOR_DATA Telemetry Stream Table
    Represents real-time telemetry events from HC-SR04 ultrasonic sensors.
    """
    __tablename__ = "sensor_data"

    reading_id = Column(Integer, primary_key=True, autoincrement=True)
    bin_id = Column(String(50), ForeignKey("bins.id", ondelete="CASCADE"), nullable=False)
    raw_distance_cm = Column(Float, nullable=False)
    calculated_fill_pct = Column(Float, nullable=False)
    battery_voltage = Column(Float, default=3.7)
    temperature_celsius = Column(Float, default=25.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    bin = relationship("Bin", back_populates="telemetry")

    def to_dict(self):
        return {
            "reading_id": self.reading_id,
            "bin_id": self.bin_id,
            "raw_distance_cm": round(float(self.raw_distance_cm), 2),
            "calculated_fill_pct": round(float(self.calculated_fill_pct), 1),
            "battery_voltage": round(float(self.battery_voltage), 2),
            "temperature_celsius": round(float(self.temperature_celsius), 1),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

class CollectionHistory(Base):
    """
    Table 8 from PBL Final Documentation: COLLECTION_HISTORY Transaction Ledger
    Records immutable logs of completed garbage collections.
    """
    __tablename__ = "collection_history"

    id = Column(String(50), primary_key=True)  # e.g. "C001", "C008"
    bin_id = Column(String(50), ForeignKey("bins.id", ondelete="CASCADE"), nullable=False)
    worker_id = Column(String(50), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    location = Column(String(200), nullable=True)
    collection_timestamp = Column(DateTime, default=datetime.utcnow)
    fill_level_before = Column(Float, nullable=True)
    fill_level_after = Column(Float, default=0.0)
    waste_weight_kg = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="Complete")

    bin = relationship("Bin", back_populates="collections")
    worker = relationship("Worker", back_populates="collections")

    def to_dict(self):
        return {
            "id": self.id,
            "bin": self.bin_id,
            "worker": self.worker_id or "Worker 01",
            "location": self.location or (self.bin.location if self.bin else "Central Area"),
            "time": self.collection_timestamp.strftime("%I:%M %p") if self.collection_timestamp else "09:00 AM",
            "timestamp": self.collection_timestamp.isoformat() if self.collection_timestamp else None,
            "fill_level_before": self.fill_level_before,
            "fill_level_after": self.fill_level_after,
            "waste_weight_kg": self.waste_weight_kg,
            "notes": self.notes or "",
            "status": self.status
        }

class RoutePlan(Base):
    """
    Table 9 from PBL Final Documentation: ROUTE_PLANS Optimization Table
    Stores generated and optimized routes calculated by TSP algorithm.
    """
    __tablename__ = "route_plans"

    id = Column(String(50), primary_key=True)  # e.g. "R1001"
    route_name = Column(String(150), nullable=False)
    worker_id = Column(String(50), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True)
    generation_time = Column(DateTime, default=datetime.utcnow)
    total_distance_km = Column(Float, default=0.0)
    estimated_time_min = Column(Float, default=0.0)
    fuel_consumed_liters = Column(Float, default=0.0)
    co2_emissions_kg = Column(Float, default=0.0)
    status = Column(String(50), default="Pending")  # "Pending", "In Progress", "Completed"
    traffic_condition = Column(String(50), default="moderate")
    traffic_delay_minutes = Column(Float, default=0.0)
    optimized = Column(Boolean, default=True)
    waypoint_sequence = Column(Text, nullable=True)  # JSON string of ordered bin IDs

    worker = relationship("Worker", back_populates="routes")

    def to_dict(self):
        import json
        waypoints = []
        if self.waypoint_sequence:
            try:
                waypoints = json.loads(self.waypoint_sequence)
            except Exception:
                waypoints = []
        return {
            "id": self.id,
            "route_name": self.route_name,
            "worker_id": self.worker_id,
            "generation_time": self.generation_time.isoformat() if self.generation_time else None,
            "total_distance_km": round(float(self.total_distance_km), 2),
            "estimated_time_min": round(float(self.estimated_time_min), 1),
            "fuel_consumed_liters": round(float(self.fuel_consumed_liters), 2),
            "co2_emissions_kg": round(float(self.co2_emissions_kg), 2),
            "status": self.status,
            "traffic_condition": self.traffic_condition,
            "traffic_delay_minutes": self.traffic_delay_minutes,
            "optimized": self.optimized,
            "waypoints": waypoints
        }

class ActivityLog(Base):
    """
    System activity stream for dashboard telemetry notifications.
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    icon = Column(String(10), default="◉")
    title = Column(String(100), nullable=False)
    detail = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        # Calculate relative time format
        delta = datetime.utcnow() - (self.created_at or datetime.utcnow())
        mins = int(delta.total_seconds() / 60)
        if mins < 1:
            time_str = "Just now"
        elif mins < 60:
            time_str = f"{mins} min ago"
        elif mins < 1440:
            hours = int(mins / 60)
            time_str = f"{hours}h ago"
        else:
            time_str = self.created_at.strftime("%b %d")

        return {
            "icon": self.icon,
            "title": self.title,
            "detail": self.detail,
            "time": time_str
        }
