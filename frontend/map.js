// frontend/map.js

const API_BASE_URL = "http://localhost:5000";

let map;
let hazardLayerGroup;

let originMarker = null;
let destinationMarker = null;
let originCoords = null;
let destinationCoords = null;
let isSelectingDestination = false;
let routeLayer = null;

let alternativeRouteLayers = {};
let recommendedRouteLayers = {};
let routeBoundsMap = {};

document.addEventListener("DOMContentLoaded", () => {
    initializeMap();
    setupEventListeners();
    fetchAndDisplayHazards();
});

function initializeMap() {
    // Neutral India-wide initial centre as a fallback viewport
    const fallbackCenterLat = 21.1458;
    const fallbackCenterLng = 79.0882;
    const fallbackZoom = 5;

    map = L.map('hazard-map').setView([fallbackCenterLat, fallbackCenterLng], fallbackZoom);

    // Keep Leaflet attribution visible as required by adding OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Layer group to hold all hazard markers
    hazardLayerGroup = L.featureGroup().addTo(map);

    // Map click handler for destination selection
    map.on('click', handleMapClick);
}

function setupEventListeners() {
    const refreshBtn = document.getElementById('refresh-hazards-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            fetchAndDisplayHazards();
        });
    }

    const retryBtn = document.getElementById('retry-hazards-btn');
    if (retryBtn) {
        retryBtn.addEventListener('click', () => {
            fetchAndDisplayHazards();
        });
    }

    // Routing listeners
    document.getElementById('btn-use-location')?.addEventListener('click', requestCurrentLocation);
    document.getElementById('btn-select-destination')?.addEventListener('click', beginDestinationSelection);
    document.getElementById('btn-clear-route')?.addEventListener('click', clearRoutePoints);
    document.getElementById('btn-find-route')?.addEventListener('click', fetchRecommendedRoute);
    document.getElementById('btn-show-recommended')?.addEventListener('click', showRecommendedRoute);
}

