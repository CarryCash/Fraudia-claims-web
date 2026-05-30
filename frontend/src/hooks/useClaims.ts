// frontend/src/hooks/useClaims.ts
/**
 * React hooks that wrap the API service calls with loading / error state.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  fetchClaims,
  fetchClaim,
  type Claim,
  type ClaimsListResponse,
} from '../services/api';

// ── useClaims ─────────────────────────────────────────────────────────────────

interface UseClaimsOptions {
  page?: number;
  limit?: number;
  color?: 'rojo' | 'amarillo' | 'verde';
}

interface UseClaimsResult {
  claims: Claim[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
  addClaim: (claim: Claim) => void;
  removeClaim: (id: number | string) => void;
}

export function useClaims(options: UseClaimsOptions = {}): UseClaimsResult {
  const { page = 1, limit = 20, color } = options;

  const [data, setData] = useState<ClaimsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchClaims(page, limit, color)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [page, limit, color, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  // Listen for cross-component deletion events and auto-refetch
  useEffect(() => {
    const handler = () => setTick((t) => t + 1);
    window.addEventListener('claim-deleted', handler);
    return () => window.removeEventListener('claim-deleted', handler);
  }, []);

  const addClaim = useCallback((claim: Claim) => {
    setData((prev) => {
      const claimId = String(claim.id_siniestro);
      if (prev) {
        const exists = prev.data.some((c) => String(c.id_siniestro) === claimId);
        if (exists) return prev;
        return {
          ...prev,
          total: prev.total + 1,
          data: [claim, ...prev.data],
        };
      }
      return {
        total: 1,
        page,
        limit,
        data: [claim],
      };
    });
  }, [limit, page]);

  const removeClaim = useCallback((id: number | string) => {
    const idStr = String(id);
    setData((prev) => {
      if (!prev) return prev;
      const filtered = prev.data.filter((c) => String(c.id_siniestro) !== idStr);
      return { ...prev, total: Math.max(0, prev.total - 1), data: filtered };
    });
  }, []);

  return {
    claims: data?.data ?? [],
    total: data?.total ?? 0,
    loading,
    error,
    refetch,
    addClaim,
    removeClaim,
  };
}

// ── useClaim (single) ─────────────────────────────────────────────────────────

interface UseClaimResult {
  claim: Claim | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useClaim(id: number | string | null): UseClaimResult {
  const [claim, setClaim] = useState<Claim | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (id === null || id === undefined || id === '') return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchClaim(id)
      .then((res) => {
        if (!cancelled) {
          setClaim(res);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id, tick]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return { claim, loading, error, refetch };
}
