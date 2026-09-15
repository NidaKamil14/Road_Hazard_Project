import axios from 'axios';

// Fallback to localhost:8000 if the VITE environment variable is not set by the host frontend
const baseURL = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Optional: Add request/response interceptors for global error handling here if needed
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Client Error:', error);
    return Promise.reject(error);
  }
);
