import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, TriangleAlert, PiggyBank, Download, Filter, RefreshCw, Sparkles, CheckSquare, Settings2, Trash2, WifiOff } from 'lucide-react';
import { useClaims } from '../hooks/useClaims';
import type { Claim } from '../services/api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function colorLabel(color: Claim['final_color']) {
  if (color === 'rojo')
    return (
      <span className="inline-flex items-center gap-1 bg-error-container text-error px-2.5 py-1 rounded-full text-label-sm font-bold">
        <span className="material-symbols-outlined text-[14px]">error</span> Muy Alto
      </span>
    );
  if (color === 'amarillo')
    return (
      <span className="inline-flex items-center gap-1 bg-yellow-100 text-yellow-800 px-2.5 py-1 rounded-full text-label-sm font-bold">
        <span className="material-symbols-outlined text-[14px]">warning</span> Medio
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 bg-green-100 text-green-800 px-2.5 py-1 rounded-full text-label-sm font-bold">
      <span className="material-symbols-outlined text-[14px]">check_circle</span> Bajo
    </span>
  );
}

function formatCurrency(n: number | undefined): string {
  if (n === undefined || n === null) return '—';
  return new Intl.NumberFormat('es-EC', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

function formatDate(s: string | undefined): string {
  if (!s) return '—';
  try {
    return new Date(s).toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return s;
  }
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <tr className="animate-pulse border-b border-outline-variant/30">
      {[...Array(7)].map((_, i) => (
        <td key={i} className="p-4">
          <div className="h-4 bg-surface-container-high rounded w-3/4" />
        </td>
      ))}
    </tr>
  );
}

// ── Dashboard / Claims View ───────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate();

  // Load a larger set of claims to allow local filtering/sorting for the demo
  const { claims: allClaims, total, loading, error, refetch } = useClaims({ page: 1, limit: 100 });

  const [activeTab, setActiveTab] = useState<'all' | 'review' | 'docs'>('all');
  const [priorityMode, setPriorityMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // Red claims (for KPI card)
  const { total: totalRojo } = useClaims({ page: 1, limit: 1, color: 'rojo' });
  const { claims: redClaims } = useClaims({ page: 1, limit: 100, color: 'rojo' });
  const potentialSavings = redClaims.reduce((acc, c) => acc + (c.monto_reclamado ?? 0), 0);

  // 1. Filter claims
  const filteredClaims = useMemo(() => {
    let result = [...allClaims];
    
    if (activeTab === 'review') {
      // "En Revisión Manual": Riesgo Alto o Medio
      result = result.filter(c => c.final_color === 'rojo' || c.final_color === 'amarillo');
    } else if (activeTab === 'docs') {
      // "Pendiente Documentación": Si la API no lo trae directamente, podemos inferirlo
      // de `documentos_completos` === 'No' o si tiene documentos con entregado === 'No'
      result = result.filter(c => c.documentos_completos === 'No' || c.documentos_completos === 'Incompleto');
    }

    return result;
  }, [allClaims, activeTab]);

  // 2. Sort claims (Priority Mode)
  const sortedClaims = useMemo(() => {
    if (!priorityMode) return filteredClaims;
    
    // Prioridad IA: Rojos primero, ordenados por monto desc, luego amarillos
    return [...filteredClaims].sort((a, b) => {
      const rank = { 'rojo': 3, 'amarillo': 2, 'verde': 1 };
      const rankA = rank[a.final_color || 'verde'];
      const rankB = rank[b.final_color || 'verde'];
      
      if (rankA !== rankB) return rankB - rankA;
      
      // Secondary sort: monto reclamado
      return (b.monto_reclamado || 0) - (a.monto_reclamado || 0);
    });
  }, [filteredClaims, priorityMode]);

  // Reset pagination when filters change
  useMemo(() => {
    setCurrentPage(1);
  }, [activeTab, priorityMode]);

  // 3. Pagination
  const totalPages = Math.ceil(sortedClaims.length / itemsPerPage);
  const paginatedClaims = sortedClaims.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Mass actions
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedIds(new Set(sortedClaims.map(c => c.id_siniestro)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const handleExport = () => {
    if (selectedIds.size === 0) return;
    
    // Find the selected claims
    const toExport = allClaims.filter(c => selectedIds.has(c.id_siniestro));
    
    // Create CSV content
    const headers = ['ID', 'Beneficiario', 'Ramo', 'Fecha', 'Monto', 'Riesgo'];
    const rows = toExport.map(c => [
      c.id_siniestro,
      c.beneficiario || '',
      c.ramo || '',
      c.fecha_ocurrencia || '',
      c.monto_reclamado || 0,
      c.final_color || ''
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(r => r.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Trigger download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `exportacion_siniestros_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clear selection
    setSelectedIds(new Set());
  };

  const [isExportingNotion, setIsExportingNotion] = useState(false);
  const handleExportToNotion = async () => {
    setIsExportingNotion(true);
    
    try {
      const toExport = selectedIds.size > 0 
        ? allClaims.filter(c => selectedIds.has(c.id_siniestro))
        : sortedClaims.slice(0, 50); // Export top 50 if none selected
        
      if (toExport.length === 0) {
        alert('No hay siniestros para exportar.');
        return;
      }

      // import exportToNotion at the top if needed. Let's do a dynamic fetch so we don't break imports if api.ts isn't fully updated yet, but we already added it.
      const { exportToNotion } = await import('../services/api');
      const res = await exportToNotion(toExport);
      if (res.success) {
        alert('Exportado a Notion con éxito! \nRevisa tu página de Notion.');
        if (res.url) window.open(res.url, '_blank');
      } else {
        alert('Error al exportar a Notion');
      }
    } catch (err: any) {
      alert('Error: ' + err.message);
    } finally {
      setIsExportingNotion(false);
      setSelectedIds(new Set());
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-display font-display font-bold text-on-surface mb-2">Gestión de Siniestros</h2>
          <p className="text-body-lg text-on-surface-variant">Centro de triaje y priorización de reclamos.</p>
        </div>
        <button
          onClick={refetch}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-outline-variant text-on-surface-variant hover:bg-surface-container-low transition-colors text-label-md bg-surface-container-lowest"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Sincronizar
        </button>
      </div>

      {error && (
        <div className="bg-error-container text-error rounded-xl p-4 mb-6 flex items-center gap-3">
          <WifiOff size={20} />
          <div>
            <h4 className="font-bold text-label-lg">Error de conexión</h4>
            <p className="text-body-sm">No se pudo cargar la base de siniestros. {error}</p>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-6">
        {/* Total Claims */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:bg-surface-container-low transition-colors duration-200">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-label-sm text-on-surface-variant uppercase font-bold tracking-wider w-20">TOTAL RECLAMOS</h3>
            <FileText className="text-on-surface-variant" size={20} />
          </div>
          <div className="text-display font-display font-bold text-on-surface mb-2">{total}</div>
          <div className="text-label-md text-on-surface-variant">Últimos 30 días</div>
        </div>

        {/* High Risk */}
        <div className="bg-error-container border border-error/20 rounded-xl p-5 hover:bg-error-container/80 transition-colors duration-200">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-label-sm text-error uppercase font-bold tracking-wider w-20">ALTO RIESGO</h3>
            <TriangleAlert className="text-error" size={20} />
          </div>
          <div className="text-display font-display font-bold text-error mb-2">{totalRojo}</div>
          <div className="text-label-md text-error/80">Requieren revisión urgente</div>
        </div>

        {/* Potential Savings */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:bg-surface-container-low transition-colors duration-200">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-label-sm text-on-surface-variant uppercase font-bold tracking-wider w-20">MONTO EN RIESGO</h3>
            <PiggyBank className="text-on-surface-variant" size={20} />
          </div>
          <div className="text-display font-display font-bold text-on-surface mb-2">
            {formatCurrency(potentialSavings)}
          </div>
          <div className="text-label-md text-on-surface-variant">En siniestros rojos activos</div>
        </div>

        {/* Precisión IA */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:bg-surface-container-low transition-colors duration-200">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-label-sm text-on-surface-variant uppercase font-bold tracking-wider w-20">PRECISIÓN IA</h3>
            <span className="material-symbols-outlined text-on-surface-variant">psychiatry</span>
          </div>
          <div className="text-display font-display font-bold text-on-surface mb-2">94.8%</div>
          <div className="text-label-md font-bold text-green-600 flex items-center gap-1">
            <span className="material-symbols-outlined text-[16px]">check_circle</span>
            Modelo v4.2 Activo
          </div>
        </div>
      </div>

      {/* Main Board */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl flex flex-col flex-1 overflow-hidden shadow-sm">
        
        {/* Toolbar */}
        <div className="p-4 border-b border-outline-variant flex flex-col md:flex-row justify-between items-center gap-4 bg-surface-container-lowest">
          
          {/* Tabs */}
          <div className="flex gap-2 bg-surface-container-low p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-4 py-1.5 rounded-md text-label-md font-bold transition-colors ${
                activeTab === 'all' ? 'bg-surface-container-lowest text-on-surface shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Todos
            </button>
            <button
              onClick={() => setActiveTab('review')}
              className={`px-4 py-1.5 rounded-md text-label-md font-bold transition-colors flex items-center gap-2 ${
                activeTab === 'review' ? 'bg-surface-container-lowest text-on-surface shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              En Revisión Manual
            </button>
            <button
              onClick={() => setActiveTab('docs')}
              className={`px-4 py-1.5 rounded-md text-label-md font-bold transition-colors flex items-center gap-2 ${
                activeTab === 'docs' ? 'bg-surface-container-lowest text-on-surface shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Pendiente Docs
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setPriorityMode(!priorityMode)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-label-md font-bold transition-all border ${
                priorityMode 
                  ? 'bg-primary/10 border-primary text-primary shadow-sm' 
                  : 'bg-surface-container-lowest border-outline-variant text-on-surface-variant hover:bg-surface-container-low'
              }`}
            >
              <Sparkles size={18} className={priorityMode ? 'text-primary' : 'text-on-surface-variant'} />
              Cola Prioridad IA
            </button>
            
            <div className="w-px h-6 bg-outline-variant/50 mx-1"></div>

            <button 
              className={`px-4 py-2 rounded-lg font-label-md font-bold text-label-sm flex items-center gap-2 transition-colors shadow-sm ${
                isExportingNotion 
                  ? 'bg-surface-container-high text-on-surface-variant cursor-not-allowed' 
                  : 'bg-surface border border-outline-variant text-primary hover:bg-surface-container-high'
              }`}
              onClick={handleExportToNotion}
              disabled={isExportingNotion}
            >
              {isExportingNotion ? (
                <RefreshCw size={16} className="animate-spin" />
              ) : (
                <span className="font-serif font-bold text-[16px] leading-none text-black">N</span>
              )}
              {isExportingNotion ? 'Enviando...' : 'Exportar a Notion'}
            </button>

            <button className="p-2 text-on-surface-variant hover:bg-surface-container-high rounded transition-colors" title="Filtros avanzados">
              <Settings2 size={20} />
            </button>
          </div>
        </div>

        {/* Mass Actions Banner (Visible when items selected) */}
        {selectedIds.size > 0 && (
          <div className="bg-primary text-on-primary px-6 py-3 flex items-center justify-between animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center gap-3 font-label-md">
              <CheckSquare size={18} />
              <span>{selectedIds.size} siniestro{selectedIds.size !== 1 ? 's' : ''} seleccionado{selectedIds.size !== 1 ? 's' : ''}</span>
            </div>
            <div className="flex items-center gap-3">
              <button 
                className="px-4 py-1.5 bg-on-primary text-primary rounded-lg font-bold text-label-sm flex items-center gap-2 hover:bg-on-primary/90 transition-colors shadow-sm"
                onClick={handleExport}
              >
                <Download size={16} />
                Exportar CSV
              </button>
              <button 
                className="px-4 py-1.5 border border-on-primary/30 text-on-primary rounded-lg font-bold text-label-sm hover:bg-on-primary/10 transition-colors"
                onClick={() => setSelectedIds(new Set())}
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {/* Table */}
        <div className="overflow-x-auto flex-1 relative">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead className="sticky top-0 bg-surface-container-lowest border-b border-outline-variant z-10">
              <tr className="text-label-sm text-on-surface-variant uppercase tracking-wider">
                <th className="p-4 w-12 text-center">
                  <input 
                    type="checkbox" 
                    className="w-4 h-4 rounded border-outline-variant text-primary focus:ring-primary"
                    checked={paginatedClaims.length > 0 && selectedIds.size >= paginatedClaims.length}
                    onChange={handleSelectAll}
                  />
                </th>
                <th className="p-4 font-bold">ID</th>
                <th className="p-4 font-bold">Beneficiario</th>
                <th className="p-4 font-bold">Ramo</th>
                <th className="p-4 font-bold">Fecha</th>
                <th className="p-4 font-bold">Importe</th>
                <th className="p-4 font-bold">Estado / Riesgo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30">
              {loading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : paginatedClaims.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-16 text-center text-on-surface-variant">
                    <div className="flex flex-col items-center gap-3">
                      <TriangleAlert size={40} className="opacity-40" />
                      <div>
                        <p className="font-bold text-title-md text-on-surface">No hay resultados</p>
                        <p className="text-body-md mt-1">Prueba cambiando la vista de estado o quitando filtros.</p>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedClaims.map((claim) => {
                  const isSelected = selectedIds.has(claim.id_siniestro);
                  return (
                    <tr
                      key={claim.id_siniestro}
                      className={`transition-colors ${isSelected ? 'bg-primary/5' : 'hover:bg-surface-container-low'}`}
                    >
                      <td className="p-4 text-center">
                        <input 
                          type="checkbox" 
                          className="w-4 h-4 rounded border-outline-variant text-primary focus:ring-primary"
                          checked={isSelected}
                          onChange={() => handleSelectOne(claim.id_siniestro)}
                        />
                      </td>
                      <td 
                        className="p-4 text-body-md text-primary font-mono font-medium cursor-pointer"
                        onClick={() => navigate(`/analyzer?id=${claim.id_siniestro}`)}
                      >
                        #{claim.id_siniestro}
                      </td>
                      <td className="p-4 text-body-md text-on-surface">{claim.beneficiario ?? '—'}</td>
                      <td className="p-4 text-body-md text-on-surface-variant">
                        <span className="font-bold">{claim.ramo}</span><br/>
                        <span className="text-[11px] opacity-80">{claim.cobertura}</span>
                      </td>
                      <td className="p-4 text-body-md text-on-surface-variant">{formatDate(claim.fecha_ocurrencia)}</td>
                      <td className="p-4 text-body-md font-bold text-on-surface">
                        {formatCurrency(claim.monto_reclamado)}
                      </td>
                      <td className="p-4">
                        <div className="flex flex-col gap-1 items-start">
                          {colorLabel(claim.final_color)}
                          {(claim.documentos_completos === 'No' || claim.documentos_completos === 'Incompleto') && (
                            <span className="text-[10px] bg-error-container text-error px-1.5 py-0.5 rounded font-bold uppercase tracking-wide">
                              Faltan Docs
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Footer / Pagination */}
        <div className="p-4 border-t border-outline-variant bg-surface-container-lowest text-label-sm text-on-surface-variant flex justify-between items-center">
          <div>
            Mostrando <span className="font-bold text-on-surface">{(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, sortedClaims.length)}</span> de <span className="font-bold text-on-surface">{sortedClaims.length}</span> siniestros
          </div>
          <div className="flex items-center gap-4">
            {priorityMode && (
              <div className="flex items-center gap-1.5 text-primary bg-primary/5 px-2 py-1 rounded">
                <Sparkles size={14} /> Orden IA
              </div>
            )}
            <div className="flex gap-2">
              <button 
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 border border-outline-variant rounded-md hover:bg-surface-container-low disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Anterior
              </button>
              <button 
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages || totalPages === 0}
                className="px-3 py-1.5 border border-outline-variant rounded-md hover:bg-surface-container-low disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Siguiente
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
