import { useEffect, useRef, useState } from 'react';

const NAV_ITEMS = [
  { id: 'upload', label: 'Upload' },
  { id: 'parser-summary', label: 'Parser Summary' },
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'c1-review', label: 'C1 Review' },
  { id: 'regression', label: 'Regression' },
  { id: 'traceability', label: 'Traceability' },
  { id: 'audit-log', label: 'Audit Log' },
  { id: 'export', label: 'Export' },
  { id: 'simulation', label: 'Simulation' },
  { id: 'test-results', label: 'Test Results' },
  { id: 'anomaly-review', label: 'Anomaly Review' },
  { id: 'draft-report', label: 'Draft Report' },
];

export default function StickyNav({ visibleSections }) {
  const [activeId, setActiveId] = useState('upload');
  const observerRef = useRef(null);

  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const intersecting = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (intersecting.length > 0) {
          setActiveId(intersecting[0].target.id);
        }
      },
      { rootMargin: '-5% 0px -65% 0px', threshold: 0 },
    );

    NAV_ITEMS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observerRef.current.observe(el);
    });

    return () => {
      if (observerRef.current) observerRef.current.disconnect();
    };
  }, [visibleSections]);

  function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  const visibleItems = NAV_ITEMS.filter((item) => visibleSections.has(item.id));

  if (visibleItems.length <= 1) return null;

  return (
    <nav className="sticky-nav" aria-label="Page sections">
      <p className="sticky-nav-title">Sections</p>
      <ul>
        {visibleItems.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              className={`sticky-nav-item${activeId === item.id ? ' sticky-nav-item--active' : ''}`}
              onClick={() => scrollToSection(item.id)}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
