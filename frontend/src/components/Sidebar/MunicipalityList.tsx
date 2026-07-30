"use client";

import { useState, useMemo } from "react";

interface RiskData {
  municipio_id: number;
  nome: string;
  risk_index: number;
  classification: string;
  triggered_rules: string[];
}

interface MunicipalityListProps {
  municipalities: RiskData[];
  selectedId: number | null;
  onSelect: (id: number, name: string) => void;
}

const CLASSIFICATION_STYLES: Record<string, { dot: string; text: string }> = {
  critico: { dot: "bg-red-500", text: "text-red-700" },
  alto: { dot: "bg-orange-500", text: "text-orange-700" },
  moderado: { dot: "bg-yellow-500", text: "text-yellow-700" },
  baixo: { dot: "bg-green-500", text: "text-green-700" },
};

export default function MunicipalityList({
  municipalities,
  selectedId,
  onSelect,
}: MunicipalityListProps) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const term = search.toLowerCase().trim();
    const list = term
      ? municipalities.filter((m) => m.nome.toLowerCase().includes(term))
      : municipalities;
    return list.sort((a, b) => b.risk_index - a.risk_index);
  }, [municipalities, search]);

  if (municipalities.length === 0) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        Nenhum município encontrado
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="text-sm font-semibold text-gray-800">Municípios</h3>
        <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full text-xs">
          {municipalities.length}
        </span>
      </div>

      {/* Busca */}
      <div className="p-2 border-b">
        <input
          type="text"
          placeholder="Buscar município..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 && (
          <div className="p-4 text-center text-gray-400 text-sm">
            Nenhum resultado para &quot;{search}&quot;
          </div>
        )}
        {filtered.map((mun) => {
          const style =
            CLASSIFICATION_STYLES[mun.classification] ||
            CLASSIFICATION_STYLES.baixo;
          const isSelected = mun.municipio_id === selectedId;

          return (
            <button
              key={mun.municipio_id}
              onClick={() => onSelect(mun.municipio_id, mun.nome)}
              className={`w-full text-left px-3 py-2 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                isSelected ? "bg-blue-50" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${style.dot}`}
                />
                <span className="text-sm text-gray-800 truncate flex-1">
                  {mun.nome}
                </span>
                <span className={`text-xs font-medium ${style.text}`}>
                  {mun.risk_index}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
