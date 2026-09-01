import React, { useState, useEffect } from 'react';
import { Cpu, DollarSign, Zap, Archive, Shield, CheckCircle2, Layers, AlertTriangle } from 'lucide-react';
import { fetchModelTiers, fetchCacheStats, fetchTokenUsage } from '../services/api';

export default function OptimizationView() {
  const [modelTiers, setModelTiers] = useState([]);
  const [cacheStats, setCacheStats] = useState(null);
  const [tokenUsage, setTokenUsage] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      let hasError = false;

      // Fetch model tiers
      try {
        const tiersData = await fetchModelTiers();
        if (tiersData.tiers && Object.keys(tiersData.tiers).length > 0) {
          const mapped = Object.entries(tiersData.tiers).map(([tierName, cfg]) => {
            const assignedAgents = tiersData.agent_routing
              ? Object.entries(tiersData.agent_routing)
                  .filter(([, tier]) => tier === tierName)
                  .map(([agent]) => agent.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()))
                  .join(', ')
              : '—';

            return {
              tier: tierName.toUpperCase().replace(/_/g, ' ') + ' TIER',
              model: cfg.model_id || '—',
              agents: assignedAgents || '—',
              costIn: `$${cfg.cost_per_1k_input} / 1K in`,
              costOut: `$${cfg.cost_per_1k_output} / 1K out`,
              role: cfg.description || '',
              speed: cfg.max_tokens ? `${cfg.max_tokens} max tokens` : '—'
            };
          });
          setModelTiers(mapped);
        }
      } catch (err) {
        console.error('Failed to fetch model tiers:', err.message);
        hasError = true;
      }

      // Fetch cache stats
      try {
        const cache = await fetchCacheStats();
        setCacheStats(cache);
      } catch (err) {
        console.error('Failed to fetch cache stats:', err.message);
        hasError = true;
      }

      // Fetch token usage
      try {
        const tokens = await fetchTokenUsage();
        setTokenUsage(tokens);
      } catch (err) {
        console.error('Failed to fetch token usage:', err.message);
        hasError = true;
      }

      if (hasError) setError('Some data could not be loaded. Ensure the backend is running on port 8000.');
      setIsLoading(false);
    };
    loadData();
  }, []);

  // Derive display values from live data — no fallbacks
  const hitRate = cacheStats?.hit_rate_pct != null ? `${cacheStats.hit_rate_pct}%` : '—';
  const cacheSize = cacheStats ? `${cacheStats.size ?? 0} / ${cacheStats.max_size ?? 256} slots` : '—';
  const cacheMeta = cacheStats ? `${cacheStats.hits ?? 0} hits / ${cacheStats.misses ?? 0} misses • TTL ${cacheStats.ttl_seconds ?? 3600}s` : 'No cache data available';

  const totalCost = tokenUsage?.total_estimated_cost_usd != null ? `$${tokenUsage.total_estimated_cost_usd.toFixed(6)}` : '—';
  const totalTokens = tokenUsage?.total_tokens != null ? tokenUsage.total_tokens.toLocaleString() : '—';
  const tokenMeta = tokenUsage ? `${tokenUsage.total_invocations ?? 0} invocations • ${tokenUsage.cache_hits ?? 0} cached` : 'No token data available';

  const savingsPct = tokenUsage?.savings_from_cache_pct != null ? `${tokenUsage.savings_from_cache_pct}%` : '—';

  return (
    <div>
      {/* Title Header */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <span className="tag-badge tag-dark">COST EFFICIENCY ENGINE</span>
          <span className="tag-badge tag-green">
            <CheckCircle2 size={12} /> TIERED MODEL ROUTING
          </span>
        </div>

        <h1 className="font-heading hero-title" style={{ fontSize: '2.8rem', lineHeight: '0.95', color: 'var(--ink)' }}>
          COST & TOKEN OPTIMIZATION
        </h1>
        <p style={{ color: 'var(--ink-muted)', fontSize: '0.95rem', marginTop: '0.4rem', maxWidth: '750px' }}>
          Intelligent model tiering, LRU response caching, and prompt compression ensuring sustainable, low-cost autonomous operation.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="brutalist-card" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem', borderLeft: '4px solid var(--amber-signal)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--ink)' }}>
            <AlertTriangle size={16} color="var(--amber-signal)" />
            {error}
          </div>
        </div>
      )}

      {/* Summary Cards Grid — Responsive */}
      <div className="opt-summary-grid">
        <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-green">ACTIVE CACHE</span>
            <Archive size={18} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1', color: 'var(--ink)' }}>
            {hitRate}
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            CACHE HIT RATE
          </div>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.35rem' }}>
            {cacheMeta}
          </div>
        </div>

        <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-amber">TOTAL COST</span>
            <DollarSign size={18} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1', color: 'var(--ink)' }}>
            {totalCost}
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            ESTIMATED INFERENCE COST
          </div>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.35rem' }}>
            {tokenMeta}
          </div>
        </div>

        <div className="brutalist-card" style={{ padding: '1.25rem 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span className="tag-badge tag-dark">CACHE SAVINGS</span>
            <Zap size={18} />
          </div>
          <div className="font-heading" style={{ fontSize: '2.4rem', lineHeight: '1', color: 'var(--ink)' }}>
            {savingsPct}
          </div>
          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--ink-muted)' }}>
            RESPONSES SERVED FROM CACHE
          </div>
          <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--ink-faint)', marginTop: '0.35rem' }}>
            {totalTokens !== '—' ? `${totalTokens} total tokens processed` : 'No invocations yet'}
          </div>
        </div>
      </div>




      {/* Transaction History List */}
      {tokenUsage?.transactions && tokenUsage.transactions.length > 0 && (
        <div className="brutalist-card" style={{ padding: '1.5rem', marginTop: '1.5rem' }}>
          <h3 className="font-heading" style={{ fontSize: '1.6rem', marginBottom: '1.25rem' }}>
            RECENT INVOCATIONS (LAST 50)
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border-dark)', textAlign: 'left', color: 'var(--ink-muted)' }}>
                  <th style={{ padding: '0.75rem 0.5rem' }}>TIMESTAMP</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>AGENT</th>
                  <th style={{ padding: '0.75rem 0.5rem' }}>TIER</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>INPUT</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>OUTPUT</th>
                  <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>COST</th>
                </tr>
              </thead>
              <tbody>
                {tokenUsage.transactions.map((tx, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-dark)', backgroundColor: tx.cached ? 'var(--card-alt-bg)' : 'transparent' }}>
                    <td style={{ padding: '0.75rem 0.5rem', color: 'var(--ink)' }}>{new Date(tx.timestamp).toLocaleTimeString()}</td>
                    <td style={{ padding: '0.75rem 0.5rem', fontWeight: 'bold' }}>{tx.agent.toUpperCase()}</td>
                    <td style={{ padding: '0.75rem 0.5rem' }}>
                      <span className="tag-badge tag-neutral" style={{ fontSize: '0.65rem' }}>{tx.tier.toUpperCase()}</span>
                    </td>
                    <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{tx.input_tokens.toLocaleString()}</td>
                    <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>{tx.output_tokens.toLocaleString()}</td>
                    <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 'bold', color: tx.cached ? 'var(--green-signal)' : 'var(--ink)' }}>
                      {tx.cached ? 'CACHED ($0)' : `$${tx.cost_usd.toFixed(6)}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
