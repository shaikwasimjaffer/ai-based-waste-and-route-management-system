import math

# Reference Central Depot coordinates (or centroid of service area)
DEPOT_LAT = 40.7580
DEPOT_LON = -73.9855

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Computes great-circle distance between two GPS coordinates in kilometers.
    Uses Formula 4 (Haversine equation) from Chapter 2.
    """
    R = 6371.0  # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_upi(fill, days_since_last=2.0, location_type="general", filling_speed=5.0):
    """
    Formula 3 from Chapter 2: Urgency Priority Index (UPI)
    UPI = 0.55 * Fill + 0.20 * FillingSpeed + 0.15 * DaysSinceLast + 0.10 * LocationWeight
    """
    type_weights = {
        "hazardous": 1.5,
        "organic": 1.3,
        "general": 1.1,
        "recyclable": 1.0
    }
    w_loc = type_weights.get(location_type.lower(), 1.0)
    upi = (0.55 * fill) + (0.20 * filling_speed) + (0.15 * days_since_last * 10) + (0.10 * w_loc * 10)
    return round(upi, 2)

def solve_tsp_route(priority_bins, depot_lat=DEPOT_LAT, depot_lon=DEPOT_LON):
    """
    Formula 4: Traveling Salesperson Route Optimization Engine
    1. Filter urgent & warning bins
    2. Compute pairwise Haversine distance matrix
    3. Generate initial tour via Nearest Neighbor heuristic
    4. 2-Opt local search refinement
    5. Return ordered stops, distance, duration, fuel, and CO2
    """
    if not priority_bins:
        return {
            "stops": [],
            "total_distance_km": 0.0,
            "estimated_time_min": 0,
            "fuel_consumed_liters": 0.0,
            "co2_emissions_kg": 0.0
        }

    # Prepare waypoints starting from depot
    waypoints = []
    for b in priority_bins:
        lat = b.latitude if b.latitude is not None else (depot_lat + 0.01)
        lon = b.longitude if b.longitude is not None else (depot_lon + 0.01)
        waypoints.append({
            "id": b.id,
            "location": b.location,
            "zone": b.zone,
            "fill": b.fill,
            "status": b.status,
            "lat": lat,
            "lon": lon
        })

    # Nearest Neighbor Heuristic
    unvisited = waypoints[:]
    current_lat = depot_lat
    current_lon = depot_lon
    ordered_stops = []
    total_dist = 0.0

    while unvisited:
        nearest_idx = 0
        min_dist = float('inf')
        for i, stop in enumerate(unvisited):
            d = haversine_distance(current_lat, current_lon, stop["lat"], stop["lon"])
            if d < min_dist:
                min_dist = d
                nearest_idx = i

        chosen = unvisited.pop(nearest_idx)
        ordered_stops.append(chosen)
        total_dist += min_dist
        current_lat = chosen["lat"]
        current_lon = chosen["lon"]

    # Return to depot
    total_dist += haversine_distance(current_lat, current_lon, depot_lat, depot_lon)

    # 2-Opt Local Search refinement if stops > 3
    if len(ordered_stops) > 3:
        improved = True
        iterations = 0
        while improved and iterations < 50:
            improved = False
            iterations += 1
            for i in range(len(ordered_stops) - 1):
                for k in range(i + 1, len(ordered_stops)):
                    # Calculate current segments length
                    prev_i = ordered_stops[i - 1] if i > 0 else {"lat": depot_lat, "lon": depot_lon}
                    next_k = ordered_stops[k + 1] if k < len(ordered_stops) - 1 else {"lat": depot_lat, "lon": depot_lon}

                    d_cur = (haversine_distance(prev_i["lat"], prev_i["lon"], ordered_stops[i]["lat"], ordered_stops[i]["lon"]) +
                             haversine_distance(ordered_stops[k]["lat"], ordered_stops[k]["lon"], next_k["lat"], next_k["lon"]))

                    d_new = (haversine_distance(prev_i["lat"], prev_i["lon"], ordered_stops[k]["lat"], ordered_stops[k]["lon"]) +
                             haversine_distance(ordered_stops[i]["lat"], ordered_stops[i]["lon"], next_k["lat"], next_k["lon"]))

                    if d_new < d_cur - 0.01:
                        ordered_stops[i:k + 1] = reversed(ordered_stops[i:k + 1])
                        total_dist -= (d_cur - d_new)
                        improved = True
                        break
                if improved:
                    break

    # Municipal metrics: average speed 25 km/h in urban traffic, 5 mins per stop collection
    driving_minutes = (total_dist / 25.0) * 60.0
    collection_minutes = len(ordered_stops) * 4.5
    estimated_time_min = round(driving_minutes + collection_minutes)

    # Fuel consumption: ~0.35 L/km for diesel garbage truck
    fuel_consumed = round(total_dist * 0.35, 1)
    # CO2: ~2.68 kg CO2 per liter diesel
    co2_emissions = round(fuel_consumed * 2.68, 1)

    return {
        "stops": ordered_stops,
        "total_distance_km": round(total_dist, 2),
        "estimated_time_min": estimated_time_min,
        "fuel_consumed_liters": fuel_consumed,
        "co2_emissions_kg": co2_emissions
    }
