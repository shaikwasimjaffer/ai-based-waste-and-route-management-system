from datetime import datetime
from backend.models import Bin, ActivityLog

def calculate_status(fill):
    """Status logic: urgent >= 85%, warning >= 65%, normal < 65%"""
    if fill >= 85:
        return "urgent"
    elif fill >= 65:
        return "warning"
    return "normal"

def execute_live_status_sync_trigger(db, bin_obj, new_fill_pct, raw_distance=None):
    """
    Trigger 1 from Section 3.6: Live Status Synchronization Trigger
    Fires on sensor telemetry reception.
    Updates bin fill, determines urgency tier, and creates activity notifications.
    """
    old_fill = bin_obj.fill
    old_status = bin_obj.status

    bin_obj.fill = max(0.0, min(100.0, float(new_fill_pct)))
    new_status = calculate_status(bin_obj.fill)
    bin_obj.status = new_status
    bin_obj.collected = False
    bin_obj.updated_at = datetime.utcnow()

    # Log significant status changes to activity stream
    if new_status == "urgent" and old_status != "urgent":
        activity = ActivityLog(
            icon="!",
            title="High fill detected",
            detail=f"{bin_obj.id} reached {round(bin_obj.fill)}% fill level",
            created_at=datetime.utcnow()
        )
        db.add(activity)
    elif new_status == "warning" and old_status == "normal":
        activity = ActivityLog(
            icon="◐",
            title="Warning threshold reached",
            detail=f"{bin_obj.id} at {round(bin_obj.fill)}% ({bin_obj.location})",
            created_at=datetime.utcnow()
        )
        db.add(activity)

    return bin_obj

def execute_collection_audit_and_reset_trigger(db, bin_obj, worker_id, location, notes=""):
    """
    Trigger 2 from Section 3.6: Collection Audit and Reset Trigger
    Fires when sanitation worker records bin collection.
    Resets bin fill to 0.00%, restores status to 'normal', marks collected=True.
    """
    fill_before = bin_obj.fill

    bin_obj.fill = 0.0
    bin_obj.status = "normal"
    bin_obj.collected = True
    bin_obj.updated_at = datetime.utcnow()

    # Log collection activity
    activity = ActivityLog(
        icon="✓",
        title="Collection completed",
        detail=f"{bin_obj.id} collected by {worker_id} from {bin_obj.location}",
        created_at=datetime.utcnow()
    )
    db.add(activity)

    return bin_obj, fill_before
