import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  fetchGrants as apiFetchGrants,
  fetchDashboardStats as apiFetchStats,
  fetchHealthCheck as apiFetchHealth,
  triggerScan as apiTriggerScan,
  clearSystemCache,
  createSSEStream,
} from '../services/api';

const GrantContext = createContext();

export function GrantProvider({ children }) {
  const [grants, setGrants] = useState([]);
  const [dashboardStats, setDashboardStats] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sectorFilter, setSectorFilter] = useState('ALL');
  const [systemHealth, setSystemHealth] = useState('checking'); // 'healthy' | 'unhealthy' | 'checking'
  const [scanThoughts, setScanThoughts] = useState([]);
  const sseRef = useRef(null);

  // ── Fetch grants from backend ──
  const loadGrants = useCallback(async () => {
    try {
      const data = await apiFetchGrants();
      setGrants(data.grants || []);
      setError(null);
    } catch (err) {
      console.warn('Failed to fetch grants from API, keeping current state:', err.message);
      setError(err.message);
    }
  }, []);

  // ── Fetch dashboard stats from backend ──
  const loadStats = useCallback(async () => {
    try {
      const data = await apiFetchStats();
      setDashboardStats(data);
    } catch (err) {
      console.warn('Failed to fetch dashboard stats:', err.message);
    }
  }, []);

  // ── Check backend health ──
  const checkHealth = useCallback(async () => {
    try {
      const data = await apiFetchHealth();
      setSystemHealth(data.status === 'healthy' ? 'healthy' : 'unhealthy');
    } catch {
      setSystemHealth('unhealthy');
    }
  }, []);

  // ── Run Discovery Cycle (real API call) ──
  const runScanCycle = useCallback(async () => {
    setIsScanning(true);
    setScanThoughts([]);
    try {
      await apiTriggerScan();
      // Refresh grants and stats after scan completes
      await Promise.all([loadGrants(), loadStats()]);
      // Keep telemetry modal visible briefly so the user can see completion
      await new Promise((resolve) => setTimeout(resolve, 1500));
    } catch (err) {
      console.error('Scan cycle failed:', err.message);
      setError(`Scan failed: ${err.message}`);
    } finally {
      setIsScanning(false);
    }
  }, [loadGrants, loadStats]);

  // ── Find grant by ID ──
  const getGrantById = useCallback((id) => {
    return grants.find(g => String(g.id) === String(id) || String(g.grant_id) === String(id));
  }, [grants]);

  // ── Initial data fetch on mount ──
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await Promise.all([loadGrants(), loadStats(), checkHealth()]);
      setIsLoading(false);
    };
    init();

    // Health check interval (every 30s)
    const healthInterval = setInterval(checkHealth, 30000);

    return () => clearInterval(healthInterval);
  }, [loadGrants, loadStats, checkHealth]);

  // ── SSE Real-Time Stream ──
  useEffect(() => {
    // Connect to SSE only if backend is healthy
    if (systemHealth !== 'healthy') return;

    const sse = createSSEStream(
      (event) => {
        // Auto-refresh data on relevant events
        if (
          event.type === 'scan_completed' ||
          event.type === 'drafting_started' ||
          event.type === 'application_drafted' ||
          event.type === 'orchestration_completed' ||
          event.type === 'cache_cleared'
        ) {
          loadGrants();
          loadStats();
        }

        if (event.type === 'drafting_failed' || event.type === 'scan_failed') {
          setError(event.message || 'An error occurred during background processing.');
          // Still load stats so UI reflects matched/aborted states
          loadGrants();
          loadStats();
        }

        if (event.type === 'agent_thought' && event.message && !event.grant_id) {
          setScanThoughts(prev => [...prev, event.message]);
        }
      },
      (err) => {
        console.warn('SSE stream error, will reconnect:', err);
      }
    );
    sseRef.current = sse;

    return () => {
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    };
  }, [systemHealth, loadGrants, loadStats]);

  // ── Clear System Cache ──
  const handleClearCache = useCallback(async () => {
    setIsClearing(true);
    setError(null);
    try {
      if (typeof window !== 'undefined') {
        sessionStorage.clear();
      }
      setGrants([]);
      setDashboardStats(prev => prev ? {
        ...prev,
        grants_discovered: 0,
        grants_this_week: 0,
        high_matches: 0,
        applications_drafted: 0,
        pipeline_value: '$0K',
      } : null);
      await clearSystemCache();
      await Promise.all([loadGrants(), loadStats()]);
    } catch (err) {
      console.error('Clear cache failed:', err.message);
      setError(`Clear cache failed: ${err.message}`);
    } finally {
      setIsClearing(false);
    }
  }, [loadGrants, loadStats]);

  return (
    <GrantContext.Provider value={{
      grants,
      setGrants,
      dashboardStats,
      isScanning,
      isClearing,
      isLoading,
      error,
      systemHealth,
      runScanCycle,
      handleClearCache,
      sectorFilter,
      setSectorFilter,
      getGrantById,
      refreshGrants: loadGrants,
      refreshStats: loadStats,
      scanThoughts,
      setError,
    }}>
      {children}
    </GrantContext.Provider>
  );
}

export function useGrants() {
  return useContext(GrantContext);
}
