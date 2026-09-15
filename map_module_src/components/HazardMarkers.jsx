import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';

/**
 * Generates a custom DivIcon based on priority level.
 */
const getMarkerIcon = (priorityLevel) => {
  let colorClass = 'marker-low';
  
  switch (priorityLevel?.toLowerCase()) {
    case 'critical':
      colorClass = 'marker-critical';
      break;
    case 'high':
      colorClass = 'marker-high';
      break;
    case 'medium':
      colorClass = 'marker-medium';
      break;
    case 'low':
      colorClass = 'marker-low';
      break;
    default:
      colorClass = 'marker-medium';
  }

  return L.divIcon({
    className: 'custom-marker',
    html: `<div class="marker-dot ${colorClass}"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -8],
  });
};

/**
 * HazardMarkers Component
 * Iterates over the hazards array and renders custom Leaflet markers.
 */
export const HazardMarkers = ({ hazards }) => {
  if (!hazards || hazards.length === 0) return null;

  return (
    <>
      {hazards.map((hazard) => {
        // Safe check for valid coordinates
        if (typeof hazard.latitude !== 'number' || typeof hazard.longitude !== 'number') return null;
        
        const badgeClass = `badge-${hazard.priority_level?.toLowerCase() || 'medium'}`;

        return (
          <Marker 
            key={hazard.id} 
            position={[hazard.latitude, hazard.longitude]}
            icon={getMarkerIcon(hazard.priority_level)}
          >
            <Popup>
              <div className="popup-content">
                <h4>{hazard.hazard_type.replace('_', ' ')}</h4>
                <p><strong>Confidence:</strong> {(hazard.confidence * 100).toFixed(1)}%</p>
                <p><strong>Score:</strong> {hazard.priority_score}</p>
                {hazard.priority_reason && (
                  <p style={{ fontSize: '11px', color: '#a0a0a0', lineHeight: 1.3 }}>
                    {hazard.priority_reason}
                  </p>
                )}
                <span className={`priority-badge ${badgeClass}`}>
                  {hazard.priority_level} Priority
                </span>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </>
  );
};
