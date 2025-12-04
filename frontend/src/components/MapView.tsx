import React, { useMemo } from "react";
import { MapContainer, TileLayer, Polyline } from "react-leaflet";
import { RouteResponse } from "../api/client";

interface MapViewProps {
  route?: RouteResponse;
}

// Проста функція, що перетворює ID вузла в "штучні" координати.
// Для демонстрації роботи; у реальному проєкті заміниш на справжні lat/lng.
function nodeIdToLatLng(id: number): [number, number] {
  const baseLat = 50.45;
  const baseLng = 30.52;
  const step = 0.002;
  const lat = baseLat + (id % 10) * step;
  const lng = baseLng + Math.floor(id / 10) * step;
  return [lat, lng];
}

export const MapView: React.FC<MapViewProps> = ({ route }) => {
  const positions = useMemo<[number, number][]>(() => {
    if (!route || route.nodes.length === 0) return [];
    return route.nodes.map(nodeIdToLatLng);
  }, [route]);

  const center: [number, number] =
    positions.length > 0 ? positions[0] : [50.45, 30.52];

  return (
    <div className="map-wrapper">
      <MapContainer center={center} zoom={13} className="map-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {positions.length > 1 && <Polyline positions={positions} />}
      </MapContainer>
    </div>
  );
};
