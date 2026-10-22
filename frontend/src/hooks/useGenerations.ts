// frontend/src/hooks/useGenerations.ts
// Generations data fetching and mutation

import { useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';
import type { Generation, GenerationListResponse, GenerateRequest } from '../api/types';

export function useGenerations() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const fetchGenerations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response: GenerationListResponse = await api.listGenerations({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
      });
      setGenerations(response.items);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch generations';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter]);

  useEffect(() => {
    fetchGenerations();
  }, [fetchGenerations]);

  const generate = async (payload: GenerateRequest): Promise<Generation> => {
    setError(null);
    try {
      const result = await api.generate(payload);
      await fetchGenerations(); // refresh list
      return result;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Generation failed';
      setError(message);
      throw err;
    }
  };

  const deleteGeneration = async (id: number): Promise<void> => {
    setError(null);
    try {
      await api.deleteGeneration(id);
      await fetchGenerations();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Delete failed';
      setError(message);
      throw err;
    }
  };

  const refetch = useCallback(() => {
    fetchGenerations();
  }, [fetchGenerations]);

  return {
    generations,
    total,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    loading,
    error,
    statusFilter,
    setStatusFilter,
    generate,
    deleteGeneration,
    refetch,
  };
}

export function useGeneration(id: number | null) {
  const [generation, setGeneration] = useState<Generation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.getGeneration(id)
      .then((data) => {
        if (!cancelled) setGeneration(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to fetch generation';
          setError(message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  return { generation, loading, error };
}