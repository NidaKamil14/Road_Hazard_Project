/**
 * Road Hazard Map Module Export
 * Exposes the main reusable components and APIs for the host frontend application.
 */

export { HazardMap } from './components/HazardMap';
export { HazardMarkers } from './components/HazardMarkers';
export { RouteLayer } from './components/RouteLayer';
export { RoutingSidebar } from './components/RoutingSidebar';

export { fetchActiveHazards } from './api/hazardsApi';
export { fetchRouteRecommendation } from './api/routingApi';
export { apiClient } from './api/apiClient';
