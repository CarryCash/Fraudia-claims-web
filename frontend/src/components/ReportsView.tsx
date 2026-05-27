import { useEffect, useState } from 'react';
import { getReportStats, type ReportStats } from '../services/api';
import { PiggyBank, Target, BarChart2, MapPin, TriangleAlert, TrendingUp } from 'lucide-react';

export default function ReportsView() {
  const [stats, setStats] = useState<ReportStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReportStats()
      .then(setStats)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-6 bg-error-container text-error rounded-xl">
        <h3 className="font-bold">Error cargando reportes</h3>
        <p>{error}</p>
      </div>
    );
  }

  const riskPercentage = stats.monto_total > 0 ? (stats.ahorro_potencial / stats.monto_total) * 100 : 0;

  return (
    <div className="flex-1 space-y-6">
      <div className="mb-8">
        <h2 className="text-display font-display font-bold text-on-surface mb-2 flex items-center gap-3">
          <BarChart2 className="text-primary" size={32} />
          Centro de Reportes y Analítica
        </h2>
        <p className="text-body-lg text-on-surface-variant">Análisis de impacto de negocio basado en datos reales de reclamos.</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gradient-to-br from-error-container to-surface-container-lowest border border-error/20 rounded-2xl p-6 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <TriangleAlert size={120} />
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 text-error font-bold mb-4">
              <TriangleAlert size={20} />
              Ahorro Potencial (Capital en Riesgo)
            </div>
            <div className="text-[48px] font-display font-bold text-on-surface leading-none mb-2">
              {formatCurrency(stats.ahorro_potencial)}
            </div>
            <div className="text-body-lg text-on-surface-variant flex items-center gap-2">
              <span className="font-bold text-error">{riskPercentage.toFixed(1)}%</span> del total reclamado.
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-surface-container-low to-surface-container-lowest border border-outline-variant rounded-2xl p-6 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <PiggyBank size={120} />
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 text-on-surface-variant font-bold mb-4">
              <PiggyBank size={20} />
              Monto Total Reclamado
            </div>
            <div className="text-[48px] font-display font-bold text-on-surface leading-none mb-2">
              {formatCurrency(stats.monto_total)}
            </div>
            <div className="text-body-lg text-on-surface-variant">
              Suma total del dataset actual.
            </div>
          </div>
        </div>
      </div>

      {/* Heatmaps & Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
        
        {/* Concentración por Sucursal */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-sm overflow-hidden flex flex-col">
          <div className="p-5 border-b border-outline-variant flex items-center gap-3 bg-surface-container-low/50">
            <MapPin className="text-primary" size={20} />
            <h3 className="font-label-lg font-bold text-on-surface">Concentración de Fraude por Sucursal</h3>
          </div>
          <div className="p-6 flex-1">
            <div className="space-y-4">
              {stats.heatmap_data.length === 0 ? (
                <p className="text-on-surface-variant text-center py-8">No hay datos suficientes.</p>
              ) : (
                stats.heatmap_data.map((item, idx) => {
                  const maxVal = stats.heatmap_data[0].siniestros_rojos;
                  const widthPct = maxVal > 0 ? (item.siniestros_rojos / maxVal) * 100 : 0;
                  // Color interpolation based on risk
                  const isTop = idx === 0;
                  return (
                    <div key={item.sucursal} className="flex items-center gap-4">
                      <div className="w-32 text-right font-medium text-label-md text-on-surface truncate" title={item.sucursal}>
                        {item.sucursal}
                      </div>
                      <div className="flex-1 h-6 bg-surface-container-high rounded-full overflow-hidden flex">
                        <div 
                          className={`h-full flex items-center justify-end pr-2 text-[10px] font-bold text-white transition-all duration-1000 ${isTop ? 'bg-error' : 'bg-orange-400'}`}
                          style={{ width: `${widthPct}%` }}
                        >
                          {item.siniestros_rojos}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Concentración por Ramo */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-sm overflow-hidden flex flex-col">
          <div className="p-5 border-b border-outline-variant flex items-center gap-3 bg-surface-container-low/50">
            <TrendingUp className="text-primary" size={20} />
            <h3 className="font-label-lg font-bold text-on-surface">Riesgo por Ramo</h3>
          </div>
          <div className="p-6 flex-1">
            <div className="space-y-4">
              {stats.riesgo_por_ramo.length === 0 ? (
                <p className="text-on-surface-variant text-center py-8">No hay datos suficientes.</p>
              ) : (
                stats.riesgo_por_ramo.map((item, idx) => {
                  const maxVal = stats.riesgo_por_ramo[0].siniestros_rojos;
                  const widthPct = maxVal > 0 ? (item.siniestros_rojos / maxVal) * 100 : 0;
                  return (
                    <div key={item.ramo} className="flex items-center gap-4">
                      <div className="w-32 text-right font-medium text-label-md text-on-surface truncate" title={item.ramo}>
                        {item.ramo}
                      </div>
                      <div className="flex-1 h-6 bg-surface-container-high rounded-full overflow-hidden flex">
                        <div 
                          className={`h-full flex items-center justify-end pr-2 text-[10px] font-bold text-white transition-all duration-1000 ${idx === 0 ? 'bg-error' : 'bg-primary'}`}
                          style={{ width: `${widthPct}%` }}
                        >
                          {item.siniestros_rojos}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
