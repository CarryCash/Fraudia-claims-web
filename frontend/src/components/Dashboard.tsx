import { useState, useMemo, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FileText, TriangleAlert, PiggyBank, Download, RefreshCw, Sparkles, CheckSquare, Settings2, WifiOff } from 'lucide-react';
import { useClaims } from '../hooks/useClaims';
import { createManualClaimComplete, validateDocumentWithAI, type Claim } from '../services/api';

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

function norm(s: unknown): string {
  if (typeof s === 'string') return s.trim().toLowerCase();
  return '';
}

function computeLiveScore(
  manual: { cobertura: string; descripcion: string; beneficiario: string; fecha_ocurrencia: string; fecha_reporte: string; monto_reclamado: string; documentos_completos: string },
  docs: { inconsistencia_detectada: string }[],
  listaRestrictiva: string[]
): { score: number; color: 'verde' | 'amarillo' | 'rojo'; flags: { label: string; severity: 'red' | 'yellow' | 'gray' }[] } {
  let score = 0;
  const flags: { label: string; severity: 'red' | 'yellow' | 'gray' }[] = [];

  const cob = manual.cobertura.toLowerCase();
  const desc = manual.descripcion.toLowerCase();
  const ben = manual.beneficiario.toLowerCase();

  // RF03: Proveedor en lista restrictiva → +30 pts (rojo)
  if (listaRestrictiva.some((bad) => bad && ben.includes(bad))) {
    score += 30;
    flags.push({ label: 'RF03: Proveedor en lista restrictiva', severity: 'red' });
  }

  // RF01: Cobertura Robo + Pérdida Total → +25 pts (rojo)
  const isRobo = cob.includes('robo');
  if (isRobo) {
    score += 10;
    flags.push({ label: 'Cobertura de Robo', severity: 'yellow' });
    if (desc.includes('robo total') || desc.includes('pérdida total') || desc.includes('perdida total')) {
      score += 20;
      flags.push({ label: 'RF01: Pérdida Total por Robo', severity: 'red' });
    }
  }

  // Days between occurrence and report
  if (manual.fecha_ocurrencia && manual.fecha_reporte) {
    const fo = new Date(manual.fecha_ocurrencia).getTime();
    const fr = new Date(manual.fecha_reporte).getTime();
    if (!isNaN(fo) && !isNaN(fr) && fr >= fo) {
      const days = Math.floor((fr - fo) / 86400000);
      if (isRobo && days > 4) {
        score += 15;
        flags.push({ label: `RF06: Demora atípica en reporte de robo (${days}d)`, severity: 'red' });
      } else if (days > 7) {
        score += 10;
        flags.push({ label: `Reporte muy tardío: ${days} días`, severity: 'yellow' });
      } else if (days > 3) {
        score += 5;
        flags.push({ label: `Reporte tardío: ${days} días`, severity: 'gray' });
      }
    }
  }

  // Documentos incompletos
  if (manual.documentos_completos === 'No') {
    score += 10;
    flags.push({ label: 'Documentación incompleta', severity: 'yellow' });
  } else if (manual.documentos_completos === 'Incompleto') {
    score += 6;
    flags.push({ label: 'Documentación parcial', severity: 'gray' });
  }

  // Inconsistencias en documentos adjuntos
  const nInc = docs.filter((d) => d.inconsistencia_detectada === 'Sí').length;
  if (nInc > 0) {
    score += nInc * 10;
    flags.push({ label: `${nInc} doc${nInc > 1 ? 's' : ''} con inconsistencia detectada`, severity: 'red' });
  }

  // Descripción con narrativa sospechosa
  const suspKeys = ['inconsistente', 'imposible', 'ilógico', 'ilogico', 'falso', 'alterado', 'sospechoso', 'no recuerda', 'no hay testigos'];
  const hitKeys = suspKeys.filter((k) => desc.includes(k));
  if (hitKeys.length > 0) {
    score += Math.min(hitKeys.length * 5, 15);
    flags.push({ label: 'Narrativa con términos sospechosos', severity: 'yellow' });
  }

  // Monto elevado
  const monto = parseFloat(manual.monto_reclamado) || 0;
  if (monto > 20000) {
    score += 8;
    flags.push({ label: `Monto muy elevado: $${monto.toLocaleString('es-EC')}`, severity: 'yellow' });
  } else if (monto > 8000) {
    score += 4;
    flags.push({ label: `Monto considerable: $${monto.toLocaleString('es-EC')}`, severity: 'gray' });
  }

  score = Math.min(score, 100);
  const color: 'verde' | 'amarillo' | 'rojo' = score >= 75 ? 'rojo' : score >= 35 ? 'amarillo' : 'verde';
  return { score, color, flags };
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonRow({ id }: { readonly id: string }) {
  return (
    <tr className="animate-pulse border-b border-outline-variant/30">
      {[...new Array(7)].map((_, i) => (
        <td key={`${id}-${i}`} className="p-4">
          <div className="h-4 bg-surface-container-high rounded w-3/4" />
        </td>
      ))}
    </tr>
  );
}

// ── Dashboard / Claims View ───────────────────────────────────────────────────
// ── Live Score Panel UI ──────────────────────────────────────────────────────
function LiveScorePanel({ score, color, flags }: ReturnType<typeof computeLiveScore>) {
  const pct = score;
  const colorMap = {
    verde:   { ring: '#22c55e', bg: 'bg-green-50',  text: 'text-green-700',  badge: 'bg-green-100 text-green-800',   label: 'Riesgo Bajo',    icon: 'check_circle' },
    amarillo: { ring: '#f59e0b', bg: 'bg-yellow-50', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-800', label: 'Riesgo Medio',   icon: 'warning' },
    rojo:    { ring: '#ef4444', bg: 'bg-red-50',    text: 'text-red-700',    badge: 'bg-red-100 text-red-800',       label: 'Riesgo Muy Alto', icon: 'error' },
  }[color];

  // SVG arc gauge params
  const R = 40;
  const CIRCUMFERENCE = 2 * Math.PI * R;
  const dash = (pct / 100) * CIRCUMFERENCE;

  return (
    <div className={`md:col-span-2 rounded-xl border ${color === 'rojo' ? 'border-red-200' : color === 'amarillo' ? 'border-yellow-200' : 'border-green-200'} ${colorMap.bg} p-4 transition-all duration-500`}>
      <div className="flex items-center gap-5">
        {/* Gauge SVG */}
        <div className="relative shrink-0 w-[96px] h-[96px] flex items-center justify-center">
          <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
            <circle cx="48" cy="48" r={R} fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <circle
              cx="48" cy="48" r={R} fill="none"
              stroke={colorMap.ring}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${dash} ${CIRCUMFERENCE}`}
              style={{ transition: 'stroke-dasharray 0.5s ease, stroke 0.5s ease' }}
            />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className={`text-2xl font-black leading-none ${colorMap.text}`} style={{ transition: 'color 0.4s' }}>{score}</span>
            <span className="text-[9px] font-bold text-on-surface-variant uppercase tracking-wider">/ 100</span>
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`material-symbols-outlined text-[18px] ${colorMap.text}`} style={{ fontVariationSettings: "'FILL' 1" }}>{colorMap.icon}</span>
            <span className={`text-label-lg font-black ${colorMap.text}`}>{colorMap.label}</span>
            <span className="text-label-sm text-on-surface-variant ml-auto">Score en vivo</span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 bg-white/60 rounded-full overflow-hidden mb-3 border border-black/5">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${pct}%`, background: colorMap.ring }}
            />
          </div>

          {/* Active flags */}
          {flags.length === 0 ? (
            <p className="text-label-sm text-on-surface-variant">Sin alertas activas — completa más campos para evaluar.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {flags.map((f) => (
                <span
                  key={f.label}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold ${
                    f.severity === 'red'    ? 'bg-red-100 text-red-700' :
                    f.severity === 'yellow' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-surface-container text-on-surface-variant'
                  }`}
                >
                  {f.severity === 'red' && <span className="material-symbols-outlined text-[11px]" style={{ fontVariationSettings: "'FILL' 1" }}>error</span>}
                  {f.severity === 'yellow' && <span className="material-symbols-outlined text-[11px]" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span>}
                  {f.label}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Dashboard / Claims View ───────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = (params.get('q') || '').trim();

  // Load full dataset (1000 siniestros) for consistent analysis across the app
  const { claims: allClaims, total, loading, error, refetch, addClaim } = useClaims({ page: 1, limit: 1000 });

  const [activeTab, setActiveTab] = useState<'all' | 'review' | 'docs'>('all');
  const [priorityMode, setPriorityMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filterColors, setFilterColors] = useState<{ rojo: boolean; amarillo: boolean; verde: boolean }>({
    rojo: true,
    amarillo: true,
    verde: true,
  });
  const [filterSucursal, setFilterSucursal] = useState<string>('Todas');
  const [filterRamo, setFilterRamo] = useState<string>('Todos');
  const [filterMissingDocs, setFilterMissingDocs] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualSaving, setManualSaving] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);
  const [manual, setManual] = useState({
    id_siniestro: '',
    id_poliza: '',
    id_asegurado: '',
    ramo: '',
    cobertura: '',
    fecha_ocurrencia: '',
    fecha_reporte: '',
    monto_reclamado: '',
    sucursal: '',
    descripcion: '',
    beneficiario: '',
    documentos_completos: 'Sí',
    id_proveedor: '',
    placa_vehiculo: '',
  });

  type ManualDocEntry = {
    tipo_documento: string;
    file: File;
    inconsistencia_detectada: string;
    observacion: string;
  };

  const [manualDocs, setManualDocs] = useState<ManualDocEntry[]>([]);
  const docFileInputRef = useRef<HTMLInputElement>(null);
  const [pendingDocPick, setPendingDocPick] = useState<{ tipo_documento: string } | null>(null);

  const DOC_TYPE_OPTIONS = [
    'Póliza',
    'Factura de Taller/Clínica',
    'Informe Policial',
    'Denuncia Fiscalía',
    'Cédula / Identificación',
    'Fotos del siniestro',
    'Otro',
  ];

  const resetManualForm = () => {
    setManual({
      id_siniestro: '',
      id_poliza: '',
      id_asegurado: '',
      ramo: '',
      cobertura: '',
      fecha_ocurrencia: '',
      fecha_reporte: '',
      monto_reclamado: '',
      sucursal: '',
      descripcion: '',
      beneficiario: '',
      documentos_completos: 'Sí',
      id_proveedor: '',
      placa_vehiculo: '',
    });
    setManualDocs([]);
    setPendingDocPick(null);
  };

  const requestDocFile = (tipo_documento: string) => {
    setPendingDocPick({ tipo_documento });
    docFileInputRef.current?.click();
  };

  const handleDocFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !pendingDocPick) return;

    setManualDocs((prev) => [
      ...prev,
      {
        tipo_documento: pendingDocPick.tipo_documento,
        file,
        inconsistencia_detectada: 'No',
        observacion: '',
      },
    ]);
    setPendingDocPick(null);
  };

  const removeManualDoc = (idx: number) => {
    setManualDocs((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateManualDoc = (idx: number, field: keyof ManualDocEntry, value: string) => {
    setManualDocs((prev) => prev.map((d, i) => (i === idx ? { ...d, [field]: value } : d)));
  };

  // ── Live Score ────────────────────────────────────────────────────────────
  const listaRestrictiva = useMemo(() => {
    return Array.from(new Set(
      allClaims
        .filter(c => c.proveedor_lista_restrictiva === 1 || c.proveedor_lista_restrictiva === true || c.proveedor_lista_restrictiva === '1' || c.proveedor_lista_restrictiva === 'Sí')
        .map(c => c.beneficiario?.toLowerCase().trim())
        .filter(Boolean)
    )) as string[];
  }, [allClaims]);

  const liveScore = useMemo(
    () => computeLiveScore(manual, manualDocs, listaRestrictiva),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [manual.cobertura, manual.descripcion, manual.beneficiario, manual.fecha_ocurrencia, manual.fecha_reporte, manual.monto_reclamado, manual.documentos_completos, manualDocs, listaRestrictiva]
  );

  const redClaims = useMemo(
    () => allClaims.filter((c) => c.final_color === 'rojo'),
    [allClaims],
  );
  const totalRojo = redClaims.length;
  const potentialSavings = redClaims.reduce((acc, c) => acc + (c.monto_reclamado ?? 0), 0);
  const missingDocsCount = allClaims.filter((c) => c.documentos_completos === 'No' || c.documentos_completos === 'Incompleto').length;

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

    // Advanced filters (Settings)
    result = result.filter((c) => {
      const color = c.final_color || 'verde';
      if (color === 'rojo' && !filterColors.rojo) return false;
      if (color === 'amarillo' && !filterColors.amarillo) return false;
      if (color === 'verde' && !filterColors.verde) return false;

      if (filterSucursal !== 'Todas' && norm(c.sucursal) !== norm(filterSucursal)) return false;
      if (filterRamo !== 'Todos' && norm(c.ramo) !== norm(filterRamo)) return false;

      if (filterMissingDocs) {
        const miss = c.documentos_completos === 'No' || c.documentos_completos === 'Incompleto';
        if (!miss) return false;
      }
      return true;
    });

    // Global query filter (TopBar search)
    if (q) {
      const needle = q.toLowerCase();
      result = result.filter((c) => {
        const id = String(c.id_siniestro ?? '');
        const pol = String(c.id_poliza ?? '');
        const aseg = String(c.id_asegurado ?? '');
        const blob = [
          id,
          pol,
          aseg,
          c.beneficiario ?? '',
          c.ramo ?? '',
          c.cobertura ?? '',
          c.sucursal ?? '',
          c.descripcion ?? '',
        ]
          .join(' ')
          .toLowerCase();
        return id.includes(needle) || pol.toLowerCase().includes(needle) || blob.includes(needle);
      });
    }

    return result;
  }, [
    allClaims,
    activeTab,
    filterColors.rojo,
    filterColors.amarillo,
    filterColors.verde,
    filterSucursal,
    filterRamo,
    filterMissingDocs,
    q,
  ]);

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

  // Reset pagination when tab or priority mode changes
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, priorityMode, filterColors.rojo, filterColors.amarillo, filterColors.verde, filterSucursal, filterRamo, filterMissingDocs, q]);

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
    link.remove();
    
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
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      alert('Error: ' + message);
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
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setManualError(null);
              setManualOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-on-primary hover:opacity-90 transition-opacity text-label-md font-bold"
          >
            + Nuevo siniestro
          </button>
          <button
            onClick={refetch}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-outline-variant text-on-surface-variant hover:bg-surface-container-low transition-colors text-label-md bg-surface-container-lowest"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Sincronizar
          </button>
        </div>
      </div>

      {/* Manual claim modal */}
      {manualOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 bg-black/30 z-40 cursor-default"
            onClick={() => { setManualOpen(false); resetManualForm(); }}
            aria-label="Close modal"
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-8">
            <div className="w-full max-w-3xl max-h-[90vh] bg-surface border border-outline-variant rounded-2xl shadow-2xl overflow-y-auto">
              <div className="p-5 border-b border-outline-variant flex items-center justify-between">
                <div>
                  <h3 className="text-headline-sm font-bold text-on-surface">Cargar siniestro manual</h3>
                  <p className="text-label-sm text-on-surface-variant">Se guardará en la base relacional para auditoría.</p>
                </div>
                <button
                  className="px-3 py-2 rounded-lg hover:bg-surface-container-low text-on-surface-variant font-bold"
                  onClick={() => { setManualOpen(false); resetManualForm(); }}
                >
                  Cerrar
                </button>
              </div>

              <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* ── Live Score Panel ── */}
                <LiveScorePanel score={liveScore.score} color={liveScore.color} flags={liveScore.flags} />
                <Field label="ID Siniestro" value={manual.id_siniestro} onChange={(v) => setManual((p) => ({ ...p, id_siniestro: v }))} placeholder="1001" />
                <Field label="ID Póliza" value={manual.id_poliza} onChange={(v) => setManual((p) => ({ ...p, id_poliza: v }))} placeholder="POL-XXXXXX" />
                <Field label="ID Asegurado" value={manual.id_asegurado} onChange={(v) => setManual((p) => ({ ...p, id_asegurado: v }))} placeholder="ASEG-XXXXXX" />
                <Field label="Sucursal" value={manual.sucursal} onChange={(v) => setManual((p) => ({ ...p, sucursal: v }))} placeholder="Loja" />
                <Field label="Ramo" value={manual.ramo} onChange={(v) => setManual((p) => ({ ...p, ramo: v }))} placeholder="Vehículos" />
                <Field label="Cobertura" value={manual.cobertura} onChange={(v) => setManual((p) => ({ ...p, cobertura: v }))} placeholder="Choque / Robo / ..." />
                <Field label="Fecha ocurrencia" type="date" value={manual.fecha_ocurrencia} onChange={(v) => setManual((p) => ({ ...p, fecha_ocurrencia: v }))} />
                <Field label="Fecha reporte" type="date" value={manual.fecha_reporte} onChange={(v) => setManual((p) => ({ ...p, fecha_reporte: v }))} />
                <Field label="Monto reclamado (USD)" value={manual.monto_reclamado} onChange={(v) => setManual((p) => ({ ...p, monto_reclamado: v }))} placeholder="1500.00" />
                <Field label="Beneficiario / Proveedor" value={manual.beneficiario} onChange={(v) => setManual((p) => ({ ...p, beneficiario: v }))} placeholder="Clínica / Taller / Perito..." />
                <Field label="ID Proveedor (opcional)" value={manual.id_proveedor} onChange={(v) => setManual((p) => ({ ...p, id_proveedor: v }))} placeholder="PROV-123" />
                <Field label="Placa vehículo (opcional)" value={manual.placa_vehiculo} onChange={(v) => setManual((p) => ({ ...p, placa_vehiculo: v }))} placeholder="ABC-1234" />

                <div className="md:col-span-2">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">Descripción</div>
                  <textarea
                    className="w-full min-h-[110px] px-3 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant outline-none focus:border-primary"
                    value={manual.descripcion}
                    onChange={(e) => setManual((p) => ({ ...p, descripcion: e.target.value }))}
                    placeholder="Narrativa del siniestro…"
                  />
                </div>

                <div className="md:col-span-2">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">Documentos completos</div>
                  <select
                    className="w-full px-3 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant outline-none focus:border-primary"
                    value={manual.documentos_completos}
                    onChange={(e) => setManual((p) => ({ ...p, documentos_completos: e.target.value }))}
                  >
                    <option value="Sí">Sí</option>
                    <option value="No">No</option>
                    <option value="Incompleto">Incompleto</option>
                  </select>
                </div>

                {/* Document entries */}
                <div className="md:col-span-2">
                  <input
                    ref={docFileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*"
                    onChange={handleDocFileSelected}
                  />
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">Documentos del siniestro</div>
                  </div>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {DOC_TYPE_OPTIONS.map((tipo) => (
                      <button
                        key={tipo}
                        type="button"
                        className="flex items-center gap-1 text-label-sm font-bold text-primary border border-primary/30 hover:bg-primary/10 px-3 py-1.5 rounded-lg transition-colors"
                        onClick={() => requestDocFile(tipo)}
                      >
                        <span className="material-symbols-outlined text-[16px]">upload_file</span>
                        {tipo}
                      </button>
                    ))}
                  </div>
                  {manualDocs.length === 0 ? (
                    <div className="text-label-sm text-on-surface-variant border border-dashed border-outline-variant rounded-xl p-4 text-center">
                      Selecciona un tipo de documento para abrir el explorador de archivos y adjuntar PDF o imágenes reales.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {manualDocs.map((doc, idx) => (
                        <div key={`${doc.file.name}-${idx}`} className="border border-outline-variant rounded-xl p-4 bg-surface-container-low relative">
                          <button
                            type="button"
                            className="absolute top-3 right-3 text-on-surface-variant hover:text-error transition-colors"
                            onClick={() => removeManualDoc(idx)}
                          >
                            <span className="material-symbols-outlined text-[18px]">close</span>
                          </button>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pr-8">
                            <div>
                              <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-1">Archivo</div>
                              <p className="text-sm font-medium text-on-surface flex items-center gap-2">
                                <span className="material-symbols-outlined text-primary text-[18px]">description</span>
                                {doc.file.name}
                              </p>
                              <p className="text-[11px] text-on-surface-variant mt-1">
                                {(doc.file.size / 1024).toFixed(1)} KB
                              </p>
                            </div>
                            <div>
                              <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-1">Tipo de documento</div>
                              <select
                                className="w-full px-3 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant outline-none focus:border-primary text-sm"
                                value={doc.tipo_documento}
                                onChange={(e) => updateManualDoc(idx, 'tipo_documento', e.target.value)}
                              >
                                {DOC_TYPE_OPTIONS.map((t) => (
                                  <option key={t} value={t}>{t}</option>
                                ))}
                              </select>
                            </div>
                            <div>
                              <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-1">¿Inconsistencia detectada?</div>
                              <select
                                className="w-full px-3 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant outline-none focus:border-primary text-sm"
                                value={doc.inconsistencia_detectada}
                                onChange={(e) => updateManualDoc(idx, 'inconsistencia_detectada', e.target.value)}
                              >
                                <option value="No">No</option>
                                <option value="Sí">Sí</option>
                              </select>
                            </div>
                            <div>
                              <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-1">Observación (opcional)</div>
                              <input
                                type="text"
                                className="w-full px-3 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant outline-none focus:border-primary text-sm"
                                value={doc.observacion}
                                onChange={(e) => updateManualDoc(idx, 'observacion', e.target.value)}
                                placeholder="Observación sobre el documento…"
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {manualError && (
                  <div className="md:col-span-2 bg-error-container text-error rounded-xl p-3 border border-error/20 font-bold text-label-sm">
                    {manualError}
                  </div>
                )}
              </div>

              <div className="p-5 border-t border-outline-variant flex items-center justify-end gap-3">
                <button
                  className="px-4 py-2 rounded-lg border border-outline-variant bg-surface hover:bg-surface-container-low font-bold"
                  onClick={() => { setManualOpen(false); resetManualForm(); }}
                  disabled={manualSaving}
                >
                  Cancelar
                </button>
                <button
                  className={`px-4 py-2 rounded-lg bg-primary text-on-primary font-bold hover:opacity-90 ${manualSaving ? 'opacity-60 cursor-not-allowed' : ''}`}
                  onClick={async () => {
                    setManualError(null);
                    // front validations
                    const monto = Number(manual.monto_reclamado);
                    if (!manual.id_siniestro.trim() || !manual.id_poliza.trim() || !manual.id_asegurado.trim()) {
                      setManualError('ID siniestro, póliza y asegurado son obligatorios.');
                      return;
                    }
                    if (!manual.ramo.trim() || !manual.cobertura.trim() || !manual.sucursal.trim()) {
                      setManualError('Ramo, cobertura y sucursal son obligatorios.');
                      return;
                    }
                    if (!manual.fecha_ocurrencia || !manual.fecha_reporte) {
                      setManualError('Fechas de ocurrencia y reporte son obligatorias.');
                      return;
                    }
                    if (!Number.isFinite(monto) || monto <= 0) {
                      setManualError('Monto reclamado debe ser un número mayor a 0.');
                      return;
                    }
                    if (!manual.descripcion.trim() || !manual.beneficiario.trim()) {
                      setManualError('Descripción y beneficiario son obligatorios.');
                      return;
                    }

                    setManualSaving(true);
                    
                    // PDF Validation via Gemini
                    const pdfDocs = manualDocs.filter(d => d.file.name.toLowerCase().endsWith('.pdf'));
                    if (pdfDocs.length > 0) {
                      for (const doc of pdfDocs) {
                        try {
                          const result = await validateDocumentWithAI(doc.file, {
                            ...manual,
                            monto_reclamado: monto
                          });
                          if (!result.isValid && result.inconsistencies.length > 0) {
                            const proceed = window.confirm(
                              `⚠️ Inconsistencias detectadas en ${doc.file.name} por IA:\n\n- ` +
                              result.inconsistencies.join('\n- ') +
                              '\n\n¿Deseas guardar el siniestro de todos modos?'
                            );
                            if (!proceed) {
                              setManualSaving(false);
                              return;
                            }
                          }
                        } catch (err) {
                           console.error('Error validando PDF con IA', err);
                        }
                      }
                    }

                    try {
                      const res = await createManualClaimComplete(
                        {
                          ...manual,
                          monto_reclamado: monto,
                          monto_estimado: monto,
                          monto_pagado: 0,
                          estado: 'Reserva',
                          etiqueta_fraude_simulada: 0,
                        },
                        manualDocs,
                      );

                      if (res.claim) {
                        addClaim(res.claim);
                      } else {
                        addClaim({
                          id_siniestro: res.id_siniestro as unknown as number,
                          id_poliza: manual.id_poliza as unknown as number,
                          id_asegurado: manual.id_asegurado as unknown as number,
                          ramo: manual.ramo,
                          cobertura: manual.cobertura,
                          fecha_ocurrencia: manual.fecha_ocurrencia,
                          fecha_reporte: manual.fecha_reporte,
                          monto_reclamado: monto,
                          monto_estimado: monto,
                          sucursal: manual.sucursal,
                          beneficiario: manual.beneficiario,
                          estado: 'Reserva',
                          descripcion: manual.descripcion,
                          documentos_completos: manual.documentos_completos,
                          final_color: 'verde',
                          final_score: 0,
                          soft_score: 0,
                          hard_score: 0,
                          soft_alerts: [],
                          hard_alerts: [],
                        });
                      }

                      setCurrentPage(1);
                      setActiveTab('all');
                      setManualOpen(false);
                      resetManualForm();

                      if (res.warning) {
                        alert(res.warning);
                      }
                    } catch (e: unknown) {
                      const errorMsg = e instanceof Error ? e.message : 'Error al guardar el siniestro.';
                      setManualError(errorMsg);
                    } finally {
                      setManualSaving(false);
                    }
                  }}
                  disabled={manualSaving}
                >
                  {manualSaving ? 'Guardando…' : 'Guardar siniestro'}
                </button>
              </div>
            </div>
          </div>
        </>
      )}

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

        {/* Docs incompletos (dato real) */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 hover:bg-surface-container-low transition-colors duration-200">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-label-sm text-on-surface-variant uppercase font-bold tracking-wider w-28">DOCS INCOMPLETOS</h3>
            <span className="material-symbols-outlined text-on-surface-variant">psychiatry</span>
          </div>
          <div className="text-display font-display font-bold text-on-surface mb-2">{missingDocsCount}</div>
          <div className="text-label-md font-bold text-on-surface-variant flex items-center gap-1">
            <span className="material-symbols-outlined text-[16px]">folder_open</span>
            En los {total} siniestros cargados
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

            <button
              className={`p-2 text-on-surface-variant hover:bg-surface-container-high rounded transition-colors ${filtersOpen ? 'bg-surface-container-high' : ''}`}
              title="Filtros avanzados"
              onClick={() => setFiltersOpen((v) => !v)}
            >
              <Settings2 size={20} />
            </button>
          </div>
        </div>

        {/* Advanced Filters Panel (Settings button) */}
        {filtersOpen && (
          <div className="border-b border-outline-variant bg-surface-container-lowest px-4 py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 flex-1">
                <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/40">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">
                    Riesgo
                  </div>
                  <div className="space-y-2">
                    {(['rojo', 'amarillo', 'verde'] as const).map((c) => (
                      <label key={c} className="flex items-center gap-2 text-label-sm text-on-surface cursor-pointer">
                        <input
                          type="checkbox"
                          checked={filterColors[c]}
                          onChange={(e) => setFilterColors((p) => ({ ...p, [c]: e.target.checked }))}
                        />
                        <span className="capitalize font-bold">{c}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/40">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">
                    Sucursal
                  </div>
                  <select
                    value={filterSucursal}
                    onChange={(e) => setFilterSucursal(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-outline-variant text-body-sm"
                  >
                    {['Todas', ...Array.from(new Set(allClaims.map((c) => String(c.sucursal ?? '').trim()).filter(Boolean)))].map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/40">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">
                    Ramo
                  </div>
                  <select
                    value={filterRamo}
                    onChange={(e) => setFilterRamo(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface border border-outline-variant text-body-sm"
                  >
                    {['Todos', ...Array.from(new Set(allClaims.map((c) => String(c.ramo ?? '').trim()).filter(Boolean)))].map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/40">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">
                    Documentos
                  </div>
                  <label className="flex items-center gap-2 text-label-sm text-on-surface cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filterMissingDocs}
                      onChange={(e) => setFilterMissingDocs(e.target.checked)}
                    />
                    Solo incompletos
                  </label>
                  {q && (
                    <div className="mt-2 text-[11px] text-on-surface-variant">
                      Búsqueda activa: <span className="font-bold text-on-surface">{q}</span>{' '}
                      <button
                        className="text-primary font-bold hover:underline ml-1"
                        onClick={() => {
                          params.delete('q');
                          setParams(params, { replace: true });
                        }}
                      >
                        limpiar
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="shrink-0 flex flex-col gap-2">
                <button
                  className="px-4 py-2 rounded-lg border border-outline-variant bg-surface hover:bg-surface-container-low text-label-md font-bold"
                  onClick={() => setFiltersOpen(false)}
                >
                  Cerrar
                </button>
                <button
                  className="px-4 py-2 rounded-lg bg-primary text-on-primary text-label-md font-bold hover:opacity-90"
                  onClick={() => {
                    setFilterColors({ rojo: true, amarillo: true, verde: true });
                    setFilterSucursal('Todas');
                    setFilterRamo('Todos');
                    setFilterMissingDocs(false);
                  }}
                >
                  Reset
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Mass Actions Banner (Visible when items selected) */}
        {selectedIds.size > 0 && (
          <div className="bg-primary text-on-primary px-6 py-3 flex items-center justify-between animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center gap-3 font-label-md">
              <CheckSquare size={18} />
              <span>{selectedIds.size} siniestro{selectedIds.size === 1 ? '' : 's'} seleccionado{selectedIds.size === 1 ? '' : 's'}</span>
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
              {loading && (
                <>
                  <SkeletonRow id="skeleton-1" />
                  <SkeletonRow id="skeleton-2" />
                  <SkeletonRow id="skeleton-3" />
                  <SkeletonRow id="skeleton-4" />
                  <SkeletonRow id="skeleton-5" />
                  <SkeletonRow id="skeleton-6" />
                  <SkeletonRow id="skeleton-7" />
                </>
              )}
              {!loading && paginatedClaims.length === 0 && (
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
              )}
              {!loading && paginatedClaims.length > 0 &&
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
              }
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

interface FieldProps {
  readonly label: string;
  readonly value: string;
  readonly onChange: (v: string) => void;
  readonly placeholder?: string;
  readonly type?: string;
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: FieldProps) {
  return (
    <div>
      <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">{label}</div>
      <input
        type={type}
        className="w-full px-3 py-2 rounded-xl bg-surface-container-lowest border border-outline-variant outline-none focus:border-primary"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}
