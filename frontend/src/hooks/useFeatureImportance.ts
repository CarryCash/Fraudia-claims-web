import { useState, useEffect } from 'react';
import { getFeatureImportance, calculateWhatIfScenario } from '../services/api';

type RiskColor = 'rojo' | 'amarillo' | 'verde';
type RiskLevel = 'high' | 'medium' | 'low';

interface Factor {
  name: string;
  feature: string;
  value: number;
  contribution: number;
  impact: RiskLevel;
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

interface FeatureImportanceData {
  id_siniestro: string;
  combined_score: number;
  final_color: RiskColor;
  top_factors: Factor[];
  sector_comparison: SectorComparison;
  risk_factors_breakdown: Record<string, RiskBreakdown>;
}

interface WhatIfResult {
  id_siniestro: string;
  original_score: number;
  original_color: RiskColor;
  new_score: number;
  new_color: RiskColor;
    importance: FeatureImportanceData;
}

export function useFeatureImportance(claimId: string | number | null) {
    const [data, setData] = useState<FeatureImportanceData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [whatIfResult, setWhatIfResult] = useState<WhatIfResult | null>(null);

    useEffect(() => {
        if (!claimId) {
            return;
        }

        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await getFeatureImportance(claimId);
                setData(result);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Error loading feature importance');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [claimId]);

    const runWhatIfScenario = async (modifications: Record<string, number>) => {
        if (!claimId) return;
        try {
            setError(null);
            const result = await calculateWhatIfScenario(claimId, modifications);
            setWhatIfResult(result);
            return result;
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : 'Error in what-if analysis';
            setError(errorMsg);
            throw err;
        }
    };

    return {
        data,
        loading,
        error,
        whatIfResult,
        runWhatIfScenario,
    };
}
