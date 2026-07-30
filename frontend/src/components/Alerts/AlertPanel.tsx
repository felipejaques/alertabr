"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Alert {
  id: number;
  municipio_id: number;
  tipo: string;
  severidade: string;
  indice_risco: number;
  descricao: string;
  data_inicio: string;
  ativo: boolean;
}

interface AlertPanelProps {
  state: string | null;
  onAlertClick: (municipioId: number) => void;
}

const SEVERITY_STYLES: Record<string, { bg: string; border: string; icon: string }> = {
  critico: { bg: "bg-red-50", border: "border-red-400", icon: "🔴" },
  alto: { bg: "bg-orange-50", border: "border-orange-400", icon: "🟠" },
  moderado: { bg: "bg-yellow-50", border: "border-yellow-400", icon: "🟡" },
  baixo: { bg: "bg-green-50", border: "border-green-400", icon: "🟢" },
};

export default function AlertPanel({ state, onAlertClick }: AlertPanelProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>("");

  useEffect(() => {
    if (!state) return;

    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ state, active: "true" });
        if (filter) params.set("severity", filter);
        const res = await fetch(`${API_URL}/api/v1/alerts?${params}`);
        const data = await res.json();
        setAlerts(data);
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000);
    return () => clearInterval(interval);
  }, [state, filter]);

  if (!state) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        Selecione um estado para ver alertas
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="text-sm font-semibold text-gray-800">
          Alertas — {state}
        </h3>
        <span className="bg-red-500 text-white px-2 py-0.5 rounded-full text-xs">
          {alerts.length}
        </span>
      </div>

      {/* Filtros */}
      <div className="flex gap-1 p-2 border-b">
        {["", "critico", "alto", "moderado"].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilter(sev)}
            className={`px-2 py-1 rounded text-xs ${
              filter === sev
                ? "bg-blue-100 text-blue-800 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {sev || "Todos"}
          </button>
        ))}
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="p-4 text-center text-gray-400 text-sm">
            Carregando...
          </div>
        )}
        {!loading && alerts.length === 0 && (
          <div className="p-4 text-center text-gray-400 text-sm">
            Nenhum alerta ativo
          </div>
        )}
        {alerts.map((alert) => {
          const style = SEVERITY_STYLES[alert.severidade] || SEVERITY_STYLES.baixo;
          return (
            <button
              key={alert.id}
              onClick={() => onAlertClick(alert.municipio_id)}
              className={`w-full text-left p-3 border-l-4 ${style.border} ${style.bg} hover:brightness-95 transition-all border-b border-gray-100`}
            >
              <div className="flex items-start gap-2">
                <span className="text-sm">{style.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {alert.tipo} — Risco {alert.indice_risco}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5 truncate">
                    {alert.descricao}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(alert.data_inicio).toLocaleDateString("pt-BR")}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
