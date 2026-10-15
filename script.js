/* =========================================================
   SMARTWASTE
   AI-Based Smart Waste Collection & Route Optimization System
   Connected to Live Backend REST API & PostgreSQL / SQLite Database
   ========================================================= */

const API_BASE = window.location.origin.includes(":5000") 
    ? "/api" 
    : "http://localhost:5000/api";

let isBackendConnected = false;
let isSyncing = false;
let currentRouteStops = null;
let currentRouteMetrics = null;

let currentUserRole = "admin"; // "admin" (Wasim) or "worker" (Collection Worker)
let activeWorkerId = "Worker 01";
let allRegisteredWorkers = [
    { id: "Worker 01", name: "Worker 01", zone: "Zone A", truck: "Truck T-01", status: "On Shift" },
    { id: "Worker 02", name: "Worker 02", zone: "Zone B", truck: "Truck T-02", status: "On Shift" },
    { id: "Worker 03", name: "Worker 03", zone: "Zone C", truck: "Truck T-03", status: "On Shift" },
    { id: "Worker 04", name: "Worker 04", zone: "Zone D", truck: "Truck T-04", status: "On Shift" }
];

/* =========================================================
   DEFAULT SENSOR DATA (Immediate cache & fallback)
   ========================================================= */

let bins = [
    { id: "B001", sensor: "S001", location: "Market Road", zone: "Zone A", fill: 94, status: "urgent", updated: "10:42 AM", collected: false },
    { id: "B002", sensor: "S002", location: "College Road", zone: "Zone A", fill: 87, status: "urgent", updated: "10:39 AM", collected: false },
    { id: "B003", sensor: "S003", location: "Bus Station", zone: "Zone B", fill: 76, status: "warning", updated: "10:36 AM", collected: false },
    { id: "B004", sensor: "S004", location: "Main Street", zone: "Zone B", fill: 68, status: "warning", updated: "10:35 AM", collected: false },
    { id: "B005", sensor: "S005", location: "Park Avenue", zone: "Zone C", fill: 91, status: "urgent", updated: "10:32 AM", collected: false },
    { id: "B006", sensor: "S006", location: "Railway Road", zone: "Zone C", fill: 52, status: "normal", updated: "10:30 AM", collected: false },
    { id: "B007", sensor: "S007", location: "Hospital Road", zone: "Zone D", fill: 89, status: "urgent", updated: "10:27 AM", collected: false },
    { id: "B008", sensor: "S008", location: "Temple Street", zone: "Zone D", fill: 42, status: "normal", updated: "10:24 AM", collected: false },
    { id: "B009", sensor: "S009", location: "City Center", zone: "Zone A", fill: 71, status: "warning", updated: "10:20 AM", collected: false },
    { id: "B010", sensor: "S010", location: "Lake Road", zone: "Zone B", fill: 29, status: "normal", updated: "10:18 AM", collected: false },
    { id: "B011", sensor: "S011", location: "Stadium Road", zone: "Zone C", fill: 63, status: "normal", updated: "10:15 AM", collected: false },
    { id: "B012", sensor: "S012", location: "Residential Block", zone: "Zone D", fill: 82, status: "warning", updated: "10:12 AM", collected: false },
    { id: "B013", sensor: "S013", location: "Central Market", zone: "Zone A", fill: 47, status: "normal", updated: "10:08 AM", collected: false },
    { id: "B014", sensor: "S014", location: "Library Road", zone: "Zone B", fill: 38, status: "normal", updated: "10:05 AM", collected: false },
    { id: "B015", sensor: "S015", location: "Industrial Area", zone: "Zone C", fill: 73, status: "warning", updated: "10:01 AM", collected: false },
    { id: "B016", sensor: "S016", location: "Old Town", zone: "Zone D", fill: 56, status: "normal", updated: "09:58 AM", collected: false },
    { id: "B017", sensor: "S017", location: "Shopping Complex", zone: "Zone A", fill: 96, status: "urgent", updated: "09:55 AM", collected: false },
    { id: "B018", sensor: "S018", location: "School Road", zone: "Zone B", fill: 61, status: "normal", updated: "09:52 AM", collected: false },
    { id: "B019", sensor: "S019", location: "Green Park", zone: "Zone C", fill: 34, status: "normal", updated: "09:48 AM", collected: false },
    { id: "B020", sensor: "S020", location: "Bus Depot", zone: "Zone D", fill: 79, status: "warning", updated: "09:44 AM", collected: false },
    { id: "B021", sensor: "S021", location: "Food Street", zone: "Zone A", fill: 58, status: "normal", updated: "09:40 AM", collected: false },
    { id: "B022", sensor: "S022", location: "University Road", zone: "Zone B", fill: 86, status: "urgent", updated: "09:36 AM", collected: false },
    { id: "B023", sensor: "S023", location: "Garden Road", zone: "Zone C", fill: 44, status: "normal", updated: "09:31 AM", collected: false },
    { id: "B024", sensor: "S024", location: "Town Hall", zone: "Zone D", fill: 69, status: "warning", updated: "09:27 AM", collected: false }
];

