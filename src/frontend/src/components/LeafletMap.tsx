import { useEffect, useRef } from "react";
import L from "leaflet";

/**
 * A minimal Leaflet wrapper that creates a map on mount and
 * DESTROYS it on unmount. Parent components force remount by
 * changing the React `key` prop whenever filters change.
 * This avoids every single Leaflet-in-React lifecycle bug.
 */
export function LeafletMap({
  onMap,
  className = "h-[420px]",
  tiles = false,
}: {
  onMap: (map: L.Map) => void;
  className?: string;
  tiles?: boolean;
}) {
  const el = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!el.current) return;
    const m = L.map(el.current, {
      maxBounds: [[47.2, 5.8], [55.1, 15.1]],
      maxBoundsViscosity: 1,
      minZoom: 5,
      attributionControl: false,
    }).setView([51.2, 10.4], 6);

    if (tiles) {
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19, attribution: "© OpenStreetMap",
      }).addTo(m);
    }

    // Let the container finish rendering
    setTimeout(() => { m.invalidateSize(); onMap(m); }, 80);

    return () => { m.remove(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={el} className={`${className} rounded-lg overflow-hidden bg-ink`} />;
}
