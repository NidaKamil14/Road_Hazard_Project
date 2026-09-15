import { apiClient } from './apiClient';

/**
 * Fetches all active hazards from the backend.
 * @param {number} limit - Maximum number of hazards to fetch
 * @returns {Promise<Array>} Array of hazard objects
 */
export const fetchActiveHazards = async (limit = 500) => {
  try {
    const response = await apiClient.get('/hazards', {
      params: {
        limit,
        status: 'active',
      },
    });
    return response.data.hazards || [];
  } catch (error) {
    console.error('Failed to fetch hazards:', error);
    throw error;
  }
};
