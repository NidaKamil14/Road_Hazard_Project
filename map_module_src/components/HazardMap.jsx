import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { fetchActiveHazards } from '../api/hazardsApi';
import { fetchRouteRecommendation } from '../api/routingApi';
import { HazardMarkers } from './HazardMarkers';
import { RouteLayer } from './RouteLayer';
import { RoutingSidebar } from './RoutingSidebar';

import '../assets/mapStyles.css';

/**
 * HazardMap Main Component
 * This is the central, self-contained map module exported for the host React app.
 * It manages fetching hazards, fetching routes, and rendering the Leaflet Map.
 */
export const HazardMap = ({ 
  initialCenter = [18.5204, 73.8567], 
  initialZoom = 13 
}) => {
  const [hazards, setHazards] = useState([]);
  const [routeResult, setRouteResult] = useState(null);
  
  const [isLoadingHazards, setIsLoadingHazards] = useState(false);
  const [isRouting, setIsRouting] = useState(false);
  
  const [hazardError, setHazardError] = useState(null);
  const [routingError, setRoutingError] = useState(null);

  // Fetch initial active hazards on mount
  useEffect(() => {
    const loadHazards = async () => {
      setIsLoadingHazards(true);
      try {
        const data = await fetchActiveHazards();
        setHazards(data);
        setHazardError(null);
      } catch (err) {
        setHazardError('Failed to load active hazards.');
      } finally {
        setIsLoadingHazards(false);
      }
    };

    loadHazards();
  }, []);

  // Handler for triggering route calculation from the Sidebar
  const handleFindRoute = async (origin, destination) => {
    setIsRouting(true);
    setRoutingError(null);
    setRouteResult(null);

    try {
      const data = await fetchRouteRecommendation(origin, destination);
      if (data && data.success) {
        setRouteResult(data);
      } else {
        setRoutingError('Failed to calculate safe route.');
      }
    } catch (err) {
      setRoutingError(
        err.response?.data?.detail || 'Routing engine error or no path found.'
      );
    } finally {
      setIsRouting(false);
    }
  };

  return (
    <div className="hazard-map-wrapper">
      <RoutingSidebar 
        onFindRoute={handleFindRoute}
        routeResult={routeResult}
        isLoading={isRouting}
        error={routingError}
      />
      
      <MapContainer 
        center={initialCenter} 
        zoom={initialZoom} 
        className="hazard-map-container"
        zoomControl={false} // Hiding default controls to keep it clean, could add custom positioning
      >
        {/* CartoDB Dark Matter Base Map - Ideal for a dark-mode hazard app */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        <HazardMarkers hazards={hazards} />
        
        {routeResult && routeResult.recommended_route && (
          <RouteLayer routeData={routeResult.recommended_route} />
        )}
      </MapContainer>
      
      {isLoadingHazards && (
        <div style={{ position: 'absolute', bottom: 20, right: 20, color: '#fff', zIndex: 1000, background: 'rgba(0,0,0,0.5)', padding: '4px 8px', borderRadius: 4 }}>
          Loading hazards...
        </div>
      )}
      {hazardError && (
        <div style={{ position: 'absolute', bottom: 20, right: 20, color: '#ef4444', zIndex: 1000, background: 'rgba(239, 68, 68, 0.2)', padding: '4px 8px', borderRadius: 4 }}>
          {hazardError}
        </div>
      )}
    </div>
  );
};
