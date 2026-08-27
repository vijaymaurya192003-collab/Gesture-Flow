/**
 * Gesture Flow — Reusable Centralized API Client Module
 * Connects: Vercel Frontend -> Render FastAPI Backend -> MongoDB Atlas
 */

class ApiClient {
  constructor() {
    this.tokenKey = "gf_jwt_token";
    this.userKey = "gf_user_data";
    this.baseUrl = this.resolveBaseUrl();
  }

  resolveBaseUrl() {
    // 1. Check window/build environment variables (Vite / custom window config)
    if (typeof window !== "undefined") {
      if (window.API_BASE_URL) return window.API_BASE_URL.replace(/\/$/, "");
      if (window.VITE_API_BASE_URL) return window.VITE_API_BASE_URL.replace(/\/$/, "");
      if (window.VITE_API_URL) return window.VITE_API_URL.replace(/\/$/, "");
      if (window.__ENV__?.VITE_API_URL) return window.__ENV__.VITE_API_URL.replace(/\/$/, "");
    }

    // 2. Check local storage override if user configured one
    if (typeof localStorage !== "undefined") {
      const custom = localStorage.getItem("API_BASE_URL") || localStorage.getItem("VITE_API_URL");
      if (custom) return custom.replace(/\/$/, "");
    }

    // 3. Fallback based on browser hostname
    if (typeof window !== "undefined") {
      if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
        return `${window.location.protocol}//${window.location.hostname}:8000`;
      }
    }

    // Production Render Backend URL
    return "https://gestureflow-backend.onrender.com";
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  setSession(token, user) {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }

  clearSession() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  getUser() {
    const raw = localStorage.getItem(this.userKey);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  async apiRequest(endpoint, options = {}) {
    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const url = `${this.baseUrl}${cleanEndpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      // Handle 401 Unauthorized (Expired or invalid token)
      if (response.status === 401) {
        this.clearSession();
        if (typeof window !== "undefined" && window.onAuthExpired) {
          window.onAuthExpired();
        }
      }

      let data = null;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      }

      if (!response.ok) {
        let message = `HTTP ${response.status}: ${response.statusText}`;
        if (data?.detail) {
          message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        }
        const error = new Error(message);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        const netErr = new Error("FastAPI backend is currently unavailable. Operating in local mode.");
        netErr.status = 0;
        throw netErr;
      }
      throw err;
    }
  }

  // --- API Endpoint Methods ---

  async checkHealth() {
    return await this.apiRequest("/health", { method: "GET" });
  }

  async register(name, email, password) {
    const data = await this.apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password })
    });
    if (data?.access_token && data?.user) {
      this.setSession(data.access_token, data.user);
    }
    return data;
  }

  async login(email, password) {
    const data = await this.apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    if (data?.access_token && data?.user) {
      this.setSession(data.access_token, data.user);
    }
    return data;
  }

  async getCurrentUser() {
    const user = await this.apiRequest("/auth/me", { method: "GET" });
    if (user) {
      localStorage.setItem(this.userKey, JSON.stringify(user));
    }
    return user;
  }

  async getGestures() {
    return await this.apiRequest("/gestures", { method: "GET" });
  }

  async updateGesture(gestureName, mappingData) {
    return await this.apiRequest(`/gestures/${encodeURIComponent(gestureName)}`, {
      method: "PUT",
      body: JSON.stringify(mappingData)
    });
  }

  async createGesture(mappingData) {
    return await this.apiRequest("/gestures", {
      method: "POST",
      body: JSON.stringify(mappingData)
    });
  }

  async deleteGesture(gestureName) {
    return await this.apiRequest(`/gestures/${encodeURIComponent(gestureName)}`, {
      method: "DELETE"
    });
  }

  async getSettings() {
    return await this.apiRequest("/settings", { method: "GET" });
  }

  async updateSettings(settingsData) {
    return await this.apiRequest("/settings", {
      method: "PUT",
      body: JSON.stringify(settingsData)
    });
  }

  async getCalibration() {
    return await this.apiRequest("/calibration", { method: "GET" });
  }

  async updateCalibration(calibrationData) {
    return await this.apiRequest("/calibration", {
      method: "PUT",
      body: JSON.stringify(calibrationData)
    });
  }

  async getStats() {
    return await this.apiRequest("/stats", { method: "GET" });
  }
}

// Global API Client Instance
const api = new ApiClient();
if (typeof window !== "undefined") {
  window.api = api;
}