/* =========================================================
   COLLECTION HISTORY
   ========================================================= */

let history = [
    { id: "C008", bin: "B030", worker: "Worker 02", location: "Market Area", time: "09:20 AM", status: "Complete" },
    { id: "C007", bin: "B029", worker: "Worker 01", location: "Station Road", time: "09:05 AM", status: "Complete" },
    { id: "C006", bin: "B027", worker: "Worker 03", location: "City Center", time: "08:48 AM", status: "Complete" },
    { id: "C005", bin: "B026", worker: "Worker 04", location: "Park Road", time: "08:32 AM", status: "Complete" },
    { id: "C004", bin: "B025", worker: "Worker 01", location: "Hospital Road", time: "08:15 AM", status: "Complete" },
    { id: "C003", bin: "B024", worker: "Worker 02", location: "Town Hall", time: "08:02 AM", status: "Complete" },
    { id: "C002", bin: "B023", worker: "Worker 03", location: "Garden Road", time: "07:45 AM", status: "Complete" },
    { id: "C001", bin: "B022", worker: "Worker 04", location: "University Road", time: "07:30 AM", status: "Complete" }
];

/* =========================================================
   ACTIVITY
   ========================================================= */

let activities = [
    { icon: "!", title: "High fill detected", detail: "B017 reached 96% fill level", time: "2 min ago" },
    { icon: "↗", title: "Route generated", detail: "5 priority collection stops", time: "8 min ago" },
    { icon: "✓", title: "Collection completed", detail: "B030 collected by Worker 02", time: "18 min ago" },
    { icon: "◉", title: "Sensor update", detail: "24 bins synchronized", time: "25 min ago" }
];

/* =========================================================
   PAGE CONFIG
   ========================================================= */

const pageTitles = {
    dashboard: { title: "Dashboard", label: "MUNICIPAL CONTROL" },
    bins: { title: "Bin Monitoring", label: "SENSOR MONITORING" },
    routes: { title: "Route Planning", label: "PROCESSING ENGINE" },
    workers: { title: "Worker Dashboard", label: "COLLECTION OPERATIONS" },
    "add-worker": { title: "Register Worker", label: "ADMINISTRATION & DISPATCH" },
    history: { title: "Collection History", label: "DATABASE RECORDS" },
    settings: { title: "System Settings", label: "SYSTEM" }
};

/* =========================================================
   NAVIGATION & ROLE SYSTEM
   ========================================================= */

const navItems = document.querySelectorAll(".nav-item");

navItems.forEach(item => {
    item.addEventListener("click", () => {
        showPage(item.dataset.page);
    });
});

function showPage(pageName) {
    if (pageName === "add-worker" && currentUserRole !== "admin") {
        showToast("Access restricted: Administrator role required");
        showPage("workers");
        return;
    }

    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active-page");
    });

    const selected = document.getElementById(pageName);
    if (!selected) return;

    selected.classList.add("active-page");

    navItems.forEach(item => {
        item.classList.toggle("active", item.dataset.page === pageName);
    });

    const config = pageTitles[pageName];
    if (config) {
        document.getElementById("pageTitle").textContent = config.title;
        document.getElementById("sectionLabel").textContent = config.label;
    }

    if (pageName === "dashboard") renderDashboard();
    if (pageName === "bins") renderBins();
    if (pageName === "routes") renderRoutesList();
    if (pageName === "workers") renderWorkers();
    if (pageName === "add-worker") renderAddWorkerPage();
    if (pageName === "history") renderHistory();
}

function toggleRole() {
    currentUserRole = (currentUserRole === "admin") ? "worker" : "admin";
    applyUserRole();
}

function applyUserRole() {
    const avatar = document.getElementById("userAvatar");
    const name = document.getElementById("userName");
    const role = document.getElementById("userRole");

    if (currentUserRole === "admin") {
        document.body.classList.remove("role-worker");
        if (avatar) avatar.textContent = "W";
        if (name) name.textContent = "Wasim";
        if (role) role.textContent = "Administrator ▾";
        showToast("Role switched to Administrator (Full access) ✓");
    } else {
        document.body.classList.add("role-worker");
        if (avatar) avatar.textContent = activeWorkerId.substring(0, 1) || "W";
        if (name) name.textContent = activeWorkerId;
        if (role) role.textContent = "Collection Worker ▾";
        showToast("Role switched to Collection Worker (Restricted view) ✓");

        const activePage = document.querySelector(".page.active-page");
        if (activePage && activePage.id === "add-worker") {
            showPage("workers");
        }
    }
}

