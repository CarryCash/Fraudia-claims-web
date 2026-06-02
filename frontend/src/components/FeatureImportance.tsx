import { useState } from 'react';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

interface Factor {
  name: string;
  feature: string;
  value: number;
  contribution: number;
  impact: 'high' | 'medium' | 'low';
  threshold: number;
}

interface SectorComparison {
  this_claim: Record<string, number>;
  sector_avg: Record<string, number>;
  percentile: number;
  percentile_description: string;
}

interface RiskBreakdown {
  score: number;
  factors: string[];
}

interface FeatureImportanceProps {
  topFactors: Factor[];
  sectorComparison: SectorComparison;
  riskFactorsBreakdown: Record<string, RiskBreakdown>;
  originalScore: number;
  finalColor: 'rojo' | 'amarillo' | 'verde';
  claimId: string;
  onWhatIfChange?: (modifications: Record<string, number>) => void;
}

export default function FeatureImportance({
  topFactors,
  sectorComparison,
  riskFactorsBreakdown,
  originalScore,
  finalColor,
  claimId,
  onWhatIfChange,
}: FeatureImportanceProps) {
  const [whatIfModifications, setWhatIfModifications] = useState<Record<string, number>>({});
  const [expandedRiskCategory, setExpandedRiskCategory] = useState<string | null>(null);

  const handleSliderChange = (feature: string, value: number) => {
    const newMods = { ...whatIfModifications, [feature]: value };
    setWhatIfModifications(newMods);
    if (onWhatIfChange) {
      onWhatIfChange(newMods);
    }
  };

  const getRiskCategoryColor = (category: string): string => {
    const breakdownItem = riskFactorsBreakdown[category];
    if (!breakdownItem) return 'text-on-surface-variant';
    const score = breakdownItem.score;
    if (score > 20) return 'text-error';
    if (score > 10) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getRiskCategoryBg = (category: string): string => {
    const breakdownItem = riskFactorsBreakdown[category];
    if (!breakdownItem) return 'bg-surface-container-low';
    const score = breakdownItem.score;
    if (score > 20) return 'bg-error-container';
    if (score > 10) return 'bg-yellow-50';
    return 'bg-green-50';
  };

  const impactColor = (impact: string): string => {
    if (impact === 'high') return 'text-error';
    if (impact === 'medium') return 'text-yellow-600';
    return 'text-green-600';
  };

  const impactBg = (impact: string): string => {
    if (impact === 'high') return 'bg-error-container/30';
    if (impact === 'medium') return 'bg-yellow-100/30';
    return 'bg-green-100/30';
  };

  return (
    <div className="space-y-6 p-6 bg-surface-container-lowest rounded-2xl border border-outline-variant">
      {/* Title */}
      <div className="flex items-center gap-2">
        <TrendingUp className="text-primary" size={24} />
        <div>
          <h3 className="font-display text-title-lg font-bold text-on-surface">
            Explicabilidad de Score
          </h3>
          <p className="text-body-sm text-on-surface-variant">
            Entiende qué factores determinan el riesgo
          </p>
        </div>
      </div>

      {/* Top 5 Factors */}
      <div className="space-y-4">
        <h4 className="font-label-lg font-bold text-on-surface flex items-center gap-2">
          <span className="w-1 h-6 bg-primary rounded-full" />
          Top 5 Factores Contribuyentes
        </h4>
        <div className="space-y-3">
          {topFactors.map((factor, idx) => (
            <div key={factor.feature} className={`p-4 rounded-lg border ${impactBg(factor.impact)} border-outline-variant/50`}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className={`font-bold ${impactColor(factor.impact)}`}>
                    #{idx + 1} {factor.name}
                  </p>
                  <p className="text-body-xs text-on-surface-variant mt-1">
                    Valor actual: <span className="font-bold text-on-surface">{factor.value.toFixed(2)}</span>
                    {' '}
                    (umbral: {factor.threshold})
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-[20px] font-bold ${impactColor(factor.impact)}`}>
                    {factor.contribution.toFixed(1)}%
                  </p>
                  <p className="text-body-xs text-on-surface-variant">
                    del riesgo
                  </p>
                </div>
              </div>
              <div className="w-full h-2 bg-surface-container-high rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    factor.impact === 'high'
                      ? 'bg-error'
                      : factor.impact === 'medium'
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(factor.contribution * 2, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sector Comparison */}
      <div className="space-y-3">
        <h4 className="font-label-lg font-bold text-on-surface flex items-center gap-2">
          <span className="w-1 h-6 bg-primary rounded-full" />
          Comparativa vs. Sector
        </h4>
        <div className="p-4 rounded-lg bg-surface border border-outline-variant">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-body-sm text-on-surface-variant">Percentil de Riesgo</p>
              <p className="text-display-xs font-bold text-on-surface mt-1">
                {sectorComparison.percentile}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-body-sm text-on-surface-variant">
                {sectorComparison.percentile_description}
              </p>
              <div className="mt-2 flex items-center gap-1 text-error">
                <TrendingUp size={16} />
                <span className="text-body-sm font-bold">Mayor riesgo que promedio</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-body-sm">
            {Object.entries(sectorComparison.this_claim).map(([key, value]) => {
              const sectorValue = sectorComparison.sector_avg[key as keyof typeof sectorComparison.sector_avg] || 0;
              const diff = (value as number) - sectorValue;
              const isDifferent = Math.abs(diff) > sectorValue * 0.1; // 10% threshold

              return (
                <div
                  key={key}
                  className={`p-2 rounded border ${isDifferent ? 'bg-error-container/10 border-error/30' : 'bg-surface-container-low border-outline-variant/30'}`}
                >
                  <p className="text-on-surface-variant text-[11px] uppercase tracking-wider font-bold mb-1">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="font-bold text-on-surface">
                    {typeof value === 'number' && value > 100 ? value.toFixed(0) : (value as number).toFixed(2)}
                  </p>
                  <p className="text-[10px] text-on-surface-variant">
                    sector: {sectorValue.toFixed(2)}
                    {isDifferent ? (
                      <span className={diff > 0 ? 'text-error font-bold' : 'text-green-600 font-bold'}>
                        {' '}({diff > 0 ? '+' : ''}{diff.toFixed(2)})
                      </span>
                    ) : null}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Risk Factors Breakdown */}
      <div className="space-y-3">
        <h4 className="font-label-lg font-bold text-on-surface flex items-center gap-2">
          <span className="w-1 h-6 bg-primary rounded-full" />
          Desglose de Riesgos
        </h4>
        <div className="space-y-2">
          {Object.entries(riskFactorsBreakdown).map(([category, breakdown]) => (
            <button
              key={category}
              onClick={() => setExpandedRiskCategory(expandedRiskCategory === category ? null : category)}
              className={`w-full p-3 rounded-lg border text-left transition-all ${getRiskCategoryBg(category)} border-outline-variant/50 hover:border-outline-variant`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className={`font-bold ${getRiskCategoryColor(category)}`}>
                    {category.replace(/_/g, ' ').toUpperCase()}
                  </p>
                  <p className="text-body-xs text-on-surface-variant mt-1">
                    {breakdown.factors.length} factor{breakdown.factors.length !== 1 ? 'es' : ''} identificado{breakdown.factors.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-title-md font-bold ${getRiskCategoryColor(category)}`}>
                    {breakdown.score.toFixed(1)}%
                  </p>
                </div>
              </div>

              {expandedRiskCategory === category && breakdown.factors.length > 0 && (
                <div className="mt-3 pt-3 border-t border-outline-variant/30 space-y-2">
                  {breakdown.factors.map((factor) => (
                    <p key={factor} className="text-body-xs text-on-surface-variant flex items-center gap-2">
                      <span className="w-1 h-1 rounded-full bg-current" />
                      {factor}
                    </p>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* What-If Analysis */}
      <div className="space-y-4 p-4 bg-surface-container-high/30 rounded-lg border border-outline-variant/50">
        <h4 className="font-label-lg font-bold text-on-surface flex items-center gap-2">
          <AlertCircle size={20} className="text-primary" />
          ¿Qué pasaría si...? (Análisis Interactivo)
        </h4>
        <p className="text-body-sm text-on-surface-variant">
          Ajusta los valores para ver cómo cambiaría el score de riesgo
        </p>

        <div className="space-y-4">
          {topFactors.slice(0, 3).map((factor) => (
            <div key={factor.feature} className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="font-label-md font-bold text-on-surface text-sm">
                  {factor.name}
                </label>
                <span className="text-body-sm font-bold text-primary">
                  {(whatIfModifications[factor.feature] ?? factor.value).toFixed(0)}
                </span>
              </div>
              <input
                type="range"
                min={Math.max(0, factor.value - factor.threshold)}
                max={factor.value + factor.threshold}
                step={Math.max(1, factor.threshold / 10)}
                value={whatIfModifications[factor.feature] ?? factor.value}
                onChange={(e) => handleSliderChange(factor.feature, parseFloat(e.target.value))}
                className="w-full h-2 bg-surface-container-low rounded-full appearance-none cursor-pointer accent-primary"
              />
              <div className="flex justify-between text-[10px] text-on-surface-variant">
                <span>{Math.max(0, factor.value - factor.threshold).toFixed(0)}</span>
                <span className="font-bold">Original: {factor.value.toFixed(0)}</span>
                <span>{(factor.value + factor.threshold).toFixed(0)}</span>
              </div>
            </div>
          ))}
        </div>

        {Object.keys(whatIfModifications).length > 0 && (
          <div className="mt-4 p-3 rounded-lg bg-surface border border-outline-variant">
            <p className="text-body-xs text-on-surface-variant mb-2">
              💡 Simulación activa - Los cambios se reflejarán en tiempo real
            </p>
            <button
              onClick={() => setWhatIfModifications({})}
              className="text-body-xs font-bold text-primary hover:text-primary-dark transition-colors"
            >
              Resetear valores
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
