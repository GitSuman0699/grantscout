/**
 * GrantScout Date Utilities
 * 
 * Provides consistent formatting for timestamps, pipeline freshness,
 * and 'Grants listed as of [Date]' indicators across the dashboard.
 */

export function formatAsOfDate(lastScan, grants = []) {
  let dateObj = null;

  if (lastScan) {
    const parsed = new Date(lastScan);
    if (!isNaN(parsed.getTime())) {
      dateObj = parsed;
    }
  }

  if (!dateObj && Array.isArray(grants) && grants.length > 0) {
    const timestamps = grants
      .map(g => g.discovered_at || g.updated_at || g.created_at || g.post_date)
      .filter(Boolean)
      .map(t => new Date(t))
      .filter(d => !isNaN(d.getTime()));

    if (timestamps.length > 0) {
      dateObj = new Date(Math.max(...timestamps.map(d => d.getTime())));
    }
  }

  if (!dateObj) {
    dateObj = new Date();
  }

  const dateString = dateObj.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).toUpperCase(); // e.g. "SEP 3, 2026"

  const fullDateString = dateObj.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return {
    dateString,
    fullDateString,
    dateObj,
  };
}