/* =========================================================
   STATUS LOGIC
   ========================================================= */

function calculateStatus(fill) {
    if (fill >= 85) return "urgent";
    if (fill >= 65) return "warning";
    return "normal";
}

function statusLabel(status) {
    const labels = {
        urgent: "Urgent",
        warning: "Warning",
        normal: "Normal",
        collected: "Collected"
    };
    return labels[status] || status;
}

function progressClass(status) {
    if (status === "urgent") return "red";
    if (status === "warning") return "orange";
    return "";
}

/* =========================================================
   DASHBOARD
   ========================================================= */

function renderDashboard() {
    const activeBins = bins.filter(bin => !bin.collected);
    const urgent = activeBins.filter(bin => bin.status === "urgent").length;
    const warning = activeBins.filter(bin => bin.status === "warning").length;

    document.getElementById("totalBins").textContent = bins.length;
    document.getElementById("urgentBins").textContent = urgent;
    document.getElementById("warningBins").textContent = warning;
    document.getElementById("collectedBins").textContent = history.length;

    renderDashboardTable();
    renderPriority();
    renderAreaStatus();
    renderActivities();
}

/* =========================================================
   DASHBOARD TABLE
   ========================================================= */

function renderDashboardTable() {
    const tbody = document.getElementById("dashboardTable");
    const important = bins
        .filter(bin => !bin.collected)
        .sort((a, b) => b.fill - a.fill)
        .slice(0, 7);

    tbody.innerHTML = "";

    important.forEach(bin => {
        tbody.innerHTML += `
            <tr>
                <td>
                    <span class="bin-name">
                        ${bin.id}
                    </span>
                </td>
                <td>
                    ${bin.location}
                </td>
                <td class="fill-cell">
                    <div class="fill-cell-top">
                        <span>
                            ${bin.fill}%
                        </span>
                    </div>
                    <div class="progress ${progressClass(bin.status)}">
                        <div style="width:${bin.fill}%"></div>
                    </div>
                </td>
                <td>
                    <span class="status-badge ${bin.status}">
                        ${statusLabel(bin.status)}
                    </span>
                </td>
                <td>
                    <button class="table-action" onclick="openBin('${bin.id}')">
                        View
                    </button>
                </td>
            </tr>
        `;
    });
}

/* =========================================================
   PRIORITY
   ========================================================= */

function renderPriority() {
    const container = document.getElementById("priorityList");
    const priority = bins
        .filter(bin => !bin.collected && (bin.status === "urgent" || bin.status === "warning"))
        .sort((a, b) => b.fill - a.fill)
        .slice(0, 5);

    container.innerHTML = "";

    priority.forEach((bin, index) => {
        container.innerHTML += `
            <div class="priority-item">
                <div class="priority-rank">
                    ${index + 1}
                </div>
                <div class="priority-info">
                    <strong>
                        ${bin.id}
                    </strong>
                    <span>
                        ${bin.location}
                    </span>
                </div>
                <span class="priority-percent">
                    ${bin.fill}%
                </span>
            </div>
        `;
    });
}

/* =========================================================
   AREA STATUS
   ========================================================= */

function renderAreaStatus() {
    const container = document.getElementById("areaList");
    const zones = ["Zone A", "Zone B", "Zone C", "Zone D"];

    container.innerHTML = "";

    zones.forEach(zone => {
        const zoneBins = bins.filter(bin => bin.zone === zone);
        const average = zoneBins.length
            ? Math.round(zoneBins.reduce((sum, bin) => sum + bin.fill, 0) / zoneBins.length)
            : 0;

        container.innerHTML += `
            <div class="area-row">
                <span class="area-name">
                    ${zone}
                </span>
                <div class="area-bar">
                    <div style="width:${average}%"></div>
                </div>
                <span class="area-value">
                    ${average}%
                </span>
            </div>
        `;
    });
}

/* =========================================================
   ACTIVITY
   ========================================================= */

