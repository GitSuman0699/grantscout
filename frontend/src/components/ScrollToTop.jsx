import { useEffect, useRef } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

const scrollPositions = new Map();

export default function ScrollToTop() {
  const location = useLocation();
  const navType = useNavigationType(); // 'POP' (back/forward), 'PUSH', 'REPLACE'
  const prevPathRef = useRef(location.pathname);

  // Save scroll position on scroll
  useEffect(() => {
    const handleScroll = () => {
      scrollPositions.set(location.pathname, window.scrollY);
      try {
        sessionStorage.setItem(`scroll_${location.pathname}`, String(window.scrollY));
      } catch {
        // ignore storage errors
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [location.pathname]);

  // Restore or reset scroll on route change
  useEffect(() => {
    const currentPath = location.pathname;
    const isReturning = navType === 'POP' || location.state?.from === currentPath;

    let targetY = 0;
    if (isReturning) {
      // Check in-memory map first, then sessionStorage
      const memoryY = scrollPositions.get(currentPath);
      if (memoryY !== undefined) {
        targetY = memoryY;
      } else {
        const stored = sessionStorage.getItem(`scroll_${currentPath}`);
        if (stored) targetY = parseInt(stored, 10) || 0;
      }
    }

    // Restore scroll position with multiple frame checks for async content loading
    const restoreScroll = () => {
      window.scrollTo({
        top: targetY,
        left: 0,
        behavior: 'instant'
      });
    };

    // Immediate
    restoreScroll();
    // After render frame
    requestAnimationFrame(restoreScroll);
    // After dynamic data loads (50ms, 150ms)
    const t1 = setTimeout(restoreScroll, 50);
    const t2 = setTimeout(restoreScroll, 150);

    prevPathRef.current = currentPath;

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [location.pathname, navType]);

  return null;
}
