import { useNavigate } from 'react-router-dom';
import { useClaims } from '../hooks/useClaims';
import type { Claim } from '../services/api';

function RiskBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 75 ? 'bg-error' : pct >= 40 ? 'bg-primary' : 'bg-green-500';
  return (
    <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
      <div className={`h-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function SkeletonAlert() {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 animate-pulse">
      <div className="h-3 bg-surface-container-high rounded w-1/3 mb-2" />
      <div className="h-4 bg-surface-container-high rounded w-2/3 mb-3" />
      <div className="h-1.5 bg-surface-container-high rounded w-full" />
    </div>
  );
}

function AlertCard({ claim, isCritical }: { claim: Claim; isCritical: boolean }) {
  const navigate = useNavigate();
  const score = claim.final_score ?? 0;

  if (isCritical) {
    return (
      <div className="bg-surface-container-lowest border-l-4 border-error border-t border-r border-b border-outline-variant rounded-r-xl p-4 shadow-sm hover:shadow-md transition-shadow relative">
        <span className="absolute top-4 right-4 material-symbols-outlined text-error">priority_high</span>
        <div className="text-label-sm font-bold text-error uppercase tracking-wider mb-1">
          CRITICAL #{claim.id_siniestro}
        </div>
        <h4 className="text-body-lg font-bold text-on-surface mb-3">
          {claim.beneficiario ?? `Siniestro #${claim.id_siniestro}`}
        </h4>
        <div className="mb-3">
          <RiskBar score={score} />
          <div className="flex justify-between mt-1">
            <span className="text-label-sm text-on-surface-variant">{claim.ramo}</span>
            <span className="font-bold text-error text-label-sm">Risk: {score}/100</span>
          </div>
        </div>
        {claim.soft_alerts && claim.soft_alerts.length > 0 && (
          <p className="text-label-sm text-on-surface-variant mb-3 italic line-clamp-2">
            {claim.soft_alerts[0]}
          </p>
        )}
        <button
          className="w-full py-2 bg-error text-on-error rounded font-label-md font-bold hover:bg-red-800 transition-colors"
          onClick={() => navigate(`/analyzer?id=${claim.id_siniestro}`)}
        >
          Analizar Siniestro
        </button>
      </div>
    );
  }

  return (
    <div
      className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 hover:bg-surface-container-low transition-colors cursor-pointer"
      onClick={() => navigate(`/analyzer?id=${claim.id_siniestro}`)}
    >
      <div className="text-label-sm text-on-surface-variant uppercase tracking-wider mb-1">
        SINIESTRO #{claim.id_siniestro}
      </div>
      <h4 className="text-body-md font-bold text-on-surface mb-3">
        {claim.beneficiario ?? claim.ramo}
      </h4>
      <div className="flex justify-between items-center text-label-md mb-2">
        <span className="text-on-surface-variant">{claim.cobertura}</span>
        <span className={`font-bold ${score >= 75 ? 'text-error' : 'text-on-surface'}`}>
          Risk: {score}/100
        </span>
      </div>
      <RiskBar score={score} />
    </div>
  );
}

export default function AlertsPanel() {
  const { claims, total, loading } = useClaims({ page: 1, limit: 5, color: 'rojo' });

  return (
    <aside className="w-[320px] shrink-0 space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-headline-sm font-headline-sm font-bold text-on-surface">Alertas Críticas</h3>
        <span className="bg-error text-on-error px-2 py-0.5 rounded-full text-[10px] font-bold">
          {loading ? '…' : `${total} Total`}
        </span>
      </div>

      <div className="space-y-4">
        {loading ? (
          <>
            <SkeletonAlert />
            <SkeletonAlert />
            <SkeletonAlert />
          </>
        ) : claims.length === 0 ? (
          <div className="p-4 text-center text-on-surface-variant text-label-md">
            No hay alertas críticas activas.
          </div>
        ) : (
          claims.slice(0, 4).map((claim, i) => (
            <AlertCard key={claim.id_siniestro} claim={claim} isCritical={i === 0} />
          ))
        )}
      </div>

      {/* Active Investigators — static (no endpoint yet) */}
      <div className="mt-8 pt-8 border-t border-outline-variant">
        <h3 className="text-label-sm text-on-surface-variant uppercase tracking-wider font-bold mb-4">
          INVESTIGADORES ACTIVOS
        </h3>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center font-bold text-on-surface-variant">
              AM
            </div>
            <div>
              <div className="text-label-md font-bold text-on-surface">Ana Martínez</div>
              <div className="text-label-sm text-green-600">Online</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center font-bold text-on-surface-variant">
              RH
            </div>
            <div>
              <div className="text-label-md font-bold text-on-surface">Roberto Hierro</div>
              <div className="text-label-sm text-on-surface-variant">Offline</div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
