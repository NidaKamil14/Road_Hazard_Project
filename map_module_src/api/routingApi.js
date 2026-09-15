import { apiClient } from './apiClient';

/**
 * Requests a hazard-aware route recommendation.
 * @param {Object} origin - { latitude, longitude }
 * @param {Object} destination - { latitude, longitude }
 * @param {number} safetyWeight - 0.0 (shortest) to 1.0 (safest)
 * @returns {Promise<Object>} The recommended route data including GeoJSON geometry
 */
export const fetchRouteRecommendation = async (origin, destination, safetyWeight = 0.7) => {
  try {
    const response = await apiClient.post('/route/recommend', {
      origin: {
        latitude: parseFloat(origin.latitude),
        longitude: parseFloat(origin.longitude),
      },
      destination: {
        latitude: parseFloat(destination.latitude),
        longitude: parseFloat(destination.longitude),
      },
      hazard_radius_meters: 50.0,
      safety_weight: safetyWeight,
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch route recommendation:', error);
    throw error;
  }
};
