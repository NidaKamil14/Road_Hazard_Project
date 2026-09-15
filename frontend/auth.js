/**
 * auth.js — Authentication API module for Road Hazard Detection System
 * 
 * Provides login, session check, and logout operations.
 * All routes are defined in AUTH_CONFIG for easy backend integration.
 * Every fetch uses credentials: "include" for cookie-based sessions.
 * 
 * No credentials are compared client-side. No passwords or tokens
 * are stored in localStorage. The backend is solely responsible
 * for authentication and authorization.
 */

const AUTH_CONFIG = {
  API_BASE_URL: "http://localhost:5000",
  ENDPOINTS: {
    LOGIN:   "/api/auth/login",
    SESSION: "/api/auth/session",
    LOGOUT:  "/api/auth/logout"
  },
  REQUEST_TIMEOUT_MS: 10000
};

const AuthAPI = {
  /**
   * Attempt to log in with username and password.
   * @param {string} username
   * @param {string} password
   * @returns {Promise<{success: boolean, user?: {username: string}, error?: string}>}
   */
  async login(username, password) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), AUTH_CONFIG.REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(AUTH_CONFIG.API_BASE_URL + AUTH_CONFIG.ENDPOINTS.LOGIN, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        credentials: "include",
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (response.status === 401) {
        return { success: false, error: "invalid_credentials" };
      }

      if (!response.ok) {
        return { success: false, error: "server_error" };
      }

      const data = await response.json();
      return {
        success: true,
        user: data.user || { username: username }
      };
    } catch (err) {
      clearTimeout(timeoutId);
      return { success: false, error: "server_unavailable" };
    }
  },

  /**
   * Check whether the user has an active authenticated session.
   * @returns {Promise<{authenticated: boolean, user?: {username: string}}>}
   */
  async checkSession() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), AUTH_CONFIG.REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(AUTH_CONFIG.API_BASE_URL + AUTH_CONFIG.ENDPOINTS.SESSION, {
        method: "GET",
        credentials: "include",
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return { authenticated: false };
      }

      const data = await response.json();
      return {
        authenticated: !!data.authenticated,
        user: data.user || null
      };
    } catch (err) {
      clearTimeout(timeoutId);
      return { authenticated: false };
    }
  },

  /**
   * Log out the current session.
   * @returns {Promise<{success: boolean}>}
   */
  async logout() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), AUTH_CONFIG.REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(AUTH_CONFIG.API_BASE_URL + AUTH_CONFIG.ENDPOINTS.LOGOUT, {
        method: "POST",
        credentials: "include",
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      return { success: response.ok };
    } catch (err) {
      clearTimeout(timeoutId);
      // Even if logout request fails, we redirect to gateway
      return { success: false };
    }
  }
};

/* ============================================================
   ADMIN PAGE PROTECTION
   Call protectAdminPage() at the top of each admin page's script.
   ============================================================ */

/**
 * Checks session and redirects unauthenticated users to the gateway.
 * Returns the user object if authenticated.
 * @returns {Promise<{username: string}|null>}
 */
async function protectAdminPage() {
  const result = await AuthAPI.checkSession();

  if (!result.authenticated) {
    window.location.replace("index.html?expired=true");
    return null;
  }

  return result.user;
}

/**
 * Perform logout: call API, clear state, redirect.
 */
async function performLogout() {
  await AuthAPI.logout();
  window.location.replace("index.html");
}

/**
 * Display authenticated username in the admin header.
 * Falls back to "Admin User" during loading.
 * @param {string|null} username
 */
function displayUsername(username) {
  const el = document.getElementById("admin-username");
  if (el) {
    el.textContent = username || "Admin User";
  }
}