async function fetchAndDisplayHazards() {
    updateStatusMessage("Loading hazards...");
    hideErrorMessage();

    // Clear the marker layer without recreating the whole map
    hazardLayerGroup.clearLayers();

    try {
        const url = `${API_BASE_URL}/hazards?status=active&limit=500&offset=0`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}`);
        }

        const data = await response.json();
        const hazards = data.hazards || [];

        processHazardData(hazards);
    } catch (error) {
        console.error("Error fetching hazards:", error);
        showErrorMessage("Failed to load hazards from the server. Please check your connection or try again.");
        updateStatusMessage("Error loading hazards.");
    }
}

function processHazardData(hazards) {
    let validHazardCount = 0;
    const groups = [];

    hazards.forEach(hazard => {
        if (isValidCoordinate(hazard.latitude, hazard.longitude)) {
            validHazardCount++;

            let matchedGroup = null;
            // Check if within 15 metres of an existing group
            for (let i = 0; i < groups.length; i++) {
                const group = groups[i];
                const distance = haversineDistance(hazard.latitude, hazard.longitude, group.avgLat, group.avgLng);
                if (distance <= 15) {
                    matchedGroup = group;
                    break;
                }
            }

            if (matchedGroup) {
                matchedGroup.hazards.push(hazard);
                // Update average lat/lng
                const total = matchedGroup.hazards.length;
                matchedGroup.avgLat = matchedGroup.avgLat + (hazard.latitude - matchedGroup.avgLat) / total;
                matchedGroup.avgLng = matchedGroup.avgLng + (hazard.longitude - matchedGroup.avgLng) / total;
            } else {
                groups.push({
                    hazards: [hazard],
                    avgLat: hazard.latitude,
                    avgLng: hazard.longitude
                });
            }
        }
    });

    if (validHazardCount === 0) {
        updateStatusMessage("No active hazards currently reported on the network.");
        // The map stays at its fallback viewport
    } else {
        updateStatusMessage(`Displaying ${validHazardCount} active hazard${validHazardCount === 1 ? '' : 's'}.`);

        groups.forEach((group) => {
            addHazardGroupMarker(group);
        });

        fitMapToMarkers();
    }
}

function haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // metres
    const rad = Math.PI / 180;
    const phi1 = lat1 * rad;
    const phi2 = lat2 * rad;
    const deltaPhi = (lat2 - lat1) * rad;
    const deltaLambda = (lon2 - lon1) * rad;

    const a = Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
              Math.cos(phi1) * Math.cos(phi2) *
              Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // in metres
}

function isValidCoordinate(lat, lng) {
    if (typeof lat !== 'number' || typeof lng !== 'number') {
        return false;
    }
    if (isNaN(lat) || isNaN(lng)) {
        return false;
    }
    if (lat < -90 || lat > 90) {
        return false;
    }
    if (lng < -180 || lng > 180) {
        return false;
    }
    return true;
}

function addHazardGroupMarker(group) {
    const groupedHazards = group.hazards;
    if (groupedHazards.length === 0) return;

    // Determine the highest priority for the marker color
    const priorityOrder = { 'critical': 4, 'high': 3, 'medium': 2, 'low': 1 };
    let highestPriority = 'low';
    let maxPrioValue = 0;

    groupedHazards.forEach(hazard => {
        const p = (hazard.priority_level || 'low').toLowerCase();
        if (priorityOrder[p] > maxPrioValue) {
            maxPrioValue = priorityOrder[p];
            highestPriority = p;
        }
    });

    let markerClass = 'map-marker-low';
    if (highestPriority === 'critical') markerClass = 'map-marker-critical';
    else if (highestPriority === 'high') markerClass = 'map-marker-high';
    else if (highestPriority === 'medium') markerClass = 'map-marker-medium';

    const groupCount = groupedHazards.length;

    // Circular custom Leaflet divIcon marker
    const customIcon = L.divIcon({
        className: `map-marker-custom ${markerClass}`,
        html: groupCount > 1 ? `<span>${groupCount}</span>` : '',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -14]
    });

    // Place grouped marker at the average latitude and longitude
    const marker = L.marker([group.avgLat, group.avgLng], { icon: customIcon });

    const popupHtml = buildGroupPopupHtml(groupedHazards);
    marker.bindPopup(popupHtml, { maxHeight: 400 });

    hazardLayerGroup.addLayer(marker);
}

function toTitleCase(str) {
    if (!str) return 'N/A';
    return String(str)
        .replace(/_/g, ' ')
        .toLowerCase()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatConfidence(conf) {
    if (conf === null || conf === undefined) return '0.0%';
    let val = parseFloat(conf);
    if (isNaN(val)) return '0.0%';
    if (val >= 0 && val <= 1) {
        val = val * 100;
    }
    return val.toFixed(1) + '%';
}

function buildGroupPopupHtml(groupedHazards) {
    let html = '';

    groupedHazards.forEach((hazard, index) => {
        const type = escapeHtml(toTitleCase(hazard.hazard_type || 'Unknown'));
        const reportId = escapeHtml(String(hazard.id || 'N/A'));
        const confidence = escapeHtml(formatConfidence(hazard.confidence));
        const severity = escapeHtml(toTitleCase(hazard.severity || 'N/A'));
        const priorityLevel = escapeHtml(toTitleCase(hazard.priority_level || 'N/A'));
        const priorityScore = escapeHtml(String(hazard.priority_score || 'N/A'));
        const status = escapeHtml(toTitleCase(hazard.status || 'N/A'));

        let detectedTime = 'N/A';
        if (hazard.detected_at) {
            try {
                const dateObj = new Date(hazard.detected_at);
                detectedTime = escapeHtml(dateObj.toLocaleString());
            } catch (e) {
                detectedTime = escapeHtml(hazard.detected_at);
            }
        }

        const lat = escapeHtml(Number(hazard.latitude).toFixed(6));
        const lng = escapeHtml(Number(hazard.longitude).toFixed(6));

        if (index > 0) {
            html += `<hr style="border-top:1px solid #333; margin: 12px 0;">`;
        }

        html += `
            <div class="map-popup-header">${type}</div>
            <div class="map-popup-row"><span class="map-popup-label">Report ID:</span> <span class="map-popup-value">${reportId}</span></div>
            <div class="map-popup-row"><span class="map-popup-label">Severity:</span> <span class="map-popup-value">${severity}</span></div>
            <div class="map-popup-row"><span class="map-popup-label">Confidence:</span> <span class="map-popup-value">${confidence}</span></div>
            <div class="map-popup-row"><span class="map-popup-label">Priority Level:</span> <span class="map-popup-value">${priorityLevel}</span></div>
            <div class="map-popup-row"><span class="map-popup-label">Priority Score:</span> <span class="map-popup-value">${priorityScore}</span></div>
            <div class="map-popup-row"><span class="map-popup-label">Status:</span> <span class="map-popup-value">${status}</span></div>
            <div class="map-popup-row"><span class="map-popup-label">Detected:</span> <span class="map-popup-value">${detectedTime}</span></div>
            <div class="map-popup-row"><span class="map-popup-label">Location:</span> <span class="map-popup-value">${lat}, ${lng}</span></div>
        `;
    });

    return html;
}

function escapeHtml(unsafeText) {
    if (!unsafeText) return '';
    return String(unsafeText)
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

function fitMapToMarkers() {
    // Automatically fit the map to all valid hazard markers.
    // Do not zoom closer than approximately zoom 15 when fitting a single/small marker group.
    if (hazardLayerGroup.getLayers().length > 0) {
        const bounds = hazardLayerGroup.getBounds();
        map.fitBounds(bounds, {
            maxZoom: 15,
            padding: [40, 40]
        });
    }
}

function updateStatusMessage(message) {
    const statusEl = document.getElementById('map-status');
    if (statusEl) {
        statusEl.textContent = message;
    }
}

function showErrorMessage(message) {
    const errorNotice = document.getElementById('map-error');
    const errorText = errorNotice?.querySelector('.error-text');
    if (errorNotice && errorText) {
        errorText.textContent = message;
        errorNotice.classList.remove('hidden');
    }
}

function hideErrorMessage() {
    const errorNotice = document.getElementById('map-error');
    if (errorNotice) {
        errorNotice.classList.add('hidden');
    }
}

// ----------------------------------------------------
// Routing Selection Logic
// ----------------------------------------------------

function handleMapClick(e) {
    if (isSelectingDestination) {
        setDestination(e.latlng.lat, e.latlng.lng);
    }
}

function requestCurrentLocation() {
    updateRouteStatus("Requesting location...");
    if (!navigator.geolocation) {
        updateRouteStatus("Geolocation is not supported by your browser.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            setOrigin(lat, lng);
        },
        (error) => {
            let msg = "Failed to get location.";
            switch(error.code) {
                case error.PERMISSION_DENIED: msg = "Location permission denied."; break;
                case error.POSITION_UNAVAILABLE: msg = "Location position unavailable."; break;
                case error.TIMEOUT: msg = "Location request timed out."; break;
            }
            updateRouteStatus(msg);
        },
        { timeout: 10000 }
    );
}

function beginDestinationSelection() {
    isSelectingDestination = true;
    document.getElementById('hazard-map').classList.add('map-crosshair');
    updateRouteStatus("Click anywhere on the map to select your destination.");
}

function setOrigin(lat, lng) {
    originCoords = { lat, lng };
    document.getElementById('display-origin').textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;

    if (originMarker) {
        map.removeLayer(originMarker);
    }

    const icon = L.divIcon({
        className: 'route-marker-origin',
        html: 'O',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    originMarker = L.marker([lat, lng], { icon }).addTo(map);
    map.setView([lat, lng], 14);
    updateRouteStatus("Origin location set successfully.");

    checkFindRouteButton();
    clearCurrentRoute();
}

function setDestination(lat, lng) {
    destinationCoords = { lat, lng };
    document.getElementById('display-destination').textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;

    if (destinationMarker) {
        map.removeLayer(destinationMarker);
    }

    const icon = L.divIcon({
        className: 'route-marker-destination',
        html: 'D',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    destinationMarker = L.marker([lat, lng], { icon }).addTo(map);

    // Exit selection mode
    isSelectingDestination = false;
    document.getElementById('hazard-map').classList.remove('map-crosshair');
    updateRouteStatus("Destination set successfully.");

    checkFindRouteButton();
    clearCurrentRoute();
}

function clearRoutePoints() {
    if (originMarker) map.removeLayer(originMarker);
    if (destinationMarker) map.removeLayer(destinationMarker);

    originMarker = null;
    destinationMarker = null;
    originCoords = null;
    destinationCoords = null;

    const originDisp = document.getElementById('display-origin');
    if (originDisp) originDisp.textContent = "Not selected";

    const destDisp = document.getElementById('display-destination');
    if (destDisp) destDisp.textContent = "Not selected";

    isSelectingDestination = false;
    const mapEl = document.getElementById('hazard-map');
    if (mapEl) mapEl.classList.remove('map-crosshair');

    clearCurrentRoute();
    checkFindRouteButton();
    updateRouteStatus("Route points cleared.");
}

function updateRouteStatus(msg) {
    const el = document.getElementById('route-status');
    if (el) el.textContent = escapeHtml(msg);
}

function checkFindRouteButton() {
    const btn = document.getElementById('btn-find-route');
    if (btn) {
        btn.disabled = !(originCoords && destinationCoords);
    }
}

function clearCurrentRoute() {
    if (routeLayer) {
        map.removeLayer(routeLayer);
        routeLayer = null;
    }

    alternativeRouteLayers = {};
    recommendedRouteLayers = {};
    routeBoundsMap = {};

    const resultsPanel = document.getElementById('route-results-panel');
    if (resultsPanel) {
        resultsPanel.classList.add('hidden');
    }

    document.getElementById('btn-show-recommended')?.classList.add('hidden');
}

async function fetchRecommendedRoute() {
    if (!originCoords || !destinationCoords) return;

    const btn = document.getElementById('btn-find-route');
    if (btn) btn.disabled = true;

    clearCurrentRoute();
    updateRouteStatus("Calculating the safest available route...");

    const requestBody = {
        origin: { latitude: originCoords.lat, longitude: originCoords.lng },
        destination: { latitude: destinationCoords.lat, longitude: destinationCoords.lng },
        hazard_radius_meters: 100,
        safety_weight: 0.7
    };

    try {
        const response = await fetch(`${API_BASE_URL}/route/recommend`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const payload = await response.json();

        if (!payload.success || !payload.recommended_route) {
            throw new Error("Invalid response or missing route data from server.");
        }

        const route = payload.recommended_route;

        if (!route.geometry || route.geometry.type !== 'LineString' || !route.geometry.coordinates || route.geometry.coordinates.length === 0) {
            throw new Error("Missing route geometry.");
        }

        drawRoutes(payload);
        displayRouteResults(payload);
        updateRouteStatus("Safer route found.");

    } catch (error) {
        console.error("Routing error:", error);
        updateRouteStatus(`Failed to find route: ${error.message}`);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function drawRoutes(payload) {
    const recommended = payload.recommended_route;
    const alternatives = payload.alternatives || [];

    routeLayer = L.layerGroup();
    const mapBounds = L.latLngBounds();

    alternativeRouteLayers = {};
    recommendedRouteLayers = {};
    routeBoundsMap = {};

    // Draw alternatives first so they are underneath
    alternatives.forEach(alt => {
        if (!alt || !alt.geometry || alt.geometry.type !== 'LineString' || !alt.geometry.coordinates || alt.geometry.coordinates.length === 0) {
            return;
        }

        // Validate coordinates are finite
        const isValid = alt.geometry.coordinates.every(c => Array.isArray(c) && c.length === 2 && isFinite(c[0]) && isFinite(c[1]));
        if (!isValid) return;

        // Leaflet expects [lat, lng]
        const latLngs = alt.geometry.coordinates.map(coord => [coord[1], coord[0]]);
        const bounds = L.latLngBounds(latLngs);
        routeBoundsMap[`alt_${alt.route_id}`] = bounds;

        const altOutline = L.polyline(latLngs, {
            color: '#ffffff',
            weight: 9,
            opacity: 1
        });

        const altPolyline = L.polyline(latLngs, {
            color: '#2563eb',
            weight: 6,
            opacity: 0.85,
            dashArray: '12 10'
        });

        altPolyline.bindTooltip(`
            <strong>Alternative Route ${escapeHtml(String(alt.route_id))}</strong><br>
            Distance: ${Number(alt.distance_km).toFixed(2)} km<br>
            Duration: ${Number(alt.duration_minutes).toFixed(1)} min<br>
            Hazards: ${alt.hazard_count} (Risk: ${Number(alt.hazard_risk_score).toFixed(2)})
        `);

        routeLayer.addLayer(altOutline);
        routeLayer.addLayer(altPolyline);
        mapBounds.extend(bounds);

        alternativeRouteLayers[alt.route_id] = {
            outline: altOutline,
            line: altPolyline
        };
    });

    // Draw recommended route last
    const recLatLngs = recommended.geometry.coordinates.map(coord => [coord[1], coord[0]]);
    const recBounds = L.latLngBounds(recLatLngs);
    routeBoundsMap['recommended'] = recBounds;

    const recOutlineLayer = L.polyline(recLatLngs, {
        color: '#000',
        weight: 10,
        opacity: 1,
        lineCap: 'round',
        lineJoin: 'round'
    });

    const recPolyline = L.polyline(recLatLngs, {
        color: '#FF5A1F',
        weight: 6,
        opacity: 1,
        lineCap: 'round',
        lineJoin: 'round'
    });

    recPolyline.bindTooltip(`
        <strong>Recommended Route</strong><br>
        Distance: ${Number(recommended.distance_km).toFixed(2)} km<br>
        Duration: ${Number(recommended.duration_minutes).toFixed(1)} min<br>
        Hazards: ${recommended.hazard_count} (Risk: ${Number(recommended.hazard_risk_score).toFixed(2)})
    `);

    routeLayer.addLayer(recOutlineLayer);
    routeLayer.addLayer(recPolyline);
    mapBounds.extend(recBounds);

    recommendedRouteLayers = {
        outline: recOutlineLayer,
        line: recPolyline
    };

    // Extend bounds to ensure origin and destination markers are included
    if (originCoords) mapBounds.extend([originCoords.lat, originCoords.lng]);
    if (destinationCoords) mapBounds.extend([destinationCoords.lat, destinationCoords.lng]);

    // Add everything to map
    routeLayer.addTo(map);

    // Fit map
    if (mapBounds.isValid()) {
        map.fitBounds(mapBounds, { padding: [50, 50] });
    }
}

function displayRouteResults(payload) {
    const route = payload.recommended_route;

    document.getElementById('route-reason').textContent = payload.recommendation_reason || "No reason provided.";
    document.getElementById('route-distance').textContent = `${Number(route.distance_km).toFixed(2)} km`;
    document.getElementById('route-duration').textContent = `${Number(route.duration_minutes).toFixed(1)} min`;
    document.getElementById('route-hazards').textContent = String(route.hazard_count);
    document.getElementById('route-critical').textContent = String(route.critical_hazard_count);
    document.getElementById('route-risk').textContent = Number(route.hazard_risk_score).toFixed(2);
    document.getElementById('route-weight').textContent = Number(payload.safety_weight_used).toFixed(1);
    document.getElementById('route-radius').textContent = `${Math.round(payload.hazard_radius_meters_used)} m`;

    const resultsPanel = document.getElementById('route-results-panel');
    if (resultsPanel) {
        resultsPanel.classList.remove('hidden');
    }

    const listEl = document.getElementById('alternative-routes-list');
    if (listEl) {
        const alternatives = payload.alternatives || [];

        if (alternatives.length === 0) {
            listEl.innerHTML = '<div class="alt-empty">No alternative routes were returned.</div>';
            document.getElementById('alternative-routes-container').style.display = 'block'; // ensure it's visible if empty
        } else {
            document.getElementById('alternative-routes-container').style.display = 'block';
            listEl.innerHTML = alternatives.map(alt => `
                <div class="alt-route-card" id="alt-card-${alt.route_id}">
                    <div class="alt-route-header" style="display: flex; justify-content: space-between; align-items: center;">
                        <span>Alternative Route ${escapeHtml(String(alt.route_id))}</span>
                        <button class="btn-outline btn-small" onclick="highlightAlternativeRoute(${alt.route_id})" aria-label="Highlight Alternative Route ${escapeHtml(String(alt.route_id))}">HIGHLIGHT ON MAP</button>
                    </div>
                    <div class="alt-route-metrics">
                        <div class="alt-metric">
                            <span class="alt-metric-label">Distance</span>
                            <span class="alt-metric-value">${Number(alt.distance_km).toFixed(2)} km</span>
                        </div>
                        <div class="alt-metric">
                            <span class="alt-metric-label">Duration</span>
                            <span class="alt-metric-value">${Number(alt.duration_minutes).toFixed(1)} min</span>
                        </div>
                        <div class="alt-metric">
                            <span class="alt-metric-label">Total Hazards</span>
                            <span class="alt-metric-value">${alt.hazard_count}</span>
                        </div>
                        <div class="alt-metric">
                            <span class="alt-metric-label">Critical</span>
                            <span class="alt-metric-value">${alt.critical_hazard_count}</span>
                        </div>
                        <div class="alt-metric">
                            <span class="alt-metric-label">Risk Score</span>
                            <span class="alt-metric-value">${Number(alt.hazard_risk_score).toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }
    }
}

