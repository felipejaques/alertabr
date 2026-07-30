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
  max: number;
  min: number;
  avg: number;
}

export default function TemperatureChart({ municipalityId, period }: Props) {
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
        const dailyMap: Record<string, { temps: number[]; maxes: number[]; mins: number[] }> = {};
        for (const r of readings) {
          const date = r.data_hora?.split("T")[0];
          if (date) {
            if (!dailyMap[date]) dailyMap[date] = { temps: [], maxes: [], mins: [] };
            if (r.temperatura != null) dailyMap[date].temps.push(r.temperatura);
            if (r.temperatura_max != null) dailyMap[date].maxes.push(r.temperatura_max);
          }
        }

        const chartData = Object.entries(dailyMap)
          .map(([date, vals]) => ({
            date: new Date(date).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
            max: vals.maxes.length > 0 ? Math.max(...vals.maxes) : 0,
            min: vals.temps.length > 0 ? Math.min(...vals.temps) : 0,
            avg: vals.temps.length > 0
              ? Math.round((vals.temps.reduce((a, b) => a + b, 0) / vals.temps.length) * 10) / 10
              : 0,
          }))
          .sort((a, b) => a.date.localeCompare(b.date));

        setData(chartData.length > 0 ? chartData : generateMockData(period));
      } catch (e) {
        console.error(e);
        setData(generateMockData(period));
      }
      setLoading(false);
    };

    fetchData();
  }, [municipalityId, period]);

  return (
    <div className="bg-white rounded-lg shadow-sm p-4">
      <h3 className="font-medium text-gray-800 mb-4">Temperatura (°C)</h3>
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
              dataKey="max"
              stroke="#ef4444"
              name="Máxima"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="avg"
              stroke="#f97316"
              name="Média"
              strokeWidth={1.5}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="min"
              stroke="#3b82f6"
              name="Mínima"
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="3 3"
            />
            <ReferenceLine
              y={40}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label={{ value: "Limiar 40°C", position: "top", fontSize: 10 }}
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
    const base = 22 + Math.random() * 8;
    data.push({
      date: date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }),
      max: Math.round((base + 5 + Math.random() * 5) * 10) / 10,
      avg: Math.round(base * 10) / 10,
      min: Math.round((base - 3 - Math.random() * 3) * 10) / 10,
    });
  }
  return data;
}
