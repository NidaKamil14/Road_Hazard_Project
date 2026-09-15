import React from 'react';
import { GeoJSON } from 'react-leaflet';

/**
 * RouteLayer Component
 * Renders a GeoJSON LineString on the Leaflet map.
 */
export const RouteLayer = ({ routeData }) => {
  if (!routeData || !routeData.geometry) return null;

  // Leaflet's GeoJSON component natively understands [longitude, latitude] arrays.
  // We apply styling to make the route highly visible.
  const routeStyle = {
    color: '#3b82f6', // Bright blue
    weight: 6,
    opacity: 0.7,
    lineJoin: 'round',
    dashArray: '10, 10', // Dashed line to distinguish from base map roads
  };

  return (
    <GeoJSON 
      key={`route-${routeData.route_id || Date.now()}`} 
      data={routeData.geometry} 
      style={routeStyle} 
    />
  );
};