// Global functions for inline HTML event handlers
window.highlightAlternativeRoute = function(routeId) {
    // Dim Recommended Route
    if (recommendedRouteLayers.line) {
        recommendedRouteLayers.line.setStyle({ opacity: 0.35 });
        recommendedRouteLayers.outline.setStyle({ opacity: 0.35 });
    }

    // Reset all alternatives to default
    Object.values(alternativeRouteLayers).forEach(layers => {
        layers.line.setStyle({ weight: 6, opacity: 0.85 });
    });

    // Highlight the selected one
    const layers = alternativeRouteLayers[routeId];
    if (layers) {
        layers.outline.bringToFront();
        layers.line.bringToFront();
        layers.line.setStyle({ weight: 8, opacity: 1 });

        const bounds = routeBoundsMap[`alt_${routeId}`];
        if (bounds) {
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    // Mark the card
    document.querySelectorAll('.alt-route-card').forEach(el => el.classList.remove('is-selected'));
    const card = document.getElementById(`alt-card-${routeId}`);
    if (card) {
        card.classList.add('is-selected');
    }

    // Show the "SHOW RECOMMENDED ROUTE" button
    document.getElementById('btn-show-recommended')?.classList.remove('hidden');
};

function showRecommendedRoute() {
    // Restore Recommended Route
    if (recommendedRouteLayers.line) {
        recommendedRouteLayers.line.setStyle({ opacity: 1 });
        recommendedRouteLayers.outline.setStyle({ opacity: 1 });
        recommendedRouteLayers.outline.bringToFront();
        recommendedRouteLayers.line.bringToFront();

        const bounds = routeBoundsMap['recommended'];
        if (bounds) {
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }

    // Reset all alternatives to default
    Object.values(alternativeRouteLayers).forEach(layers => {
        layers.line.setStyle({ weight: 6, opacity: 0.85 });
    });

    // Remove marking on cards
    document.querySelectorAll('.alt-route-card').forEach(el => el.classList.remove('is-selected'));

    // Hide the button
    document.getElementById('btn-show-recommended')?.classList.add('hidden');
}
