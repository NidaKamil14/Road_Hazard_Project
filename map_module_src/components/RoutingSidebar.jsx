import React, { useState } from 'react';

/**
 * RoutingSidebar Component
 * Provides a UI overlay for the user to input Origin and Destination coordinates,
 * triggers the routing API call, and displays the summary.
 */
export const RoutingSidebar = ({ onFindRoute, routeResult, isLoading, error }) => {
  // Local state for coordinate inputs. 
  // In a full production app, this might be a geocoder search box.
  const [originLat, setOriginLat] = useState('18.5204');
  const [originLng, setOriginLng] = useState('73.8567');
  const [destLat, setDestLat] = useState('18.5310');
  const [destLng, setDestLng] = useState('73.8470');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!originLat || !originLng || !destLat || !destLng) return;
    
    onFindRoute(
      { latitude: parseFloat(originLat), longitude: parseFloat(originLng) },
      { latitude: parseFloat(destLat), longitude: parseFloat(destLng) }
    );
  };

  return (
    <div className="routing-sidebar">
      <h3>Hazard-Aware Navigation</h3>
      
      <form onSubmit={handleSubmit} className="routing-form">
        <div className="input-group">
          <label>Origin</label>
          <div className="input-row">
            <input 
              type="number" step="any" placeholder="Lat" 
              className="routing-input" 
              value={originLat} onChange={(e) => setOriginLat(e.target.value)} required 
            />
            <input 
              type="number" step="any" placeholder="Lng" 
              className="routing-input" 
              value={originLng} onChange={(e) => setOriginLng(e.target.value)} required 
            />
          </div>
        </div>

        <div className="input-group">
          <label>Destination</label>
          <div className="input-row">
            <input 
              type="number" step="any" placeholder="Lat" 
              className="routing-input" 
              value={destLat} onChange={(e) => setDestLat(e.target.value)} required 
            />
            <input 
              type="number" step="any" placeholder="Lng" 
              className="routing-input" 
              value={destLng} onChange={(e) => setDestLng(e.target.value)} required 
            />
          </div>
        </div>

        <button type="submit" className="btn-primary" disabled={isLoading}>
          {isLoading ? 'Calculating Safe Route...' : 'Find Safest Route'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {routeResult && routeResult.recommended_route && (
        <div className="route-summary">
          <h4>Recommended Route</h4>
          <div className="summary-stats">
            <span>{routeResult.recommended_route.distance_km.toFixed(2)} km</span>
            <span>{Math.round(routeResult.recommended_route.duration_minutes)} min</span>
          </div>
          <div className="summary-stats">
            <span>Hazards Avoided:</span>
            <span>{routeResult.recommended_route.hazard_count}</span>
          </div>
          <p className="summary-reason">
            {routeResult.recommendation_reason}
          </p>
        </div>
      )}
    </div>
  );
};
