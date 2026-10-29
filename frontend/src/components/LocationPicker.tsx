import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { api } from "../lib/api";
import type { GeoSuggestion } from "../lib/types";

const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946];
const DEFAULT_ZOOM = 13;
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Leaflet's default marker image URLs are resolved by the bundler, so point the
// default icon at the Vite-hashed asset URLs instead of the CSS-relative paths.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

export interface PickedLocation {
  lat: number;
  lng: number;
  address?: string;
  city?: string;
}

interface LocationPickerProps {
  lat: number | null;
  lng: number | null;
  onPick: (location: PickedLocation) => void;
}

const combineLine = (line1?: string | null, postal?: string | null) =>
  [line1, postal].filter(Boolean).join(", ");

export function LocationPicker({ lat, lng, onPick }: LocationPickerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  const onPickRef = useRef(onPick);
  onPickRef.current = onPick;

  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<GeoSuggestion[]>([]);
  const [searching, setSearching] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const placeMarker = useCallback((la: number, ln: number, recenter: boolean) => {
    const map = mapRef.current;
    if (!map) return;
    if (!markerRef.current) {
      const marker = L.marker([la, ln], { draggable: true }).addTo(map);
      marker.on("dragend", () => {
        const pos = marker.getLatLng();
        void resolvePin(pos.lat, pos.lng, false);
      });
      markerRef.current = marker;
    } else {
      markerRef.current.setLatLng([la, ln]);
    }
    if (recenter) {
      map.flyTo([la, ln], Math.max(map.getZoom(), 15));
    }
  }, []);

  const resolvePin = useCallback(
    async (la: number, ln: number, recenter: boolean) => {
      // Save the coordinates immediately; the address lookup can fail independently.
      placeMarker(la, ln, recenter);
      onPickRef.current({ lat: la, lng: ln });
      setResolving(true);
      setError(null);
      try {
        const r = await api.geoReverse(la, ln);
        onPickRef.current({
          lat: la,
          lng: ln,
          address: combineLine(r.line1, r.postal_code) || r.label || undefined,
          city: r.city ?? undefined,
        });
      } catch {
        // Coordinates are still valid even if reverse geocoding fails.
      } finally {
        setResolving(false);
      }
    },
    [placeMarker],
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: lat != null && lng != null ? [lat, lng] : DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: OSM_ATTRIBUTION,
    }).addTo(map);
    map.on("click", (e: L.LeafletMouseEvent) => {
      void resolvePin(e.latlng.lat, e.latlng.lng, true);
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [lat, lng, resolvePin]);

  // Reflect externally-set coordinates (e.g. a picked search result).
  useEffect(() => {
    if (lat == null || lng == null) return;
    const current = markerRef.current?.getLatLng();
    if (current && Math.abs(current.lat - lat) < 1e-6 && Math.abs(current.lng - lng) < 1e-6) {
      return;
    }
    placeMarker(lat, lng, false);
  }, [lat, lng, placeMarker]);

  // Debounced forward-geocoding search.
  useEffect(() => {
    const q = query.trim();
    if (q.length < 3) {
      setSuggestions([]);
      return;
    }
    const handle = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await api.geoSearch(q, 5);
        setSuggestions(res.results);
        setOpen(true);
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 400);
    return () => clearTimeout(handle);
  }, [query]);

  const chooseSuggestion = (s: GeoSuggestion) => {
    setOpen(false);
    setQuery(s.label);
    placeMarker(s.lat, s.lng, true);
    onPickRef.current({
      lat: s.lat,
      lng: s.lng,
      address: combineLine(s.line1, s.postal_code) || s.label,
      city: s.city ?? undefined,
    });
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by this browser.");
      return;
    }
    setResolving(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        void resolvePin(pos.coords.latitude, pos.coords.longitude, true);
      },
      () => {
        setResolving(false);
        setError("Could not access your location. Please search or drop a pin.");
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  return (
    <div className="map-picker">
      <div className="map-search">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="Search an area, street or landmark…"
          aria-label="Search pickup location"
        />
        <button type="button" className="btn btn-ghost btn-sm" onClick={useMyLocation}>
          Use my location
        </button>
        {open && suggestions.length > 0 && (
          <ul className="map-suggestions">
            {suggestions.map((s, i) => (
              <li key={`${s.lat}-${s.lng}-${i}`}>
                <button type="button" onClick={() => chooseSuggestion(s)}>
                  {s.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div ref={containerRef} className="map-canvas" />

      <div className="map-hint muted small">
        {resolving
          ? "Resolving address…"
          : searching
            ? "Searching places…"
            : error ?? "Drag the pin or tap the map to set the exact pickup point."}
      </div>
    </div>
  );
}