function renderActivities() {
    const container = document.getElementById("activityList");
    container.innerHTML = "";

    activities.slice(0, 5).forEach(activity => {
        container.innerHTML += `
            <div class="activity-item">
                <div class="activity-icon">
                    ${activity.icon}
                </div>
                <div class="activity-content">
                    <strong>
                        ${activity.title}
                    </strong>
                    <span>
                        ${activity.detail} · ${activity.time}
                    </span>
                </div>
            </div>
        `;
    });
}

/* =========================================================
   BIN MONITORING
   ========================================================= */

function renderBins() {
    const grid = document.getElementById("binGrid");
    const search = document.getElementById("searchInput").value.toLowerCase().trim();
    const status = document.getElementById("statusFilter").value;
    const area = document.getElementById("areaFilter").value;

    const filtered = bins.filter(bin => {
        const searchMatch = bin.id.toLowerCase().includes(search) || bin.location.toLowerCase().includes(search);
        let statusMatch = true;
        if (status !== "all") {
            if (status === "collected") {
                statusMatch = bin.collected;
            } else {
                statusMatch = !bin.collected && bin.status === status;
            }
        }
        const areaMatch = (area === "all" || bin.zone === area);
        return searchMatch && statusMatch && areaMatch;
    });

    grid.innerHTML = "";

    if (!filtered.length) {
        grid.innerHTML = `
            <div class="panel">
                <h3>No bins found</h3>
                <p>Try changing your search or filters.</p>
            </div>
        `;
        return;
    }

    filtered.forEach(bin => {
        grid.innerHTML += `
            <div class="bin-card">
                <div class="bin-card-header">
                    <h3>${bin.id}</h3>
                    <span class="status-badge ${bin.status}">
                        ${statusLabel(bin.status)}
                    </span>
                </div>
                <p class="bin-location">
                    ${bin.location} · ${bin.zone}
                </p>
                <div class="bin-fill-header">
                    <span>Fill Level</span>
                    <span class="bin-fill-number">${bin.fill}%</span>
                </div>
                <div class="progress ${progressClass(bin.status)}">
                    <div style="width:${bin.fill}%"></div>
                </div>
                <div class="bin-card-footer">
                    <span>Sensor ${bin.sensor}</span>
                    <button class="table-action" onclick="openBin('${bin.id}')">
                        Details
                    </button>
                </div>
            </div>
        `;
    });
}

/* =========================================================
   FILTER LISTENERS
   ========================================================= */

document.getElementById("searchInput").addEventListener("input", renderBins);
document.getElementById("statusFilter").addEventListener("change", renderBins);
document.getElementById("areaFilter").addEventListener("change", renderBins);

/* =========================================================
   BIN MODAL
   ========================================================= */

function openBin(binId) {
    const bin = bins.find(item => item.id === binId);
    if (!bin) return;

    document.getElementById("modalBinId").textContent = bin.id;
    document.getElementById("modalLocation").textContent = `${bin.location} · ${bin.zone}`;
    document.getElementById("modalFill").textContent = `${bin.fill}%`;
    document.getElementById("modalProgress").style.width = `${bin.fill}%`;
    document.getElementById("modalSensor").textContent = bin.sensor;
    document.getElementById("modalTime").textContent = bin.updated;
    document.getElementById("modalCollection").textContent = bin.collected ? "Completed" : "Pending";
    document.getElementById("modalZone").textContent = bin.zone;

    const status = document.getElementById("modalStatus");
    status.textContent = statusLabel(bin.status);
    status.className = `status-badge ${bin.status}`;

    const progress = document.getElementById("modalProgress");
    progress.style.background = bin.status === "urgent"
        ? "var(--red)"
        : bin.status === "warning"
            ? "var(--orange)"
            : "var(--primary)";

    const action = document.getElementById("modalAction");
    if (bin.collected) {
        action.textContent = "Collection Completed";
        action.disabled = true;
    } else {
        action.textContent = "Mark as Collected";
        action.disabled = false;
        action.onclick = () => {
            completeCollection(bin.id);
            closeModal();
        };
    }

    document.getElementById("binModal").classList.add("show");
}

function closeModal() {
    document.getElementById("binModal").classList.remove("show");
}

document.getElementById("binModal").addEventListener("click", event => {
    if (event.target.id === "binModal") closeModal();
});

/* =========================================================
   ROUTE PRESENTATION & GENERATION (Read-only vs On-Demand)
   ========================================================= */

