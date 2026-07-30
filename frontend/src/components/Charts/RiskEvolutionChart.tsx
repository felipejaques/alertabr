"use client";

import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Props {
  municipalityId: number;
  period: "7d" | "30d" | "90d";
}

interface DataPoint {
  date: string;
  risk: number;
}

export default function RiskEvolutionChart({ municipalityId, period }: Props) {
  const [data, setData] = useState<DataPoint[]>([]);
  const [currentRisk, setCurrentRisk] = useState<number>(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/risk/${municipalityId}`);
        const risk = await res.json();
        setCurrentRisk(risk.index || 0);
      } catch (e) {
        console.error(e);
      }
      // Gerar dados simulados de evolução (API não tem histórico de risco ainda)
      setData(generateRiskEvolution(period, currentRisk));
    };

    fetchData();
  }, [municipalityId, period]);

  return (
    <div className="bg-white rounded-lg shadow-sm p-4 lg:col-span-2">
      <h3 className="font-medium text-gray-800 mb-4">
        Evolução do Índice de Risco
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(value: number) => [`${value}`, "Índice de Risco"]}
          />
          <ReferenceLine y={75} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "Crítico", fontSize: 10 }} />
          <ReferenceLine y={50} stroke="#f97316" strokeDasharray="3 3" label={{ value: "Alto", fontSize: 10 }} />
          <ReferenceLine y={25} stroke="#eab308" strokeDasharray="3 3" label={{ value: "Moderado", fontSize: 10 }} />
          <Area
            type="monotone"
            dataKey="risk"
            stroke="#f97316"
            fill="url(#riskGradient)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function generateRiskEvolution(period: string, currentRisk: number): DataPoint[] {
  const days = period === "7d" ? 7 : period === "30d" ? 30 : 90;
  const data: DataPoint[] = [];
  const now = new Date();
  const baseRisk = currentRisk || 30;

  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    // Simular evolução com tendência ao valor atual
    const progress = (days - i) / days;
    const noise = (Math.random() - 0.5) * 20;
    const risk = Math.max(0, Math.min(100, baseRisk * progress + 20 * (1 - progress) + noise));

    data.push({
      date: date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
      risk: Math.round(risk * 10) / 10,
    });
  }
  return data;
}
