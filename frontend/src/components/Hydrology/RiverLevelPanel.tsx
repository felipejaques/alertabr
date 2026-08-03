"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface HydroStation {
  estacao_id: number;
  codigo_ana: string;
  nome: string;
  rio_nome: string;
  municipio_id: number;
  nivel_atual: number;
  status: "normal" | "atencao" | "alerta" | "emergencia";
  data_hora: string;
  limiares: {
    atencao: number | null;
    alerta: number | null;
    emergencia: number | null;
  };
}

interface HydroStatus {
  total_stations: number;
  alerts_count: number;
  alerts: HydroStation[];
}

interface RiverLevelPanelProps {
  state: string | null;
  onStationClick?: (municipioId: number) => void;
}

const STATUS_STYLES: Record<string, { bg: string; border: string; icon: string; label: string }> = {
  emergencia: { bg: "bg-purple-50", border: "border-purple-500", icon: "🟣", label: "Emergência" },
  alerta: { bg: "bg-red-50", border: "border-red-400", icon: "🔴", label: "Alerta" },
  atencao: { bg: "bg-yellow-50", border: "border-yellow-400", icon: "🟡", label: "Atenção" },
  normal: { bg: "bg-blue-50", border: "border-blue-300", icon: "🔵", label: "Normal" },
};

export default function RiverLevelPanel({ state, onStationClick }: RiverLevelPanelProps) {
  const [hydroStatus, setHydroStatus] = useState<HydroStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!state) {
      setHydroStatus(null);
      return;
    }

    const fetchHydroStatus = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_URL}/api/v1/hydrology/status?state=${state}`);
        if (!res.ok) throw new Error("Falha ao buscar dados hidrológicos");
        const data = await res.json();
        setHydroStatus(data);
      } catch (e) {
        setError("Erro ao carregar dados de rios");
        console.error(e);
      }
      setLoading(false);
    };

    fetchHydroStatus();
    // Atualizar a cada 2 minutos (dados ANA atualizam a cada 2h)
    const interval = setInterval(fetchHydroStatus, 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, [state]);

  if (!state) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        Selecione um estado para ver dados hidrológicos
      </div>
    );
  }

  if (loading && !hydroStatus) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        Carregando dados de rios...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-400 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header com resumo */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="text-sm font-semibold text-gray-800">
          Nível de Rios — {state}
        </h3>
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-500">
            {hydroStatus?.total_stations || 0} estações
          </span>
          {hydroStatus && hydroStatus.alerts_count > 0 && (
            <span className="bg-red-500 text-white px-2 py-0.5 rounded-full text-xs ml-1">
              {hydroStatus.alerts_count}
            </span>
          )}
        </div>
      </div>

      {/* Indicadores rápidos */}
      {hydroStatus && hydroStatus.alerts_count > 0 && (
        <div className="grid grid-cols-3 gap-1 p-2 border-b bg-gray-50">
          {["emergencia", "alerta", "atencao"].map((status) => {
            const count = hydroStatus.alerts.filter((a) => a.status === status).length;
            const style = STATUS_STYLES[status];
            return (
              <div key={status} className="text-center">
                <span className="text-xs">{style.icon}</span>
                <p className="text-xs font-medium text-gray-700">{count}</p>
                <p className="text-[10px] text-gray-500">{style.label}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Lista de estações em alerta */}
      <div className="flex-1 overflow-y-auto">
        {hydroStatus && hydroStatus.alerts_count === 0 && (
          <div className="p-4 text-center text-gray-400 text-sm">
            <span className="text-lg block mb-1">✓</span>
            Todas as estações em nível normal
          </div>
        )}

        {hydroStatus?.alerts.map((station) => {
          const style = STATUS_STYLES[station.status] || STATUS_STYLES.normal;
          const percentOfAlert = station.limiares.alerta
            ? ((station.nivel_atual / station.limiares.alerta) * 100).toFixed(0)
            : null;

          return (
            <button
              key={station.estacao_id}
              onClick={() => onStationClick?.(station.municipio_id)}
              className={`w-full text-left p-3 border-l-4 ${style.border} ${style.bg} hover:brightness-95 transition-all border-b border-gray-100`}
            >
              <div className="flex items-start gap-2">
                <span className="text-sm">{style.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {station.rio_nome || "Rio"}
                  </p>
                  <p className="text-xs text-gray-600 truncate">
                    {station.nome}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-semibold text-gray-700">
                      {station.nivel_atual.toFixed(2)} m
                    </span>
                    {percentOfAlert && (
                      <span className="text-[10px] text-gray-500">
                        ({percentOfAlert}% do alerta)
                      </span>
                    )}
                  </div>

                  {/* Barra visual de nível */}
                  <div className="mt-1.5">
                    <NivelBar
                      nivel={station.nivel_atual}
                      atencao={station.limiares.atencao}
                      alerta={station.limiares.alerta}
                      emergencia={station.limiares.emergencia}
                    />
                  </div>

                  <p className="text-[10px] text-gray-400 mt-1">
                    {new Date(station.data_hora).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
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

/** Barra visual indicando nível atual em relação aos limiares. */
function NivelBar({
  nivel,
  atencao,
  alerta,
  emergencia,
}: {
  nivel: number;
  atencao: number | null;
  alerta: number | null;
  emergencia: number | null;
}) {
  // Usar o maior limiar como referência (100% da barra)
  const maxRef = emergencia || alerta || atencao || nivel;
  if (!maxRef || maxRef <= 0) return null;

  const barMax = maxRef * 1.2; // 20% além do maior limiar
  const pct = Math.min((nivel / barMax) * 100, 100);
  const pctAtencao = atencao ? (atencao / barMax) * 100 : null;
  const pctAlerta = alerta ? (alerta / barMax) * 100 : null;
  const pctEmergencia = emergencia ? (emergencia / barMax) * 100 : null;

  let barColor = "bg-blue-400";
  if (emergencia && nivel >= emergencia) barColor = "bg-purple-500";
  else if (alerta && nivel >= alerta) barColor = "bg-red-400";
  else if (atencao && nivel >= atencao) barColor = "bg-yellow-400";

  return (
    <div className="relative h-2 bg-gray-200 rounded-full overflow-visible">
      {/* Barra de nível */}
      <div
        className={`absolute left-0 top-0 h-full rounded-full ${barColor} transition-all`}
        style={{ width: `${pct}%` }}
      />
      {/* Marcadores de limiar */}
      {pctAtencao && (
        <div
          className="absolute top-0 h-full w-px bg-yellow-600 opacity-70"
          style={{ left: `${pctAtencao}%` }}
          title={`Atenção: ${atencao?.toFixed(2)}m`}
        />
      )}
      {pctAlerta && (
        <div
          className="absolute top-0 h-full w-px bg-red-600 opacity-70"
          style={{ left: `${pctAlerta}%` }}
          title={`Alerta: ${alerta?.toFixed(2)}m`}
        />
      )}
      {pctEmergencia && (
        <div
          className="absolute top-0 h-full w-px bg-purple-700 opacity-70"
          style={{ left: `${pctEmergencia}%` }}
          title={`Emergência: ${emergencia?.toFixed(2)}m`}
        />
      )}
    </div>
  );
}
