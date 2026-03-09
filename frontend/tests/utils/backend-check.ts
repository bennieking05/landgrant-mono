/**
 * Backend availability check for E2E tests
 * 
 * API tests require the backend to be running. This utility provides
 * a way to skip API tests when the backend is unavailable.
 */

const API_BASE = "http://localhost:8050";

let backendAvailable: boolean | null = null;
let checkPromise: Promise<boolean> | null = null;

/**
 * Check if the backend API is available
 * Caches the result for the test run
 */
export async function isBackendAvailable(): Promise<boolean> {
  // Return cached result if available
  if (backendAvailable !== null) {
    return backendAvailable;
  }
  
  // If a check is already in progress, wait for it
  if (checkPromise) {
    return checkPromise;
  }

  // Start the check
  checkPromise = (async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      
      const response = await fetch(`${API_BASE}/health/live`, {
        method: "GET",
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      backendAvailable = response.ok;
    } catch {
      backendAvailable = false;
    }
    return backendAvailable;
  })();

  return checkPromise;
}

/**
 * Synchronous check - use after isBackendAvailable() has been called once
 */
export function isBackendAvailableSync(): boolean {
  return backendAvailable === true;
}

/**
 * Skip message for API tests when backend is unavailable
 */
export const SKIP_API_MESSAGE = "Backend API not available at localhost:8050 - skipping API test";
