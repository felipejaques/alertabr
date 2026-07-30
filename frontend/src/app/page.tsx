import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-3xl text-center">
        {/* Logo/Title */}
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Alerta<span className="text-green-600">BR</span>
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Plataforma de Prevenção a Desastres Naturais
        </p>

        {/* Description */}
        <p className="text-gray-500 mb-12 max-w-xl mx-auto">
          Monitoramento em tempo real de riscos climáticos com mapas interativos,
          alertas automáticos e relatórios preditivos para todo o Brasil.
        </p>

        {/* Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/dashboard"
            className="block p-6 bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-blue-300 transition-all"
          >
            <div className="text-3xl mb-3">🗺️</div>
            <h2 className="text-lg font-semibold text-gray-800">Dashboard</h2>
            <p className="text-sm text-gray-500 mt-2">
              Mapa interativo com índices de risco por município
            </p>
          </Link>

          <Link
            href="/reports"
            className="block p-6 bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-blue-300 transition-all"
          >
            <div className="text-3xl mb-3">📊</div>
            <h2 className="text-lg font-semibold text-gray-800">Relatórios</h2>
            <p className="text-sm text-gray-500 mt-2">
              Gráficos históricos e análise de tendências
            </p>
          </Link>

          <Link
            href="/scenarios"
            className="block p-6 bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-blue-300 transition-all"
          >
            <div className="text-3xl mb-3">🌊</div>
            <h2 className="text-lg font-semibold text-gray-800">Cenários</h2>
            <p className="text-sm text-gray-500 mt-2">
              Simulações de impacto (El Niño, La Niña)
            </p>
          </Link>
        </div>

        {/* Status */}
        <div className="mt-12 flex items-center justify-center gap-2 text-sm text-gray-400">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          Sistema operacional — dados atualizados em tempo real
        </div>
      </div>
    </main>
  );
}
