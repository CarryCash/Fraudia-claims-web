import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getProviderRisk, type ProviderRisk } from '../services/api';
import { Users, AlertTriangle, Building2, Stethoscope, Search, ShieldAlert, ArrowRight, Eye, Bookmark } from 'lucide-react';

export default function EntitiesView() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [providers, setProviders] = useState<ProviderRisk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [watchedProviders, setWatchedProviders] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 9;

  useEffect(() => {
    const q = (params.get('q') || '').trim();
    if (q && searchTerm !== q) {
      queueMicrotask(() => setSearchTerm(q));
    }
  }, [params, searchTerm]);

  useEffect(() => {
    try {
      const stored = globalThis.localStorage.getItem('entities-watchlist');
      if (stored && watchedProviders.length === 0) {
        queueMicrotask(() => setWatchedProviders(JSON.parse(stored)));
      }
    } catch {
      // Ignore parse errors
    }
  }, [watchedProviders.length]);

  useEffect(() => {
    getProviderRisk()
      .then(setProviders)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    globalThis.localStorage.setItem('entities-watchlist', JSON.stringify(watchedProviders));
  }, [watchedProviders]);

  const getIcon = (tipo: string) => {
    if (tipo.toLowerCase().includes('taller')) return <Building2 size={20} />;
    if (tipo.toLowerCase().includes('médico') || tipo.toLowerCase().includes('clinica') || tipo.toLowerCase().includes('clínica')) return <Stethoscope size={20} />;
    return <Users size={20} />;
  };

  const getRiskClasses = (tasa: number) => {
    const isHighRisk = tasa >= 50;
    const isMediumRisk = tasa >= 20 && tasa < 50;
    
    let indicatorClass: string;
    let iconBgClass: string;
    let textColorClass: string;

    if (isHighRisk) {
      indicatorClass = 'bg-error';
      iconBgClass = 'bg-error-container text-error';
      textColorClass = 'text-error';
    } else if (isMediumRisk) {
      indicatorClass = 'bg-orange-400';
      iconBgClass = 'bg-orange-100 text-orange-700';
      textColorClass = 'text-orange-600';
    } else {
      indicatorClass = 'bg-green-500';
      iconBgClass = 'bg-surface-container-high text-on-surface-variant';
      textColorClass = 'text-green-600';
    }
    
    return {
      isHighRisk,
      isMediumRisk,
      indicatorClass,
      iconBgClass,
      textColorClass,
    };
  };

  const filteredProviders = providers.filter(p => 
    p.nombre.toLowerCase().includes(searchTerm.toLowerCase()) || 
    p.id_proveedor.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalPages = Math.max(1, Math.ceil(filteredProviders.length / itemsPerPage));

  useEffect(() => {
    if (searchTerm && currentPage !== 1) {
      queueMicrotask(() => setCurrentPage(1));
    }
  }, [searchTerm, currentPage]);

  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      queueMicrotask(() => setCurrentPage(totalPages));
    }
  }, [currentPage, totalPages]);

  const currentProviders = filteredProviders.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage,
  );

  const watchedProviderList = providers.filter((p) => watchedProviders.includes(p.id_proveedor));
  const toggleWatch = (id: string) => {
    setWatchedProviders((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-error-container text-error rounded-xl">
        <h3 className="font-bold">Error cargando entidades</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6">
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-display font-display font-bold text-on-surface mb-2 flex items-center gap-3">
            <Users className="text-primary" size={32} />
            Directorio de Entidades
          </h2>
          <p className="text-body-lg text-on-surface-variant">Perfiles de riesgo de proveedores basados en su histórico de reclamos.</p>
          {watchedProviderList.length > 0 && (
            <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-surface-container-low border border-outline-variant px-4 py-2 text-sm text-on-surface-variant">
              <Bookmark size={16} />
              Vigilando {watchedProviderList.length} proveedor{watchedProviderList.length === 1 ? '' : 'es'}
            </div>
          )}
        </div>
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" size={20} />
          <input
            type="text"
            placeholder="Buscar por nombre o ID..."
            className="w-full pl-10 pr-4 py-2 bg-surface-container-lowest border border-outline-variant rounded-lg outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-on-surface"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {currentProviders.map(provider => {
          const riskClasses = getRiskClasses(provider.tasa_siniestralidad);
          const networkFocusId = `provider_${provider.id_proveedor}`;
          
          return (
            <div key={provider.id_proveedor} className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 shadow-sm flex flex-col transition-all hover:shadow-md relative overflow-hidden group">
              {/* Risk Indicator Line */}
              <div className={`absolute top-0 left-0 w-full h-1 ${riskClasses.indicatorClass}`} />

              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${riskClasses.iconBgClass}`}>
                    {getIcon(provider.tipo)}
                  </div>
                  <div>
                    <h3 className="font-label-lg font-bold text-on-surface leading-tight" title={provider.nombre}>
                      {provider.nombre.length > 25 ? provider.nombre.substring(0, 25) + '...' : provider.nombre}
                    </h3>
                    <p className="text-label-sm text-on-surface-variant flex items-center gap-1 mt-1">
                      {provider.tipo} <span className="opacity-50">•</span> {provider.id_proveedor}
                    </p>
                  </div>
                </div>
                {riskClasses.isHighRisk && (
                  <div className="bg-error text-on-error px-2.5 py-1 rounded-full text-[10px] font-bold flex items-center gap-1 shrink-0 shadow-sm animate-pulse">
                    <ShieldAlert size={12} /> ALTO RIESGO
                  </div>
                )}
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-surface-container-low rounded-xl p-3 border border-outline-variant/50">
                  <p className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Tasa de Riesgo</p>
                  <p className={`text-[24px] font-bold leading-none ${riskClasses.textColorClass}`}>
                    {provider.tasa_siniestralidad}%
                  </p>
                </div>
                <div className="bg-surface-container-low rounded-xl p-3 border border-outline-variant/50">
                  <p className="text-[10px] uppercase font-bold text-on-surface-variant tracking-wider mb-1">Alertas (Rojo)</p>
                  <p className="text-[24px] font-bold leading-none text-on-surface">
                    {provider.siniestros_rojos} <span className="text-body-sm text-on-surface-variant font-normal">de {provider.total_siniestros}</span>
                  </p>
                </div>
              </div>

              {/* Connections */}
              <div className="flex-1 flex flex-col justify-end">
                <div className="text-label-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2 flex items-center gap-1">
                  Asegurados Vinculados ({provider.asegurados_vinculados.length})
                </div>
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {provider.asegurados_vinculados.slice(0, 3).map(client => (
                    <span key={client.id} className="inline-flex items-center px-2 py-1 bg-surface-container-high rounded text-[11px] font-medium text-on-surface-variant border border-outline-variant/30">
                      {client.name.split(' ')[0]} {/* Show just first name/word to save space */}
                    </span>
                  ))}
                  {provider.asegurados_vinculados.length > 3 && (
                    <span className="inline-flex items-center px-2 py-1 bg-surface-container-high rounded text-[11px] font-medium text-on-surface-variant border border-outline-variant/30">
                      +{provider.asegurados_vinculados.length - 3} más
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-1 gap-3">
                  <button
                    className="w-full py-2.5 bg-surface border border-outline-variant rounded-lg font-label-md font-bold text-on-surface hover:bg-surface-container-low transition-colors flex items-center justify-center gap-2"
                    onClick={() => navigate(`/analyzer?provider=${encodeURIComponent(provider.id_proveedor)}`)}
                    title="Ver siniestros asociados a este proveedor"
                  >
                    <Eye size={16} />
                    Ver siniestros asociados
                  </button>
                  <button
                    className={`w-full py-2.5 rounded-lg font-label-md font-bold transition-all flex items-center justify-center gap-2 ${watchedProviders.includes(provider.id_proveedor) ? 'bg-primary text-on-primary' : 'bg-surface border border-outline-variant text-on-surface hover:bg-surface-container-low'}`}
                    onClick={() => toggleWatch(provider.id_proveedor)}
                    title={watchedProviders.includes(provider.id_proveedor) ? 'Quitar de vigilancia' : 'Agregar a vigilancia'}
                  >
                    <Bookmark size={16} />
                    {watchedProviders.includes(provider.id_proveedor) ? 'Quitar de vigilancia' : 'Agregar a vigilancia'}
                  </button>
                  <button
                    className="w-full py-2.5 bg-surface border border-outline-variant rounded-lg font-label-md font-bold text-on-surface hover:bg-surface-container-low transition-colors flex items-center justify-center gap-2"
                    onClick={() => navigate(`/network?focus=${encodeURIComponent(networkFocusId)}`)}
                    title="Ir a este nodo en la Red"
                  >
                    Ver en Red de Relaciones
                    <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      
      {filteredProviders.length === 0 && !loading && (
        <div className="text-center py-20 bg-surface-container-lowest border border-outline-variant rounded-2xl border-dashed">
          <AlertTriangle className="mx-auto text-on-surface-variant opacity-50 mb-3" size={48} />
          <h3 className="font-bold text-on-surface text-title-md">No se encontraron entidades</h3>
          <p className="text-on-surface-variant mt-1">Prueba con otro término de búsqueda.</p>
        </div>
      )}

      {filteredProviders.length > 0 && (
        <div className="p-4 border-t border-outline-variant bg-surface-container-lowest text-label-sm text-on-surface-variant flex flex-col md:flex-row items-center justify-between gap-3">
          <div>
            Mostrando <span className="font-bold text-on-surface">{(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, filteredProviders.length)}</span> de <span className="font-bold text-on-surface">{filteredProviders.length}</span> entidades
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1.5 border border-outline-variant rounded-md hover:bg-surface-container-low disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Anterior
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages || totalPages === 0}
              className="px-3 py-1.5 border border-outline-variant rounded-md hover:bg-surface-container-low disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
