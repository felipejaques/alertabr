"use client";

const LEGEND_ITEMS = [
  { label: "Crítico (76-100)", color: "#ef4444" },
  { label: "Alto (51-75)", color: "#f97316" },
  { label: "Moderado (26-50)", color: "#eab308" },
  { label: "Baixo (0-25)", color: "#22c55e" },
];

export default function MapLegend() {
  return (
    <div className="absolute bottom-4 right-4 z-[1000] bg-white rounded-lg shadow-md p-3">
      <h4 className="text-xs font-semibold text-gray-700 mb-2">
        Índice de Risco
      </h4>
      <div className="space-y-1">
        {LEGEND_ITEMS.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            <div
              className="w-4 h-3 rounded-sm"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-xs text-gray-600">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
