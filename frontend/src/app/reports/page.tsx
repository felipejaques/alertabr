"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";

const PrecipitationChart = dynamic(
  () => import("@/components/Charts/PrecipitationChart"),
  { ssr: false }
);
const TemperatureChart = dynamic(
  () => import("@/components/Charts/TemperatureChart"),
  { ssr: false }
);
const RiskEvolutionChart = dynamic(
  () => import("@/components/Charts/RiskEvolutionChart"),
  { ssr: false }
);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Municipality {
  id: number;
  codigo_ibge: number;
  nome: string;
}

export default function ReportsPage() {
  const [states, setStates] = useState<{ sigla: string; nome: string }[]>([]);
  const [selectedState, setSelectedState] = useState("");
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [selectedMunicipality, setSelectedMunicipality] = useState<number | null>(null);
  const [period, setPeriod] = useState<"7d" | "30d" | "90d">("30d");

  // Buscar estados
  useEffect(() => {
    fetch(`${API_URL}/api/v1/states`)
      .then((r) => r.json())
      .then(setStates)
      .catch(console.error);
  }, []);

  // Buscar municípios quando estado muda
  useEffect(() => {
    if (!selectedState) {
      setMunicipalities([]);
      setSelectedMunicipality(null);
      return;
    }
    fetch(`${API_URL}/api/v1/states/${selectedState}/municipalities`)
      .then((r) => r.json())
      .then((data) => {
        setMunicipalities(data);
        setSelectedMunicipality(null);
      })
      .catch(console.error);
  }, [selectedState]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Relatórios e Análises
      </h1>

      {/* Seletores */}
      <div className="flex flex-wrap gap-4 mb-6 bg-white p-4 rounded-lg shadow-sm">
        {/* Estado */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Estado
          </label>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="border rounded-md px-3 py-2 text-sm"
          >
            <option value="">Selecione...</option>
            {states.map((s) => (
              <option key={s.sigla} value={s.sigla}>
                {s.nome}
              </option>
            ))}
          </select>
        </div>

        {/* Município */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Município
          </label>
          <select
            value={selectedMunicipality || ""}
            onChange={(e) => setSelectedMunicipality(Number(e.target.value) || null)}
            className="border rounded-md px-3 py-2 text-sm"
            disabled={!selectedState}
          >
            <option value="">Selecione...</option>
            {municipalities.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nome}
              </option>
            ))}
          </select>
        </div>

        {/* Período */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Período
          </label>
          <div className="flex gap-1">
            {(["7d", "30d", "90d"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-2 rounded-md text-sm ${
                  period === p
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {p === "7d" ? "7 dias" : p === "30d" ? "30 dias" : "90 dias"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Gráficos */}
      {selectedMunicipality ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PrecipitationChart
            municipalityId={selectedMunicipality}
            period={period}
          />
          <TemperatureChart
            municipalityId={selectedMunicipality}
            period={period}
          />
          <RiskEvolutionChart
            municipalityId={selectedMunicipality}
            period={period}
          />
        </div>
      ) : (
        <div className="text-center py-20 text-gray-400">
          <p className="text-5xl mb-4">📊</p>
          <p>Selecione um estado e município para visualizar os gráficos</p>
        </div>
      )}
    </div>
  );
}