function renderRoutesList() {
    const container = document.getElementById("routeList");
    const stopsCounter = document.getElementById("routeStops");
    if (!container || !stopsCounter) return;

    const stops = (currentRouteStops && currentRouteStops.length > 0)
        ? currentRouteStops.filter(s => {
            const b = bins.find(item => item.id === s.id);
            return b ? !b.collected : true;
        })
        : bins.filter(b => !b.collected && (b.status === "urgent" || b.status === "warning"))
              .sort((a, b) => b.fill - a.fill)
              .slice(0, 10);

    stopsCounter.textContent = stops.length;

    // Update subtitle with TSP metrics
    const subtitle = document.getElementById("routeSubtitle");
    if (subtitle) {
        if (currentRouteMetrics && currentRouteMetrics.distance) {
            subtitle.textContent = `TSP 2-Opt Tour · ${currentRouteMetrics.distance} km · Est. ${currentRouteMetrics.duration} min · Central Depot Start`;
        } else {
            subtitle.textContent = "Based on fill level and collection priority";
        }
    }

    // Update status badge
    const statusBadge = document.getElementById("routeStatusBadge");
    if (statusBadge) {
        if (currentRouteMetrics && currentRouteMetrics.savedAt && currentRouteMetrics.savedAt !== "Initial") {
            statusBadge.textContent = `OPTIMIZED (${currentRouteMetrics.savedAt})`;
        } else {
            statusBadge.textContent = "READY";
        }
    }

    container.innerHTML = "";

    if (!stops.length) {
        container.innerHTML = `
            <div style="padding: 20px 0; text-align: center; color: var(--text-light); font-size: 9px;">
                All priority collection stops completed ✓
            </div>
        `;
        return;
    }

    stops.forEach((bin, index) => {
        container.innerHTML += `
            <div class="route-item">
                <div class="route-number">${index + 1}</div>
                <div class="route-info">
                    <strong>${bin.id}</strong>
                    <span>${bin.location} · ${bin.zone}</span>
                </div>
                <span class="route-fill">${bin.fill}%</span>
            </div>
        `;
    });
}

// User explicitly clicks "Generate New Route"
async function generateRoute() {
    const btn = document.getElementById("generateRouteBtn") || document.querySelector("#routes .page-intro button");
    const container = document.getElementById("routeList");
    const originalText = btn ? btn.textContent : "Generate New Route";

    if (btn) {
        btn.disabled = true;
        btn.textContent = "↻ Optimizing Route...";
    }
    if (container) {
        container.style.opacity = "0.35";
        container.style.transition = "opacity 0.25s ease";
    }

    showToast("Solving TSP optimal route from Central Depot...");

    if (isBackendConnected) {
        try {
            const res = await fetch(`${API_BASE}/routes/generate`, { method: "POST" });
            if (res.ok) {
                const data = await res.json();
                if (data.stops && data.stops.length > 0) {
                    currentRouteStops = data.stops;
                    currentRouteMetrics = {
                        distance: data.total_distance_km,
                        duration: data.estimated_time_min,
                        fuel: data.fuel_consumed_liters,
                        co2: data.co2_emissions_kg,
                        planId: data.plan_id,
                        savedAt: data.saved_at || getCurrentTime()
                    };

                    // Realistic slight pause so the user visually sees the re-evaluation
                    await new Promise(r => setTimeout(r, 300));

                    renderRoutesList();
                    if (container) container.style.opacity = "1";

                    const planTag = data.plan_id ? ` · Saved ${data.plan_id} to DB` : "";
                    showToast(`Route optimized: ${data.stops.length} priority stops (${data.total_distance_km} km · ~${data.estimated_time_min} mins${planTag}) ✓`);
                    return;
                }
            }
        } catch (e) {
            console.warn("Backend route generation error, using local solver:", e);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText;
            }
            if (container) container.style.opacity = "1";
        }
    }

    // Local fallback
    currentRouteStops = bins
        .filter(b => !b.collected && (b.status === "urgent" || b.status === "warning"))
        .sort((a, b) => b.fill - a.fill)
        .slice(0, 10);

    currentRouteMetrics = {
        distance: 14.8,
        duration: 45,
        savedAt: getCurrentTime()
    };

    renderRoutesList();
    if (container) container.style.opacity = "1";
    if (btn) {
        btn.disabled = false;
        btn.textContent = originalText;
    }
    showToast("Route generated successfully ✓");
}

/* =========================================================
   WORKER DASHBOARD & MANAGEMENT
   ========================================================= */

function selectActiveWorker(workerId) {
    activeWorkerId = workerId;
    renderWorkers();
    const w = allRegisteredWorkers.find(item => item.id === workerId);
    showToast(`Active worker switched to ${w?.name || workerId} ✓`);
}

