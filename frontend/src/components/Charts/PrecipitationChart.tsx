"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Props {
  municipalityId: number;
  period: "7d" | "30d" | "90d";
}

interface DataPoint {
  date: string;
  value: number;
}

export default function PrecipitationChart({ municipalityId, period }: Props) {
  const [data, setData] = useState<DataPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const limit = period === "7d" ? 168 : period === "30d" ? 720 : 2160;
        const res = await fetch(
          `${API_URL}/api/v1/weather/municipality/${municipalityId}/readings?limit=${limit}`
        );
        const readings = await res.json();

        // Agrupar por dia
        const dailyMap: Record<string, number> = {};
        for (const r of readings) {
          const date = r.data_hora?.split("T")[0];
          if (date && r.precipitacao != null) {
            dailyMap[date] = (dailyMap[date] || 0) + r.precipitacao;
          }
        }

        const chartData = Object.entries(dailyMap)
          .map(([date, value]) => ({
            date: new Date(date).toLocaleDateString("pt-BR", {
              day: "2-digit",
              month: "2-digit",
            }),
            value: Math.round(value * 10) / 10,
          }))
          .sort((a, b) => a.date.localeCompare(b.date));

        setData(chartData.length > 0 ? chartData : generateMockData(period));
      } catch (e) {
        console.error(e);
        // Dados simulados caso não haja dados reais
        setData(generateMockData(period));
      }
      setLoading(false);
    };

    fetchData();
  }, [municipalityId, period]);

  return (
    <div className="bg-white rounded-lg shadow-sm p-4">
      <h3 className="font-medium text-gray-800 mb-4">
        Precipitação Acumulada (mm/dia)
      </h3>
      {loading ? (
        <div className="h-[250px] flex items-center justify-center text-gray-400">
          Carregando...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              name="Precipitação (mm)"
              strokeWidth={2}
              dot={false}
            />
            <ReferenceLine
              y={80}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={{ value: "Limiar 80mm", position: "top", fontSize: 10 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function generateMockData(period: string): DataPoint[] {
  const days = period === "7d" ? 7 : period === "30d" ? 30 : 90;
  const data: DataPoint[] = [];
  const now = new Date();
  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    data.push({
      date: date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
      value: Math.round(Math.random() * 60 * 10) / 10,
    });
  }
  return data;
}
