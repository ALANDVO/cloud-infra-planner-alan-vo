// frontend/src/components/HistoryList.tsx
// Generation history list with pagination and actions

import { Link, useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight, Trash2, Eye, Download, AlertTriangle } from 'lucide-react';
import { useGenerations } from '../hooks/useGenerations';
import { useAuth } from '../hooks/useAuth';
import type { GenerationStatus } from '../api/types';
import clsx from 'clsx';
import '../styles/components.css';

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Status' },
  { value: 'completed', label: 'Completed' },
  { value: 'pending', label: 'Pending' },
  { value: 'failed', label: 'Failed' },
];

const statusColors: Record<GenerationStatus, string> = {
  completed: 'status-completed',
  pending: 'status-pending',
  failed: 'status-failed',
};

export function HistoryList() {
  const { isOperator } = useAuth();
  const [search, setSearch] = useState('');
  const [_searchParams, setSearchParams] = useSearchParams();

  const {
    generations,
    total,
    page,
    setPage,
    totalPages,
    loading,
    error,
    statusFilter,
    setStatusFilter,
    deleteGeneration,
    refetch,
  } = useGenerations();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ page: '1', status: statusFilter, q: search });
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    setSearchParams({ page: '1', status: value, q: search });
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this generation? This cannot be undone.')) return;
    try {
      await deleteGeneration(id);
    } catch {
      // error handled in hook
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading && generations.length === 0) {
    return (
      <div className="history-list loading">
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history-list error">
        <div className="error-state">
          <AlertTriangle size={32} />
          <h3>Failed to Load History</h3>
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={refetch}>Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="history-list">
      <div className="history-header">
        <h1>Generation History</h1>
        <p className="history-subtitle">{total} total generation{total !== 1 ? 's' : ''}</p>
      </div>

      <div className="history-toolbar">
        <form onSubmit={handleSearch} className="search-form">
          <label htmlFor="search" className="visually-hidden">Search descriptions</label>
          <div className="search-input-wrapper">
            <Search size={18} />
            <input
              id="search"
              type="search"
              className="search-input"
              placeholder="Search descriptions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </form>

        <div className="filter-group">
          <label htmlFor="status-filter" className="visually-hidden">Filter by status</label>
          <select
            id="status-filter"
            className="filter-select"
            value={statusFilter}
            onChange={(e) => handleStatusChange(e.target.value)}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {generations.length === 0 ? (
        <div className="history-empty">
          <div className="empty-state">
            <AlertTriangle size={48} />
            <h3>No Generations Found</h3>
            <p>{search || statusFilter ? 'Try adjusting your filters.' : 'Generate your first template to get started.'}</p>
            <Link to="/generate" className="btn btn-primary">
              Generate Template
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div className="history-table-wrapper">
            <table className="history-table" role="table">
              <thead>
                <tr>
                  <th scope="col">Description</th>
                  <th scope="col">Provider</th>
                  <th scope="col">Target</th>
                  <th scope="col">Status</th>
                  <th scope="col">Cost</th>
                  <th scope="col">Created</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {generations.map((gen) => (
                  <tr key={gen.id}>
                    <td className="description-cell">
                      <Link to={`/history/${gen.id}`} className="description-link">
                        {gen.description.length > 80 ? gen.description.slice(0, 80) + '…' : gen.description}
                      </Link>
                    </td>
                    <td>
                      <span className={clsx('badge badge-provider', gen.provider)}>
                        {gen.provider.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className={clsx('badge badge-target', gen.target)}>
                        {gen.target.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className={clsx('badge badge-status', statusColors[gen.status])}>
                        {gen.status.charAt(0).toUpperCase() + gen.status.slice(1)}
                      </span>
                    </td>
                    <td>
                      {gen.cost_estimate_usd !== undefined ? (
                        <span className="cost-value">${gen.cost_estimate_usd.toLocaleString()}/mo</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="date-cell">{formatDate(gen.created_at)}</td>
                    <td>
                      <div className="action-menu">
                        <Link
                          to={`/history/${gen.id}`}
                          className="action-btn"
                          title="View details"
                          aria-label={`View generation ${gen.id}`}
                        >
                          <Eye size={16} />
                        </Link>
                        <button
                          className="action-btn"
                          onClick={() => {
                            const blob = new Blob([gen.template || ''], { type: 'text/plain' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `infra-${gen.id}.${gen.provider === 'terraform' ? 'tf' : gen.provider === 'cloudformation' ? 'yaml' : 'json'}`;
                            a.click();
                            URL.revokeObjectURL(url);
                          }}
                          title="Download template"
                          aria-label={`Download generation ${gen.id}`}
                          disabled={!gen.template}
                        >
                          <Download size={16} />
                        </button>
                        {isOperator && (
                          <button
                            className="action-btn action-btn-danger"
                            onClick={() => handleDelete(gen.id)}
                            title="Delete"
                            aria-label={`Delete generation ${gen.id}`}
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <nav className="pagination" aria-label="Pagination">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="pagination-info">
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages}
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}

import { useState } from 'react';