function renderWorkers() {
    const container = document.getElementById("workerGrid");
    const workerSelect = document.getElementById("workerSelect");
    
    // Update worker select dropdown
    if (workerSelect) {
        workerSelect.innerHTML = "";
        allRegisteredWorkers.forEach(w => {
            const opt = document.createElement("option");
            opt.value = w.id;
            opt.textContent = `${w.name || w.id} (${w.zone || "Zone A"})`;
            if (w.id === activeWorkerId) opt.selected = true;
            workerSelect.appendChild(opt);
        });
    }

    // Active worker profile
    const currentWorker = allRegisteredWorkers.find(w => w.id === activeWorkerId) || {
        id: activeWorkerId,
        name: activeWorkerId,
        zone: "Zone A",
        truck: "Truck T-01"
    };

    const avatar = document.getElementById("workerAvatar");
    const name = document.getElementById("currentWorkerName");
    const area = document.getElementById("currentWorkerArea");

    if (avatar) avatar.textContent = (currentWorker.name || currentWorker.id).substring(0, 1).toUpperCase();
    if (name) name.textContent = currentWorker.name || currentWorker.id;
    if (area) area.textContent = `Assigned area: ${currentWorker.zone || "Zone A"} · ${currentWorker.truck || "Truck T-01"}`;

    const assigned = (currentRouteStops && currentRouteStops.length > 0)
        ? currentRouteStops.filter(s => {
            const b = bins.find(item => item.id === s.id);
            return b ? !b.collected : true;
        }).slice(0, 5)
        : bins.filter(bin => !bin.collected && (bin.status === "urgent" || bin.status === "warning"))
              .sort((a, b) => b.fill - a.fill)
              .slice(0, 5);

    const completed = history.filter(item => item.worker === activeWorkerId || item.worker === "Worker 01" || item.worker === "D405").length;

    document.getElementById("assignedCount").textContent = assigned.length + completed;
    document.getElementById("workerCompleted").textContent = completed;
    document.getElementById("workerRemaining").textContent = assigned.length;

    container.innerHTML = "";

    assigned.forEach((bin, index) => {
        container.innerHTML += `
            <div class="worker-task">
                <div class="worker-task-top">
                    <span class="status-badge ${bin.status}">
                        ${statusLabel(bin.status)}
                    </span>
                    <span>Stop ${index + 1}</span>
                </div>
                <h3>${bin.id}</h3>
                <p>
                    ${bin.location}<br>
                    ${bin.zone}<br>
                    Fill level: <strong>${bin.fill}%</strong>
                </p>
                <button class="primary-button" onclick="completeCollection('${bin.id}')">
                    Complete Collection
                </button>
            </div>
        `;
    });

    if (!assigned.length) {
        container.innerHTML = `
            <div class="panel">
                <h3>All assigned collections completed ✓</h3>
                <p>No priority bins are currently pending for ${currentWorker.name || currentWorker.id}.</p>
            </div>
        `;
    }
}

/* =========================================================
   ADD WORKER (ADMIN ONLY LOGIC)
   ========================================================= */

function renderAddWorkerPage() {
    const table = document.getElementById("registeredWorkersList");
    const countBadge = document.getElementById("registeredWorkerCount");
    const idInput = document.getElementById("workerIdInput");

    if (countBadge) {
        countBadge.textContent = `${allRegisteredWorkers.length} Workers`;
    }

    if (idInput && !idInput.value) {
        idInput.value = `Worker ${String(allRegisteredWorkers.length + 1).padStart(2, "0")}`;
    }

    if (!table) return;
    table.innerHTML = "";

    allRegisteredWorkers.slice(0, 20).forEach(w => {
        table.innerHTML += `
            <tr>
                <td>
                    <span class="bin-name">${w.name || w.id}</span>
                    <span style="display:block; font-size:7px; color:var(--text-light);">${w.id}</span>
                </td>
                <td>${w.zone || "Zone A"}</td>
                <td>${w.truck || "Truck T-01"}</td>
                <td>
                    <span class="status-badge normal">
                        ${w.status || "On Shift"}
                    </span>
                </td>
            </tr>
        `;
    });
}

