import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useClaim, useClaims } from '../hooks/useClaims';
import { API_BASE, explainClaim, deleteClaim, type Claim, type ClaimDocument } from '../services/api';
import ReactMarkdown from 'react-markdown';

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCurrency(n: number | undefined | null): string {
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

function riskColor(color: Claim['final_color'] | undefined) {
  if (color === 'rojo') return { text: 'text-error', bg: 'text-error', ring: 'stroke-error', label: 'Riesgo Muy Alto', badge: 'bg-error-container text-on-error-container' };
  if (color === 'amarillo') return { text: 'text-yellow-600', bg: 'text-yellow-600', ring: 'stroke-yellow-500', label: 'Riesgo Medio', badge: 'bg-yellow-100 text-yellow-800' };
  return { text: 'text-green-600', bg: 'text-green-600', ring: 'stroke-green-500', label: 'Riesgo Bajo', badge: 'bg-green-100 text-green-800' };
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
function SkeletonBlock({ h = 'h-6', w = 'w-full' }: { h?: string; w?: string }) {
  return <div className={`animate-pulse bg-surface-container-high rounded ${h} ${w}`} />;
}

// ── Score Ring ────────────────────────────────────────────────────────────────
function ScoreRing({ score, color }: { score: number; color: Claim['final_color'] }) {
  const rc = riskColor(color);
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);

  return (
    <div className="w-32 h-32 relative">
      <svg className="w-full h-full -rotate-90">
        <circle className="text-surface-container-highest" cx="64" cy="64" fill="transparent" r={radius} stroke="currentColor" strokeWidth="8" />
        <circle
          className={`${rc.ring} transition-all duration-700`}
          cx="64" cy="64" fill="transparent" r={radius}
          stroke="currentColor"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeWidth="8"
          strokeLinecap="round"
        />
      </svg>
      <div className={`absolute inset-0 flex items-center justify-center font-headline-sm ${rc.text}`}>
        {score}%
      </div>
    </div>
  );
}

// ── Claim Timeline ───────────────────────────────────────────────────────
interface TimelineStep {
  key: string;
  label: string;
  icon: string;
  date: string | undefined;
}

function daysBetween(a: string | undefined, b: string | undefined): number | null {
  if (!a || !b) return null;
  try {
    const da = new Date(a);
    const db = new Date(b);
    if (isNaN(da.getTime()) || isNaN(db.getTime())) return null;
    return Math.round((db.getTime() - da.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return null;
  }
}

function gapSeverity(days: number | null): 'ok' | 'warning' | 'danger' {
  if (days === null) return 'ok';
  if (days < 0) return 'danger';
  if (days > 90) return 'danger';
  if (days > 30) return 'warning';
  return 'ok';
}

function ClaimTimeline({ claim }: { claim: Claim }) {
  const docs = claim.documentos ?? [];
  const docDates = docs
    .map((d) => d.fecha_emision)
    .filter((d): d is string => !!d)
    .sort();
  const latestDocDate = docDates.length > 0 ? docDates[docDates.length - 1] : undefined;

  const steps: TimelineStep[] = [
    { key: 'poliza', label: 'Inicio Póliza', icon: 'shield', date: claim.poliza_fecha_inicio },
    { key: 'ocurrencia', label: 'Ocurrencia', icon: 'fmd_bad', date: claim.fecha_ocurrencia },
    { key: 'reporte', label: 'Reporte', icon: 'edit_document', date: claim.fecha_reporte },
    { key: 'documentos', label: 'Documentos', icon: 'folder_open', date: latestDocDate },
  ];

  const gaps: { days: number | null; severity: 'ok' | 'warning' | 'danger' }[] = [];
  for (let i = 0; i < steps.length - 1; i++) {
    const d = daysBetween(steps[i].date, steps[i + 1].date);
    gaps.push({ days: d, severity: gapSeverity(d) });
  }

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:bg-surface-container-low transition-colors duration-200">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
          Línea de Tiempo del Siniestro
        </h3>
        <span className="material-symbols-outlined text-on-surface-variant text-[20px]">timeline</span>
      </div>

      <div className="claim-timeline">
        {steps.map((step, i) => {
          const filled = !!step.date;
          return (
            <div className="timeline-step" key={step.key}>
              <div className={`timeline-node ${filled ? 'timeline-node--filled' : 'timeline-node--empty'}`}>
                <span className="material-symbols-outlined" style={filled ? { fontVariationSettings: "'FILL' 1" } : {}}>
                  {step.icon}
                </span>
              </div>
              <div className="timeline-label">
                <span className="timeline-label__title">{step.label}</span>
                <span className={`timeline-label__date ${!filled ? 'timeline-label__date--empty' : ''}`}>
                  {filled ? formatDate(step.date) : 'Sin dato'}
                </span>
              </div>

              {i < gaps.length && gaps[i].days !== null && gaps[i].severity !== 'ok' && (
                <div className="timeline-gap-flag" style={{ left: 'calc(50% + 50%)', top: '-2px' }}>
                  <span
                    className={`gap-badge ${gaps[i].severity === 'danger' ? 'gap-badge--danger' : 'gap-badge--warning'}`}
                    title={`${gaps[i].days} días entre ${steps[i].label} y ${steps[i + 1].label}`}
                  >
                    <span className="material-symbols-outlined">
                      {gaps[i].severity === 'danger' ? 'error' : 'warning'}
                    </span>
                    {gaps[i].days! < 0 ? `${Math.abs(gaps[i].days!)}d antes` : `${gaps[i].days}d`}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex justify-center gap-6 mt-3 flex-wrap">
        {gaps.map((gap, i) => {
          if (gap.days === null) return null;
          const color =
            gap.severity === 'danger'
              ? 'text-error'
              : gap.severity === 'warning'
                ? 'text-yellow-700'
                : 'text-on-surface-variant';
          return (
            <div key={i} className={`flex items-center gap-1.5 text-[11px] font-bold ${color}`}>
              {gap.severity !== 'ok' && (
                <span className="material-symbols-outlined text-[13px]">
                  {gap.severity === 'danger' ? 'error' : 'warning'}
                </span>
              )}
              <span>
                {steps[i].label} → {steps[i + 1].label}: {gap.days! < 0 ? `−${Math.abs(gap.days!)}` : gap.days}d
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Claim Selector (when no ID in URL) ────────────────────────────────────────
function ClaimSelector({ onSelect }: { onSelect: (id: number) => void }) {
  const [searchInput, setSearchInput] = useState('');
  const { claims, loading, removeClaim } = useClaims({ page: 1, limit: 20 });

  const filtered = claims.filter(
    (c) =>
      String(c.id_siniestro).includes(searchInput) ||
      (c.beneficiario ?? '').toLowerCase().includes(searchInput.toLowerCase()) ||
      (c.ramo ?? '').toLowerCase().includes(searchInput.toLowerCase()),
  );

  return (
    <div className="max-w-2xl mx-auto mt-16">
      <div className="text-center mb-8">
        <span className="material-symbols-outlined text-[48px] text-on-surface-variant mb-4 block">manage_search</span>
        <h2 className="text-headline-md font-bold text-on-surface mb-2">Selecciona un Siniestro</h2>
        <p className="text-body-md text-on-surface-variant">Busca por ID, beneficiario o ramo para comenzar el análisis.</p>
      </div>

      <div className="relative mb-6">
        <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant">search</span>
        <input
          className="w-full pl-12 pr-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-xl text-body-md focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
          placeholder="Buscar siniestro..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {loading ? (
          <div className="text-center text-on-surface-variant py-8 animate-pulse">Cargando siniestros…</div>
        ) : (
          filtered.map((c) => {
            const rc = riskColor(c.final_color);
            return (
              <button
                key={c.id_siniestro}
                className="w-full flex items-center justify-between p-4 bg-surface-container-lowest border border-outline-variant rounded-xl hover:bg-surface-container-low transition-colors text-left"
                onClick={() => onSelect(c.id_siniestro)}
              >
                <div>
                  <span className="font-mono font-bold text-primary text-label-md">#{c.id_siniestro}</span>
                  <span className="mx-2 text-on-surface-variant">·</span>
                  <span className="text-body-md text-on-surface">{c.beneficiario ?? '—'}</span>
                  <span className="ml-2 text-label-sm text-on-surface-variant">{c.ramo}</span>
                </div>
                <span className={`text-label-sm font-bold ${rc.text}`}>
                  {c.final_score}/100
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

// ── Docs Drawer ──────────────────────────────────────────────────────────────
function DocsDrawer({ claim, onClose }: { claim: Claim; onClose: () => void }) {
  const docs: ClaimDocument[] = claim.documentos ?? [];
  const missing = docs.filter((d) => d.entregado === 'No');
  const flagged = docs.filter((d) => d.inconsistencia_detectada === 'Sí');

  // Build a Google Maps search URL using the sucursal city name in Ecuador
  const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    `${claim.sucursal ?? 'Ecuador'}, Ecuador`
  )}`;

  return (
    <div className="fixed right-0 top-0 h-full w-[520px] bg-surface-container-lowest border-l border-outline-variant shadow-2xl z-50 flex flex-col transform transition-all duration-300 ease-in-out">
      {/* Header */}
      <div className="p-6 border-b border-outline-variant flex justify-between items-center bg-surface shrink-0">
        <div>
          <h3 className="font-headline-md text-headline-md text-on-surface">Documentación del Siniestro</h3>
          <p className="text-label-sm text-on-surface-variant mt-0.5">#{claim.id_siniestro} · {claim.ramo}</p>
        </div>
        <button className="p-2 hover:bg-surface-container-high rounded-full transition-colors" onClick={onClose}>
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar">
        {/* Summary banner */}
        <div className="p-6 pb-0 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-surface-container-low border border-outline-variant rounded-xl p-3 text-center">
              <p className="text-[28px] font-bold text-on-surface">{docs.length}</p>
              <p className="text-[10px] text-on-surface-variant uppercase tracking-wider font-bold mt-0.5">Total Docs</p>
            </div>
            <div className={`rounded-xl p-3 text-center border ${missing.length > 0 ? 'bg-error-container border-error/30' : 'bg-surface-container-low border-outline-variant'}`}>
              <p className={`text-[28px] font-bold ${missing.length > 0 ? 'text-error' : 'text-on-surface'}`}>{missing.length}</p>
              <p className={`text-[10px] uppercase tracking-wider font-bold mt-0.5 ${missing.length > 0 ? 'text-error' : 'text-on-surface-variant'}`}>Faltantes</p>
            </div>
            <div className={`rounded-xl p-3 text-center border ${flagged.length > 0 ? 'bg-yellow-50 border-yellow-300' : 'bg-surface-container-low border-outline-variant'}`}>
              <p className={`text-[28px] font-bold ${flagged.length > 0 ? 'text-yellow-700' : 'text-on-surface'}`}>{flagged.length}</p>
              <p className={`text-[10px] uppercase tracking-wider font-bold mt-0.5 ${flagged.length > 0 ? 'text-yellow-700' : 'text-on-surface-variant'}`}>Inconsistencias</p>
            </div>
          </div>
        </div>

        {/* Document list */}
        <div className="p-6 space-y-3">
          <h4 className="text-label-xs font-bold text-on-surface-variant uppercase tracking-wider mb-4">Detalle de Documentos</h4>
          {docs.length === 0 ? (
            <div className="py-12 text-center text-on-surface-variant">
              <span className="material-symbols-outlined text-[48px] mb-2 block">folder_open</span>
              <p className="text-body-md">No hay documentos registrados para este siniestro.</p>
            </div>
          ) : (
            docs.map((doc) => {
              const entregado = doc.entregado === 'Sí' || doc.entregado === 'Si';
              const legible = doc.legible === 'Sí' || doc.legible === 'Si';
              const inconsistente = doc.inconsistencia_detectada === 'Sí' || doc.inconsistencia_detectada === 'Si';

              return (
                <div
                  key={doc.id_documento}
                  className={`rounded-xl border p-4 transition-colors ${inconsistente
                    ? 'border-yellow-300 bg-yellow-50'
                    : !entregado
                      ? 'border-error/30 bg-error-container/20'
                      : 'border-outline-variant bg-surface-container-lowest hover:bg-surface-container-low'
                    }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${inconsistente ? 'bg-yellow-100' : !entregado ? 'bg-error-container' : 'bg-surface-container-high'
                        }`}>
                        <span className={`material-symbols-outlined text-[20px] ${inconsistente ? 'text-yellow-700' : !entregado ? 'text-error' : 'text-on-surface-variant'
                          }`}>
                          {inconsistente ? 'warning' : !entregado ? 'block' : 'description'}
                        </span>
                      </div>
                      <div>
                        <p className="font-label-md font-bold text-on-surface">{doc.tipo_documento}</p>
                        <p className="text-[11px] text-on-surface-variant font-mono mt-0.5">{doc.id_documento}</p>
                        {doc.observacion && (
                          <p className="text-label-sm text-yellow-800 mt-2 leading-relaxed">
                            ⚠️ {doc.observacion}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1.5 shrink-0">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${entregado ? 'bg-green-100 text-green-700' : 'bg-error-container text-error'
                        }`}>
                        {entregado ? '✓ Entregado' : '✗ Faltante'}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${legible ? 'bg-surface-container-high text-on-surface-variant' : 'bg-error-container text-error'
                        }`}>
                        {legible ? 'Legible' : 'Ilegible'}
                      </span>
                    </div>
                  </div>

                  {doc.fecha_emision && (
                    <p className="mt-2 text-[11px] text-on-surface-variant ml-12">
                      Emitido: {new Date(doc.fecha_emision).toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </p>
                  )}

                  {doc.archivo_pdf && (
                    <div className="mt-4 ml-12 flex items-center gap-2">
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-high px-3 py-2 text-label-sm font-bold text-primary hover:bg-primary/5 transition-colors"
                        onClick={() => window.open(`${API_BASE}/api/claims/${claim.id_siniestro}/documentos/${doc.id_documento}/preview`, '_blank')}
                      >
                        <span className="material-symbols-outlined">visibility</span>
                        Ver archivo
                      </button>
                      <span className="text-[11px] text-on-surface-variant">{doc.archivo_pdf}</span>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Location section with Google Maps link */}
        <div className="px-6 pb-6">
          <div className="border border-outline-variant rounded-xl overflow-hidden">
            <div className="p-4 bg-surface-container-low border-b border-outline-variant flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">location_on</span>
              <div>
                <p className="font-label-md font-bold text-on-surface">Sucursal del Siniestro</p>
                <p className="text-label-sm text-on-surface-variant">{claim.sucursal}, Ecuador</p>
              </div>
            </div>
            {/* Static maps preview using placeholder embed */}
            <div
              className="w-full h-36 relative bg-surface-container-high flex items-center justify-center overflow-hidden cursor-pointer group"
              onClick={() => window.open(mapsUrl, '_blank')}
            >
              {/* Decorative grid pattern imitating a map */}
              <div
                className="absolute inset-0 opacity-30"
                style={{
                  backgroundImage:
                    'linear-gradient(#c4c7c7 1px, transparent 1px), linear-gradient(90deg, #c4c7c7 1px, transparent 1px)',
                  backgroundSize: '30px 30px',
                }}
              />
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 z-10 group-hover:bg-primary/5 transition-colors">
                <div className="w-12 h-12 bg-primary rounded-full shadow-lg flex items-center justify-center">
                  <span className="material-symbols-outlined text-on-primary text-[24px]" style={{ fontVariationSettings: "'FILL' 1" }}>location_on</span>
                </div>
                <p className="text-label-sm font-bold text-on-surface">{claim.sucursal}, Ecuador</p>
              </div>
            </div>
            <a
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 p-3.5 bg-surface-container-lowest hover:bg-surface-container-low transition-colors text-primary font-label-md font-bold border-t border-outline-variant"
            >
              <span className="material-symbols-outlined text-[18px]">open_in_new</span>
              Ver en Google Maps
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Delete Confirmation Modal ────────────────────────────────────────────────
const DELETE_REASONS = [
  'Error de ingreso de datos',
  'Fraude confirmado — causa mayor',
  'Siniestro duplicado',
  'Siniestro cancelado por el asegurado',
  'Otro motivo',
];

function DeleteModal({
  claim,
  onConfirm,
  onCancel,
  isDeleting,
}: {
  claim: Claim;
  onConfirm: (motivo: string) => void;
  onCancel: () => void;
  isDeleting: boolean;
}) {
  const [motivo, setMotivo] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const idStr = String(claim.id_siniestro);
  const canDelete = motivo !== '' && confirmText === idStr;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onCancel} />

      {/* Modal */}
      <div className="relative w-full max-w-md bg-surface-container-lowest rounded-2xl shadow-2xl border border-outline-variant overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-outline-variant bg-error-container/30">
          <div className="w-10 h-10 rounded-full bg-error flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-on-error text-[22px]">delete_forever</span>
          </div>
          <div>
            <h3 className="font-bold text-on-surface text-headline-sm">Eliminar Siniestro</h3>
            <p className="text-label-sm text-on-surface-variant font-mono">#{idStr}</p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Warning */}
          <div className="flex gap-3 p-4 bg-error-container/40 border border-error/30 rounded-xl">
            <span className="material-symbols-outlined text-error text-[20px] shrink-0 mt-0.5">warning</span>
            <p className="text-label-md text-on-surface leading-relaxed">
              Esta acción es <strong>permanente e irreversible</strong>. Se eliminarán el siniestro y todos sus documentos asociados.
            </p>
          </div>

          {/* Reason selector */}
          <div className="space-y-2">
            <label className="text-label-sm font-bold text-on-surface-variant uppercase tracking-wider">
              Motivo de eliminación <span className="text-error">*</span>
            </label>
            <select
              id="delete-motivo"
              className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-3 py-2.5 text-body-md text-on-surface focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            >
              <option value="">Selecciona un motivo…</option>
              {DELETE_REASONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          {/* Confirm by typing ID */}
          <div className="space-y-2">
            <label className="text-label-sm font-bold text-on-surface-variant uppercase tracking-wider">
              Escribe el ID <span className="font-mono text-primary">{idStr}</span> para confirmar <span className="text-error">*</span>
            </label>
            <input
              id="delete-confirm-text"
              type="text"
              className="w-full bg-surface-container-low border border-outline-variant rounded-lg px-3 py-2.5 font-mono text-body-md text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-error focus:ring-2 focus:ring-error/20 transition-all"
              placeholder={idStr}
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              autoComplete="off"
            />
            {confirmText && confirmText !== idStr && (
              <p className="text-label-sm text-error">El ID no coincide.</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button
              id="delete-cancel-btn"
              className="flex-1 py-2.5 border border-outline-variant rounded-lg font-label-md font-bold text-on-surface hover:bg-surface-container-low transition-colors"
              onClick={onCancel}
              disabled={isDeleting}
            >
              Cancelar
            </button>
            <button
              id="delete-confirm-btn"
              className={`flex-1 py-2.5 rounded-lg font-label-md font-bold text-on-error transition-all flex items-center justify-center gap-2 ${
                canDelete && !isDeleting
                  ? 'bg-error hover:opacity-90 active:scale-95'
                  : 'bg-error/40 cursor-not-allowed'
              }`}
              onClick={() => canDelete && onConfirm(motivo)}
              disabled={!canDelete || isDeleting}
            >
              {isDeleting ? (
                <>
                  <span className="w-4 h-4 border-2 border-on-error/40 border-t-on-error rounded-full animate-spin" />
                  Eliminando…
                </>
              ) : (
                <>
                  Eliminar permanentemente
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function ClaimAnalyzer() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const idParam = searchParams.get('id');

  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isDocsOpen, setIsDocsOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);

  const { claim, loading, error } = useClaim(idParam);

  // Normalize scores: if backend sends values in 0-1, scale to 0-100
  const rawFinal = claim?.final_score ?? 0;
  const rawSoft = claim?.soft_score ?? 0;
  const rawHard = claim?.hard_score ?? 0;
  const score = rawFinal <= 1 ? rawFinal * 100 : rawFinal;
  const softScore = rawSoft <= 1 ? rawSoft * 100 : rawSoft;
  const hardScore = rawHard <= 1 ? rawHard * 100 : rawHard;

  const rc = claim ? riskColor(claim.final_color) : riskColor(undefined);
  const softAlerts = claim?.soft_alerts ?? [];
  const hardAlerts = claim?.hard_alerts ?? [];
  const allAlerts = [...hardAlerts, ...softAlerts];

  const handleSelectClaim = (id: number) => {
    setSearchParams({ id: String(id) });
  };

  const { removeClaim } = useClaims({ page: 1, limit: 20 });

  const handleDelete = async (motivo: string) => {
    if (!idParam) return;
    setIsDeleting(true);
    try {
      await deleteClaim(idParam, motivo);
      // Optimistically remove from local list immediately
      removeClaim(idParam);
      // Notify all other useClaims instances (Dashboard, etc.) to refetch
      window.dispatchEvent(new CustomEvent('claim-deleted', { detail: { id: idParam } }));
      setIsDeleteOpen(false);
      setDeleteSuccess(idParam);
      // Navigate back to the claim list after a short delay
      setTimeout(() => {
        setSearchParams({});
      }, 1500);
    } catch (e: any) {
      alert(`Error al eliminar: ${e.message ?? 'Error desconocido'}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleExplain = async () => {
    if (!idParam) return;
    setLoadingExplain(true);
    setExplainError(null);
    setExplanation(null);
    setIsDrawerOpen(true);
    try {
      const res = await explainClaim(idParam);
      setExplanation(res.explanation);
    } catch (e: any) {
      setExplainError(e.message ?? 'Error al obtener explicación');
    } finally {
      setLoadingExplain(false);
    }
  };

  // No ID selected → show selector
  if (!idParam) {
    return <ClaimSelector onSelect={handleSelectClaim} />;
  }

  return (
    <>
      {/* Header Section */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <nav className="flex gap-2 text-label-sm text-on-surface-variant mb-2">
            <button className="hover:text-primary transition-colors" onClick={() => navigate('/')}>Dashboard</button>
            <span>/</span>
            <button className="hover:text-primary transition-colors" onClick={() => setSearchParams({})}>Siniestros</button>
            <span>/</span>
            <span className="text-primary font-bold">#{idParam}</span>
          </nav>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">Analizador de Siniestros</h2>
        </div>
        
      </div>

      {/* Error state */}
      {error && (
        <div className="p-6 bg-error-container text-error rounded-xl border border-error/30 mb-6">
          <p className="font-bold">Error al cargar el siniestro #{idParam}</p>
          <p className="text-label-sm">{error}</p>
        </div>
      )}

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-12 gap-6 items-start">
        {/* Left Column */}
        <div className="col-span-12 lg:col-span-8 space-y-6">

          {/* Combined Score Card */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex items-center justify-between hover:bg-surface-container-low transition-colors duration-200">
            <div>
              <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-4">
                Score Combinado de Fraude
              </h3>
              {loading ? (
                <div className="space-y-2">
                  <SkeletonBlock h="h-10" w="w-32" />
                  <SkeletonBlock h="h-6" w="w-48" />
                </div>
              ) : (
                <div className="flex items-end gap-3">
                  <span className={`font-display text-display leading-none ${rc.text}`}>{score.toFixed(1)}</span>
                  <span className="font-headline-sm text-on-surface-variant pb-1">/ 100</span>
                  <span className={`ml-4 ${rc.badge} px-3 py-1 rounded-full font-label-sm flex items-center gap-1`}>
                    <span className="material-symbols-outlined text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>warning</span>
                    {rc.label}
                  </span>
                </div>
              )}
            </div>
            {loading ? (
              <div className="w-32 h-32 rounded-full bg-surface-container-high animate-pulse" />
            ) : (
              <ScoreRing score={Math.round(score)} color={claim?.final_color ?? 'verde'} />
            )}
          </div>

          {/* Anomaly Alert */}
          {!loading && claim?.is_anomaly && (
            <div className="bg-error-container border border-error/50 rounded-xl p-4 flex items-center gap-4">
              <div className="bg-error text-on-error w-10 h-10 rounded-full flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined">psychology_alt</span>
              </div>
              <div>
                <h3 className="font-bold text-error">Detección de Anomalías: Comportamiento Atípico</h3>
                <p className="text-on-error-container text-sm">El modelo no supervisado (Isolation Forest) detectó que los patrones numéricos de este siniestro son atípicos frente al histórico.</p>
              </div>
            </div>
          )}

          {/* Claim Timeline */}
          {!loading && claim && (
            <ClaimTimeline claim={claim} />
          )}

          {/* Analysis Breakdown Cards */}
          <div className="grid grid-cols-2 gap-6">
            {/* Rule Engine */}
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:bg-surface-container-low transition-colors duration-200">
              <div className="flex justify-between items-start mb-6">
                <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
                  Score Reglas (Heurístico)
                </h3>
                <span className="material-symbols-outlined text-on-surface-variant">gavel</span>
              </div>
              {loading ? <SkeletonBlock h="h-8" w="w-24" /> : (
                <>
                  <div className="flex items-center gap-4">
                    <span className="font-display text-headline-lg text-primary">{softScore.toFixed(0)}%</span>
                    <div className="flex-1 bg-surface-container-highest h-2 rounded-full overflow-hidden">
                      <div className="bg-primary h-full transition-all duration-700" style={{ width: `${softScore}%` }} />
                    </div>
                  </div>
                  <p className="mt-4 font-body-md text-on-surface-variant">
                    {softAlerts.length} alertas activadas en motor heurístico.
                  </p>
                </>
              )}
            </div>

            {/* ML Model */}
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 hover:bg-surface-container-low transition-colors duration-200">
              <div className="flex justify-between items-start mb-6">
                <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">
                  Score Reglas Duras
                </h3>
                <span className="material-symbols-outlined text-on-surface-variant">auto_awesome</span>
              </div>
              {loading ? <SkeletonBlock h="h-8" w="w-24" /> : (
                <>
                  <div className="flex items-center gap-4">
                    <span className="font-display text-headline-lg text-primary">{hardScore.toFixed(0)}%</span>
                    <div className="flex-1 bg-surface-container-highest h-2 rounded-full overflow-hidden">
                      <div className="bg-primary h-full transition-all duration-700" style={{ width: `${hardScore}%` }} />
                    </div>
                  </div>
                  <p className="mt-4 font-body-md text-on-surface-variant">
                    {hardAlerts.length} reglas duras activadas.
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Activated Alerts List */}
          {!loading && allAlerts.length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
              <div className="p-6 border-b border-outline-variant flex justify-between items-center bg-surface-container-lowest">
                <h3 className="font-headline-sm text-headline-sm text-on-surface">Alertas Activadas</h3>
                <span className="bg-surface-container-high px-2 py-1 rounded font-label-sm text-on-surface-variant">
                  Total: {allAlerts.length}
                </span>
              </div>
              <div className="divide-y divide-outline-variant bg-surface-container-lowest">
                {hardAlerts.map((alert, i) => (
                  <div key={`hard-${i}`} className="p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors">
                    <div className="flex gap-4 items-start">
                      <div className="w-8 h-8 rounded bg-error-container flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-error text-[20px]">priority_high</span>
                      </div>
                      <div>
                        <p className="font-label-md font-bold text-on-surface">Regla Dura Activada</p>
                        <p className="font-body-md text-on-surface-variant">{alert}</p>
                      </div>
                    </div>
                    <span className="font-label-md text-error font-bold">HARD</span>
                  </div>
                ))}
                {softAlerts.map((alert, i) => (
                  <div key={`soft-${i}`} className="p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors">
                    <div className="flex gap-4 items-start">
                      <div className="w-8 h-8 rounded bg-surface-container-high flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-on-surface-variant text-[20px]">warning</span>
                      </div>
                      <div>
                        <p className="font-label-md font-bold text-on-surface">Alerta Heurística</p>
                        <p className="font-body-md text-on-surface-variant">{alert}</p>
                      </div>
                    </div>
                    <span className="font-label-md text-on-surface-variant font-bold">SOFT</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Technical File */}
        <div className="col-span-12 lg:col-span-4 space-y-6">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 sticky top-24 hover:bg-surface-container-low transition-colors duration-200">
            <h3 className="font-headline-sm text-headline-sm text-on-surface mb-6">Ficha Técnica del Reclamo</h3>
            {loading ? (
              <div className="space-y-4">
                <SkeletonBlock h="h-12" />
                <SkeletonBlock h="h-6" w="w-3/4" />
                <SkeletonBlock h="h-6" w="w-2/3" />
                <SkeletonBlock h="h-6" w="w-4/5" />
                <SkeletonBlock h="h-6" w="w-1/2" />
              </div>
            ) : claim ? (
              <div className="space-y-5">
                {/* Beneficiary */}
                <div className="flex flex-col gap-1">
                  <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Beneficiario</span>
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-secondary-fixed flex items-center justify-center font-bold text-primary text-label-md">
                      {(claim.beneficiario ?? '?').slice(0, 2).toUpperCase()}
                    </div>
                    <p className="font-label-md font-bold text-on-surface">{claim.beneficiario ?? '—'}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Ramo</span>
                    <p className="font-body-md font-bold text-on-surface">{claim.ramo}</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Cobertura</span>
                    <p className="font-body-md font-bold text-on-surface">{claim.cobertura}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Póliza</span>
                    <p className="font-body-md font-bold text-on-surface">#{claim.id_poliza}</p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Monto Reclamado</span>
                    <p className={`font-body-md font-bold ${rc.text}`}>{formatCurrency(claim.monto_reclamado)}</p>
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Fecha de Evento</span>
                  <div className="flex items-center gap-2 font-body-md text-on-surface">
                    <span className="material-symbols-outlined text-[18px]">calendar_today</span>
                    {formatDate(claim.fecha_ocurrencia)}
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Sucursal</span>
                  <div className="flex items-center gap-2 font-body-md text-on-surface">
                    <span className="material-symbols-outlined text-[18px]">pin_drop</span>
                    {claim.sucursal ?? '—'}
                  </div>
                </div>

                {claim.estado && (
                  <div className="flex flex-col gap-1">
                    <span className="font-label-sm text-on-surface-variant uppercase tracking-wider">Estado</span>
                    <p className="font-body-md text-on-surface">{claim.estado}</p>
                  </div>
                )}

                <div className="pt-5 border-t border-outline-variant space-y-3">
                  <button
                    className="w-full py-2.5 bg-primary text-on-primary rounded-lg font-label-md font-bold hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                    onClick={handleExplain}
                  >
                    <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
                    Obtener Explicación IA
                  </button>
                  <button
                    className="w-full py-2.5 bg-surface border border-outline-variant rounded-lg font-label-md font-bold hover:bg-surface-container-low transition-colors flex items-center justify-center gap-2"
                    onClick={() => setIsDocsOpen(true)}
                  >
                    <span className="material-symbols-outlined text-[18px]">folder_open</span>
                    Ver Documentación
                    {claim?.documentos && claim.documentos.filter(d => d.entregado === 'No' || d.inconsistencia_detectada === 'Sí').length > 0 && (
                      <span className="ml-auto bg-error text-on-error text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                        {claim.documentos.filter(d => d.entregado === 'No' || d.inconsistencia_detectada === 'Sí').length}
                      </span>
                    )}
                  </button>
                  <button
                    id="delete-claim-btn"
                    className="w-full py-2.5 bg-surface border border-error/40 text-error rounded-lg font-label-md font-bold hover:bg-error-container/40 transition-colors flex items-center justify-center gap-2"
                    onClick={() => setIsDeleteOpen(true)}
                  >
                    <span className="material-symbols-outlined text-[18px]">delete_forever</span>
                    Eliminar Siniestro
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Delete Success Toast */}
      {deleteSuccess && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-surface-container-lowest border border-outline-variant rounded-xl shadow-2xl px-5 py-3 animate-bounce-once">
          <span className="material-symbols-outlined text-green-600" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
          <p className="text-body-md font-bold text-on-surface">Siniestro <span className="font-mono text-primary">#{deleteSuccess}</span> eliminado correctamente.</p>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteOpen && claim && (
        <DeleteModal
          claim={claim}
          onConfirm={handleDelete}
          onCancel={() => setIsDeleteOpen(false)}
          isDeleting={isDeleting}
        />
      )}

      {/* Documentation Drawer */}
      {isDocsOpen && claim && (
        <>
          <div className="fixed inset-0 bg-black/20 z-40" onClick={() => setIsDocsOpen(false)} />
          <DocsDrawer claim={claim} onClose={() => setIsDocsOpen(false)} />
        </>
      )}

      {/* AI Explanation Drawer */}
      <div
        className={`fixed right-0 top-0 h-full w-[480px] bg-surface-container-lowest border-l border-outline-variant shadow-2xl z-40 transform transition-transform duration-300 ease-in-out ${isDrawerOpen ? 'translate-x-0' : 'translate-x-full'}`}
        id="explain-drawer"
      >
        <div className="flex flex-col h-full">
          <div className="p-6 border-b border-outline-variant flex justify-between items-center bg-surface">
            <h3 className="font-headline-md text-headline-md text-on-surface">Explicación del Agente IA</h3>
            <button className="p-2 hover:bg-surface-container-high rounded-full transition-colors" onClick={() => setIsDrawerOpen(false)}>
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-4 no-scrollbar">
            {loadingExplain ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-on-surface-variant">
                <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center animate-pulse">
                  <span className="material-symbols-outlined text-on-primary">auto_awesome</span>
                </div>
                <p className="text-body-md">El agente está analizando el siniestro…</p>
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            ) : explainError ? (
              <div className="p-4 bg-error-container text-error rounded-xl">
                <p className="font-bold mb-1">Error</p>
                <p className="text-label-sm">{explainError}</p>
              </div>
            ) : explanation ? (
              <div className="bg-surface-container-low rounded-xl border border-outline-variant shadow-sm overflow-hidden flex flex-col">
                {/* Cabecera */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-outline-variant bg-surface-container-lowest">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary text-xl">auto_awesome</span>
                    <p className="font-label-sm text-on-surface-variant font-semibold uppercase tracking-wider mb-0">
                      Análisis de IA
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigator.clipboard.writeText(explanation)}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-primary hover:bg-primary/10 transition-colors"
                  >
                    <span className="material-symbols-outlined text-sm">content_copy</span>
                    Copiar
                  </button>
                </div>

                {/* Contenido parseado de Markdown */}
                <div className="p-5 font-body-md text-on-surface leading-relaxed aianalisis-content">
                  <ReactMarkdown>{explanation}</ReactMarkdown>
                </div>
              </div>
            ) : (
              <div className="text-center text-on-surface-variant py-8">
                <span className="material-symbols-outlined text-[48px] mb-2 block">auto_awesome</span>
                <p className="text-body-md">Pulsa "Obtener Explicación IA" para analizar este siniestro.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
