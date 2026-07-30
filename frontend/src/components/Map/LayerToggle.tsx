"use client";

interface LayerToggleProps {
  activeLayer: string;
  onChange: (layer: string) => void;
}

const LAYERS = [
  { id: "composite", label: "Risco Composto", icon: "🎯" },
  { id: "precipitation", label: "Precipitação", icon: "🌧️" },
  { id: "temperature", label: "Temperatura", icon: "🌡️" },
];

export default function LayerToggle({ activeLayer, onChange }: LayerToggleProps) {
  return (
    <div className="absolute top-4 right-4 z-[1000] bg-white rounded-lg shadow-md p-2">
      <p className="text-xs font-semibold text-gray-500 px-2 mb-1">Camadas</p>
      {LAYERS.map((layer) => (
        <button
          key={layer.id}
          onClick={() => onChange(layer.id)}
          className={`block w-full text-left px-3 py-1.5 rounded text-sm ${
            activeLayer === layer.id
              ? "bg-blue-100 font-medium text-blue-800"
              : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          {layer.icon} {layer.label}
        </button>
      ))}
    </div>
  );
}