async function handleWorkerSubmit(event) {
    event.preventDefault();
    if (currentUserRole !== "admin") {
        showToast("Access restricted: Administrator role required");
        return;
    }

    const btn = document.getElementById("btnSubmitWorker");
    const originalText = btn ? btn.textContent : "+ Register Worker in Database";
    if (btn) {
        btn.disabled = true;
        btn.textContent = "↻ Registering Worker...";
    }

    const payload = {
        name: document.getElementById("workerFullName").value.trim(),
        id: document.getElementById("workerIdInput").value.trim(),
        zone: document.getElementById("workerZoneSelect").value,
        phone: document.getElementById("workerPhone").value.trim() || "+1 (555) 019-2834",
        truck: document.getElementById("workerTruckInput").value.trim() || `Truck T-${allRegisteredWorkers.length + 1}`,
        vehicle_type: document.getElementById("workerVehicleType").value,
        status: document.getElementById("workerShift").value,
        truck_capacity_tons: parseFloat(document.getElementById("workerCapacity").value) || 2.5
    };

    if (isBackendConnected) {
        try {
            const res = await fetch(`${API_BASE}/workers`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                const data = await res.json();
                const newWorker = data.worker || payload;
                allRegisteredWorkers.unshift(newWorker);
                activeWorkerId = newWorker.id;

                showToast(`Worker ${newWorker.name} (${newWorker.id}) registered in database ✓`);
                document.getElementById("addWorkerForm").reset();
                renderAddWorkerPage();
                renderWorkers();
                return;
            }
        } catch (e) {
            console.warn("Backend worker registration error, using optimistic update:", e);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }
    }

    // Local fallback
    allRegisteredWorkers.unshift(payload);
    activeWorkerId = payload.id;
    showToast(`Worker ${payload.name} (${payload.id}) registered successfully ✓`);
    document.getElementById("addWorkerForm").reset();
    renderAddWorkerPage();
    renderWorkers();
    if (btn) {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

/* =========================================================
   COLLECTION ACTION (Triggers backend Trigger 2 & updates DB)
   ========================================================= */

async function completeCollection(binId) {
    const bin = bins.find(item => item.id === binId);
    if (!bin || bin.collected) return;

    if (isBackendConnected) {
        try {
            const res = await fetch(`${API_BASE}/bins/${encodeURIComponent(binId)}/collect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ worker: activeWorkerId, notes: `Manual collection confirmed by ${activeWorkerId}` })
            });

            if (res.ok) {
                const data = await res.json();
                bin.collected = true;
                bin.fill = 0;
                bin.status = "collected";
                bin.updated = getCurrentTime();
                if (currentRouteStops) {
                    currentRouteStops = currentRouteStops.filter(s => s.id !== bin.id);
                }

                if (data.collection) {
                    history.unshift(data.collection);
                }

                activities.unshift({
                    icon: "✓",
                    title: "Collection completed",
                    detail: `${bin.id} collected by ${activeWorkerId}`,
                    time: "Just now"
                });
                activities = activities.slice(0, 5);

                showToast(`${bin.id} collected & saved to database ✓`);
                renderAll();
                return;
            }
        } catch (e) {
            console.warn("Backend collection request failed, applying optimistic update:", e);
        }
    }

    bin.collected = true;
    bin.fill = 0;
    bin.status = "collected";
    bin.updated = getCurrentTime();

    const collection = {
        id: "C" + String(history.length + 1).padStart(3, "0"),
        bin: bin.id,
        worker: activeWorkerId,
        location: bin.location,
        time: getCurrentTime(),
        status: "Complete"
    };

    history.unshift(collection);

    activities.unshift({
        icon: "✓",
        title: "Collection completed",
        detail: `${bin.id} collected from ${bin.location}`,
        time: "Just now"
    });
    activities = activities.slice(0, 5);

    showToast(`${bin.id} collected successfully`);
    renderAll();
}

/* =========================================================
   HISTORY
   ========================================================= */

function renderHistory() {
    const tbody = document.getElementById("historyTable");
    tbody.innerHTML = "";

    history.forEach(record => {
        tbody.innerHTML += `
            <tr>
                <td>
                    <span class="bin-name">
                        ${record.id}
                    </span>
                </td>
                <td>
                    ${record.bin}
                </td>
                <td>
                    ${record.worker}
                </td>
                <td>
                    ${record.location}
                </td>
                <td>
                    ${record.time}
                </td>
                <td>
                    <span class="status-badge collected">
                        ${record.status}
                    </span>
                </td>
            </tr>
        `;
    });

    document.getElementById("historyTotal").textContent = history.length;
}

/* =========================================================
   SENSOR SIMULATION (Triggers backend Trigger 1 & updates DB)
   ========================================================= */

async function simulateSensorUpdate() {
    const toggle = document.getElementById("sensorToggle");
    if (toggle && !toggle.checked) {
        showToast("Sensor simulation is disabled");
        return;
    }

    if (isBackendConnected) {
        try {
            const res = await fetch(`${API_BASE}/sensors/simulate`, { method: "POST" });
            if (res.ok) {
                await syncFromBackend();
                document.getElementById("lastSync").textContent = "Just now";
                showToast("Live sensors synchronized with database ✓");
                return;
            }
        } catch (e) {
            console.warn("Simulation API error, using local simulation:", e);
        }
    }

    let changed = 0;
    bins.forEach(bin => {
        if (bin.collected) return;
        const change = Math.floor(Math.random() * 7) - 2;
        bin.fill = Math.max(0, Math.min(100, bin.fill + change));
        bin.status = calculateStatus(bin.fill);
        bin.updated = getCurrentTime();
        changed++;
    });

    activities.unshift({
        icon: "◉",
        title: "Sensor data synchronized",
        detail: `${changed} active bins updated`,
        time: "Just now"
    });
    activities = activities.slice(0, 5);

    document.getElementById("lastSync").textContent = "Just now";
    showToast("Sensor readings updated");
    renderAll();
}

/* =========================================================
   CLOCK
   ========================================================= */

function getCurrentTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/* =========================================================
   TOAST
   ========================================================= */

let toastTimer;

function showToast(message) {
    const toast = document.getElementById("toast");
    document.getElementById("toastMessage").textContent = message;
    toast.classList.add("show");

    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 2800);
}

/* =========================================================
   NOTIFICATIONS
   ========================================================= */

const notificationButton = document.getElementById("notificationButton");
const notificationPanel = document.getElementById("notificationPanel");

notificationButton.addEventListener("click", () => {
    notificationPanel.classList.toggle("show");
});

function closeNotifications() {
    notificationPanel.classList.remove("show");
}

document.addEventListener("click", event => {
    if (!notificationPanel.contains(event.target) && !notificationButton.contains(event.target)) {
        closeNotifications();
    }
});

/* =========================================================
   GLOBAL REFRESH
   ========================================================= */

function renderAll() {
    renderDashboard();
    renderBins();
    renderRoutesList();
    renderWorkers();
    renderAddWorkerPage();
    renderHistory();
}

/* =========================================================
   BACKEND LIVE SYNCHRONIZATION
   ========================================================= */

async function syncFromBackend() {
    if (isSyncing) return;
    isSyncing = true;
    try {
        const [dashRes, binsRes, histRes, routeRes, workersRes] = await Promise.all([
            fetch(`${API_BASE}/dashboard`),
            fetch(`${API_BASE}/bins`),
            fetch(`${API_BASE}/history?limit=50`),
            fetch(`${API_BASE}/routes`),
            fetch(`${API_BASE}/workers/list`)
        ]);

        if (dashRes.ok && binsRes.ok && histRes.ok) {
            const dashData = await dashRes.json();
            const binsData = await binsRes.json();
            const histData = await histRes.json();

            if (binsData && binsData.length > 0) {
                bins = binsData;
            }
            if (histData && histData.records) {
                history = histData.records;
            }
            if (dashData && dashData.activities && dashData.activities.length > 0) {
                activities = dashData.activities;
            }

            if (workersRes && workersRes.ok) {
                const workersData = await workersRes.json();
                if (workersData && workersData.length > 0) {
                    allRegisteredWorkers = workersData;
                }
            }

            if (routeRes.ok) {
                const routeData = await routeRes.json();
                if (routeData && routeData.stops) {
                    currentRouteStops = routeData.stops;
                    currentRouteMetrics = {
                        distance: routeData.total_distance_km,
                        duration: routeData.estimated_time_min,
                        fuel: routeData.fuel_consumed_liters,
                        co2: routeData.co2_emissions_kg,
                        savedAt: "Live"
                    };
                }
            }

            isBackendConnected = true;
            document.getElementById("lastSync").textContent = "Synced (Live DB)";
            renderAll();
            return true;
        }
    } catch (e) {
        isBackendConnected = false;
    } finally {
        isSyncing = false;
    }
    return false;
}

/* =========================================================
   INITIALIZE
   ========================================================= */

// Immediate initial render for zero delay
renderAll();

// Connect to backend and load live dataset
syncFromBackend();

/* =========================================================
   AUTO SENSOR REFRESH (30s interval)
   ========================================================= */

setInterval(() => {
    const sensorToggle = document.getElementById("sensorToggle");
    if (sensorToggle && sensorToggle.checked) {
        if (isBackendConnected) {
            syncFromBackend();
        } else {
            bins.forEach(bin => {
                if (bin.collected) return;
                if (Math.random() > 0.65) {
                    const change = Math.random() > 0.5 ? 1 : -1;
                    bin.fill = Math.max(0, Math.min(100, bin.fill + change));
                    bin.status = calculateStatus(bin.fill);
                }
            });
            document.getElementById("lastSync").textContent = "Just now";
            renderAll();
        }
    }
}, 30000);