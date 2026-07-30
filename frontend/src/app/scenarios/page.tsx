"use client";

import { useState, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Scenario {
  id: string;
  name: string;
  description: string;
}

interface ScenarioDetail {
  id: string;
  name: string;
  description: string;
  impacts: Record<
    string,
    {
      precipitation_factor: number;
      temperature_factor: number;
      primary_risk: string;
      description: string;
      affected_states: string[];
      severity_projection: string;
    }
  >;
}

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [activeScenario, setActiveScenario] = useState<ScenarioDetail | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/scenarios`)
      .then((r) => r.json())
      .then(setScenarios)
      .catch(console.error);
  }, []);

  const loadScenario = async (id: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/scenarios/${id}`);
      const data = await res.json();
      setActiveScenario(data);
    } catch (e) {
      console.error(e);
    }
  };

  const RISK_TYPE_LABELS: Record<string, { icon: string; label: string }> = {
    inundacao: { icon: "🌊", label: "Inundação" },
    seca: { icon: "☀️", label: "Seca" },
  };

  const SEVERITY_COLORS: Record<string, string> = {
    alto_a_critico: "bg-red-100 text-red-800 border-red-200",
    moderado_a_alto: "bg-orange-100 text-orange-800 border-orange-200",
    moderado: "bg-yellow-100 text-yellow-800 border-yellow-200",
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">
        Simulação de Cenários
      </h1>
      <p className="text-gray-500 mb-6">
        Visualize o impacto projetado de fenômenos climáticos por região do Brasil
      </p>

      {/* Seletor de cenário */}
      <div className="flex gap-4 mb-8">
        {scenarios.map((s) => (
          <button
            key={s.id}
            onClick={() => loadScenario(s.id)}
            className={`px-6 py-3 rounded-lg border-2 transition-all ${
              activeScenario?.id === s.id
                ? "border-blue-500 bg-blue-50 shadow-md"
                : "border-gray-200 hover:border-blue-300 hover:bg-gray-50"
            }`}
          >
            <p className="text-lg font-semibold">
              {s.id === "el-nino" ? "🌊" : "❄️"} {s.name.split(" - ")[0]}
            </p>
            <p className="text-xs text-gray-500 mt-1">{s.description.slice(0, 50)}...</p>
          </button>
        ))}
      </div>

      {/* Detalhes do cenário */}
      {activeScenario && (
        <div>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            {activeScenario.name}
          </h2>
          <p className="text-gray-600 mb-6">{activeScenario.description}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(activeScenario.impacts).map(([region, impact]) => {
              const riskType = RISK_TYPE_LABELS[impact.primary_risk] || {
                icon: "⚠️",
                label: impact.primary_risk,
              };
              const sevColor =
                SEVERITY_COLORS[impact.severity_projection] || SEVERITY_COLORS.moderado;

              return (
                <div
                  key={region}
                  className="bg-white rounded-lg border shadow-sm p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-800">{region}</h3>
                    <span className="text-xl">{riskType.icon}</span>
                  </div>

                  <p className="text-sm text-gray-600 mb-3">
                    {impact.description}
                  </p>

                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Precipitação</span>
                      <span className="font-medium">
                        {impact.precipitation_factor > 1
                          ? `+${Math.round((impact.precipitation_factor - 1) * 100)}%`
                          : `-${Math.round((1 - impact.precipitation_factor) * 100)}%`}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Temperatura</span>
                      <span className="font-medium">
                        {impact.temperature_factor > 1
                          ? `+${Math.round((impact.temperature_factor - 1) * 100)}%`
                          : `-${Math.round((1 - impact.temperature_factor) * 100)}%`}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Risco principal</span>
                      <span className="font-medium">{riskType.label}</span>
                    </div>
                  </div>

                  <div className="mt-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${sevColor}`}
                    >
                      {impact.severity_projection.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-1">
                    {impact.affected_states.map((uf) => (
                      <span
                        key={uf}
                        className="text-xs bg-gray-100 px-1.5 py-0.5 rounded"
                      >
                        {uf}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!activeScenario && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-5xl mb-4">🌍</p>
          <p>Selecione um cenário acima para visualizar as projeções</p>
        </div>
      )}
    </div>
  );
}
