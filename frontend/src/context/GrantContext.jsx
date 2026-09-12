import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  fetchGrants as apiFetchGrants,
  fetchDashboardStats as apiFetchStats,
  fetchHealthCheck as apiFetchHealth,
  triggerScan as apiTriggerScan,
  clearSystemCache,
  createSSEStream,
} from '../services/api';

/**
 * Universal dynamic deduplication keys for grants.
 * Extracts all valid identity signals: Grants.gov numeric ID, federal solicitation code,
 * and normalized title slug without requiring any hardcoded dictionaries.
 */
export function getGrantDedupKeys(grant) {
  if (!grant) return [];
  const keys = new Set();

  // 1. Direct numeric Grants.gov Opportunity ID (5 to 8 digits)
  const idStr = String(grant.id || '').trim();
  if (/^\d{5,8}$/.test(idStr)) keys.add(`id:${idStr}`);

  const gidStr = String(grant.grant_id || '').trim();
  const cleanGid = gidStr.replace(/^grants-gov-/, '').trim();
  if (/^\d{5,8}$/.test(cleanGid)) keys.add(`id:${cleanGid}`);

  // 2. Extract numeric ID from Grants.gov URLs (e.g. oppId=350821 or detail/359157)
  for (const f of [grant.application_url, grant.url, grant.additional_info_url]) {
    if (typeof f === 'string') {
      const m = f.match(/(?:oppId=|opp_id=|detail\/)(\d{5,8})/i);
      if (m && m[1]) keys.add(`id:${m[1]}`);
    }
  }

  // 3. Match by official federal opportunity / solicitation number (e.g., PAR-27-077, 26-503, DOD-26-072)
  const oppNum = String(grant.opportunity_number || '').trim().toUpperCase();
  const rawCodes = `${oppNum} ${gidStr}`;
  const codeMatches = rawCodes.match(/([A-Z]{2,5}-\d{2,3}-\d{2,4}|\d{2,3}-\d{3,5})/g);
  if (codeMatches) {
    codeMatches.forEach(c => keys.add(`opp:${c.toUpperCase()}`));
  } else if (oppNum && oppNum.length >= 4) {
    keys.add(`opp:${oppNum}`);
  }

  // 4. Normalized title slug (collapses punctuation and whitespace)
  const title = String(grant.title || '').toLowerCase();
  const slug = title.replace(/[^a-z0-9]/g, '').slice(0, 28);
  if (slug && slug.length >= 10) keys.add(`title:${slug}`);

  return Array.from(keys);
}

/**
 * Deduplicates an array of grants dynamically, merging duplicates sharing any identity signal.
 */
export function deduplicateGrants(grantList) {
  if (!Array.isArray(grantList)) return [];

  const canonicalGroups = [];

  for (const raw of grantList) {
    if (!raw) continue;
    const itemKeys = getGrantDedupKeys(raw);

    const matchedGroup = canonicalGroups.find(g => itemKeys.some(k => g.keys.has(k)));

    if (!matchedGroup) {
      canonicalGroups.push({ keys: new Set(itemKeys), grant: { ...raw } });
    } else {
      itemKeys.forEach(k => matchedGroup.keys.add(k));
      const existing = matchedGroup.grant;

      const isPreferred =
        (String(raw.grant_id || '').startsWith('grants-gov-') && !String(existing.grant_id || '').startsWith('grants-gov-')) ||
        (raw.is_drafted && !existing.is_drafted) ||
        ((raw.match_score?.total || 0) > (existing.match_score?.total || 0));

      const merged = isPreferred
        ? { ...existing, ...raw }
        : { ...raw, ...existing };

      merged.is_drafted = Boolean(existing.is_drafted || raw.is_drafted);
      if (existing.draft_location || raw.draft_location) {
        merged.draft_location = existing.draft_location || raw.draft_location;
      }
      if (existing.status === 'ready_for_review' || raw.status === 'ready_for_review') {
        merged.status = 'ready_for_review';
      }
      matchedGroup.grant = merged;
    }
  }

  return canonicalGroups.map(group => {
    const g = group.grant;
    const idKey = Array.from(group.keys).find(k => k.startsWith('id:'));
    if (idKey) {
      const oppId = idKey.replace('id:', '');
      return {
        ...g,
        id: oppId,
        grant_id: `grants-gov-${oppId}`,
        application_url: `https://www.grants.gov/search-results-detail/${oppId}`,
        url: `https://www.grants.gov/search-results-detail/${oppId}`,
      };
    }
    return g;
  });
}

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
      const raw = data.grants || [];
      const deduped = deduplicateGrants(raw);
      setGrants(deduped);
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
    if (!id) return undefined;
    const searchKeys = getGrantDedupKeys({ id, grant_id: id, opportunity_number: id });
    return grants.find(g => {
      if (String(g.id) === String(id) || String(g.grant_id) === String(id)) return true;
      const gKeys = getGrantDedupKeys(g);
      if (searchKeys.some(sk => gKeys.includes(sk))) return true;
      return false;
    });
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
