"use client";

import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import type { Layer, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface RiskData {
  municipio_id: number;
  risk_index: number;
  classification: string;
  triggered_rules: string[];
}

interface BrazilMapProps {
  onStateSelect: (uf: string) => void;
  onMunicipalitySelect: (id: number, name: string) => void;
  riskData?: RiskData[];
  activeLayer?: string;
}

const RISK_COLORS: Record<string, string> = {
  critico: "#ef4444",
  alto: "#f97316",
  moderado: "#eab308",
  baixo: "#22c55e",
};

function FitBounds({ geojson }: { geojson: any }) {
  const map = useMap();
  useEffect(() => {
    if (geojson && geojson.features?.length > 0) {
      const L = require("leaflet");
      const layer = L.geoJSON(geojson);
      map.fitBounds(layer.getBounds(), { padding: [20, 20] });
    }
  }, [geojson, map]);
  return null;
}

export default function BrazilMap({
  onStateSelect,
  onMunicipalitySelect,
  riskData,
  activeLayer,
}: BrazilMapProps) {
  const [statesGeoJSON, setStatesGeoJSON] = useState<any>(null);
  const [municipalitiesGeoJSON, setMunicipalitiesGeoJSON] = useState<any>(null);
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/geojson/states`)
      .then((r) => r.json())
      .then(setStatesGeoJSON)
      .catch(console.error);
  }, []);

  const handleStateClick = async (uf: string) => {
    setLoading(true);
    setSelectedState(uf);
    onStateSelect(uf);
    try {
      const res = await fetch(
        `${API_URL}/api/v1/geojson/municipalities?state=${uf}`
      );
      const data = await res.json();
      setMunicipalitiesGeoJSON(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const handleBackToStates = () => {
    setSelectedState(null);
    setMunicipalitiesGeoJSON(null);
  };

  const getRiskColor = (municipioId: number): string => {
    if (!riskData) return "#3b82f6";
    const risk = riskData.find((r) => r.municipio_id === municipioId);
    if (!risk) return "#94a3b8";
    return RISK_COLORS[risk.classification] || "#94a3b8";
  };

  const stateStyle = (): PathOptions => ({
    fillColor: "#3b82f6",
    weight: 1,
    opacity: 1,
    color: "#1e40af",
    fillOpacity: 0.3,
  });

  const municipalityStyle = (feature: any): PathOptions => ({
    fillColor: getRiskColor(feature?.properties?.id),
    weight: 0.5,
    opacity: 1,
    color: "#475569",
    fillOpacity: 0.65,
  });

  return (
    <div className="relative w-full h-full">
      {selectedState && (
        <button
          onClick={handleBackToStates}
          className="absolute top-4 left-4 z-[1000] bg-white px-3 py-2 rounded-lg shadow-md text-sm font-medium hover:bg-gray-50"
        >
          ← Voltar aos estados
        </button>
      )}

      {loading && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-white px-4 py-2 rounded-lg shadow-md text-sm">
          Carregando...
        </div>
      )}

      <MapContainer
        center={[-14.235, -51.925]}
        zoom={4}
        className="w-full h-full"
        style={{ minHeight: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />

        {statesGeoJSON && !selectedState && (
          <GeoJSON
            key="states"
            data={statesGeoJSON}
            style={stateStyle}
            onEachFeature={(feature, layer) => {
              layer.bindTooltip(feature.properties.nome || feature.properties.sigla);
              layer.on("click", () => {
                handleStateClick(feature.properties.sigla);
              });
            }}
          />
        )}

        {municipalitiesGeoJSON && selectedState && (
          <>
            <GeoJSON
              key={`municipalities-${selectedState}-${activeLayer}`}
              data={municipalitiesGeoJSON}
              style={municipalityStyle}
              onEachFeature={(feature, layer) => {
                const risk = riskData?.find(
                  (r) => r.municipio_id === feature.properties.id
                );
                const tooltip = risk
                  ? `<strong>${feature.properties.nome}</strong><br/>Risco: ${risk.classification} (${risk.risk_index})`
                  : `<strong>${feature.properties.nome}</strong>`;
                layer.bindTooltip(tooltip);
                layer.on("click", () => {
                  onMunicipalitySelect(
                    feature.properties.id,
                    feature.properties.nome
                  );
                });
              }}
            />
            <FitBounds geojson={municipalitiesGeoJSON} />
          </>
        )}
      </MapContainer>
    </div>
  );
}
