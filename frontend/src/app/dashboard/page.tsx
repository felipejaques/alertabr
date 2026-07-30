"use client";

import dynamic from "next/dynamic";
import { useState, useEffect } from "react";
import MapLegend from "@/components/Map/MapLegend";
import LayerToggle from "@/components/Map/LayerToggle";
import AlertPanel from "@/components/Alerts/AlertPanel";
import MunicipalityList from "@/components/Sidebar/MunicipalityList";

// Leaflet não funciona em SSR - carregar apenas no client
const BrazilMap = dynamic(() => import("@/components/Map/BrazilMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-100">
      <p className="text-gray-400">Carregando mapa...</p>
    </div>
  ),
});

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface RiskData {
  municipio_id: number;
  nome: string;
  risk_index: number;
  classification: string;
  triggered_rules: string[];
}

export default function DashboardPage() {
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [selectedMunicipality, setSelectedMunicipality] = useState<{
    id: number;
    name: string;
  } | null>(null);
  const [activeLayer, setActiveLayer] = useState("composite");
  const [riskData, setRiskData] = useState<RiskData[]>([]);
  const [sidebarTab, setSidebarTab] = useState<"municipios" | "alertas">("municipios");

  // Buscar dados de risco quando estado é selecionado
  useEffect(() => {
    if (!selectedState) {
      setRiskData([]);
      return;
    }

    const fetchRisk = async () => {
      try {
        const res = await fetch(
          `${API_URL}/api/v1/risk/map?state=${selectedState}`
        );
        const data = await res.json();
        setRiskData(data.municipalities || []);
      } catch (e) {
        console.error("Erro ao buscar risco:", e);
      }
    };

    fetchRisk();
    // Auto-refresh a cada 5 min
    const interval = setInterval(fetchRisk, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [selectedState]);

  return (
    <div className="flex flex-col lg:flex-row h-screen">
      {/* Mapa principal */}
      <main className="flex-1 relative">
        <BrazilMap
          onStateSelect={(uf) => {
            setSelectedState(uf);
            setSelectedMunicipality(null);
          }}
          onMunicipalitySelect={(id, name) => {
            setSelectedMunicipality({ id, name });
          }}
          riskData={riskData}
          activeLayer={activeLayer}
        />
        <MapLegend />
        {selectedState && (
          <LayerToggle activeLayer={activeLayer} onChange={setActiveLayer} />
        )}
      </main>

      {/* Sidebar */}
      <aside className="w-full lg:w-80 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
        {/* Info do município selecionado */}
        {selectedMunicipality && (
          <div className="p-3 border-b bg-blue-50">
            <p className="text-xs text-blue-600 font-medium">Selecionado</p>
            <p className="text-sm font-semibold text-gray-800">
              {selectedMunicipality.name}
            </p>
            {riskData && (() => {
              const risk = riskData.find(
                (r) => r.municipio_id === selectedMunicipality.id
              );
              if (!risk) return null;
              return (
                <p className="text-xs text-gray-600 mt-1">
                  Risco: <span className="font-medium">{risk.classification}</span>{" "}
                  ({risk.risk_index})
                </p>
              );
            })()}
          </div>
        )}

        {/* Tabs */}
        {selectedState && (
          <div className="flex border-b">
            <button
              onClick={() => setSidebarTab("municipios")}
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                sidebarTab === "municipios"
                  ? "text-blue-700 border-b-2 border-blue-700 bg-blue-50"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Municípios ({riskData.length})
            </button>
            <button
              onClick={() => setSidebarTab("alertas")}
              className={`flex-1 py-2 text-xs font-medium transition-colors ${
                sidebarTab === "alertas"
                  ? "text-blue-700 border-b-2 border-blue-700 bg-blue-50"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Alertas
            </button>
          </div>
        )}

        {/* Conteúdo da tab */}
        <div className="flex-1 overflow-hidden">
          {!selectedState && (
            <div className="p-4 text-center text-gray-400 text-sm">
              Selecione um estado no mapa
            </div>
          )}

          {selectedState && sidebarTab === "municipios" && (
            <MunicipalityList
              municipalities={riskData}
              selectedId={selectedMunicipality?.id ?? null}
              onSelect={(id, name) => {
                setSelectedMunicipality({ id, name });
              }}
            />
          )}

          {selectedState && sidebarTab === "alertas" && (
            <AlertPanel
              state={selectedState}
              onAlertClick={(municipioId) => {
                const mun = riskData.find((r) => r.municipio_id === municipioId);
                if (mun) {
                  setSelectedMunicipality({ id: municipioId, name: mun.nome });
                }
              }}
            />
          )}
        </div>
      </aside>
    </div>
  );
}
