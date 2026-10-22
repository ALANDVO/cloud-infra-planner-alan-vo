// frontend/src/components/GenerationDetail.tsx
// Detailed view of a single generation with validation and cost

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle } from 'lucide-react';
import { useGeneration } from '../hooks/useGenerations';
import { TemplateDisplay } from './TemplateDisplay';
import { CostPanel } from './CostPanel';
import { ValidationPanel } from './ValidationPanel';
import { api } from '../api/client';
import type { EstimateResponse, ValidateResponse } from '../api/types';
import clsx from 'clsx';
import '../styles/components.css';

export function GenerationDetail() {
  const { id } = useParams<{ id: string }>();
  const generationId = id ? parseInt(id, 10) : null;
  const { generation, loading, error } = useGeneration(generationId);

  const [validation, setValidation] = useState<ValidateResponse | undefined>(undefined);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [estimate, setEstimate] = useState<EstimateResponse | undefined>(undefined);
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [estimateError, setEstimateError] = useState<string | null>(null);

  const handleValidate = async () => {
    if (!generation?.template) return;
    setValidationLoading(true);
    setValidationError(null);
    try {
      const result = await api.validate({
        template: generation.template,
        provider: generation.provider,
        target: generation.target,
      });
      setValidation(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Validation failed';
      setValidationError(message);
    } finally {
      setValidationLoading(false);
    }
  };

  const handleEstimate = async () => {
    if (!generation?.template) return;
    setEstimateLoading(true);
    setEstimateError(null);
    try {
      const result = await api.estimate({
        template: generation.template,
        target: generation.target,
        regions: 1,
      });
      setEstimate(result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Estimation failed';
      setEstimateError(message);
    } finally {
      setEstimateLoading(false);
    }
  };

  const handleExport = () => {
    if (!generation?.template) return;
    const blob = new Blob([generation.template], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ext = generation.provider === 'terraform' ? 'tf' : generation.provider === 'cloudformation' ? 'yaml' : 'json';
    a.download = `infra-${generation.id}.${ext}`;
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="generation-detail loading">
        <div className="skeleton skeleton-title"></div>
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
      </div>
    );
  }

  if (error || !generation) {
    return (
      <div className="generation-detail error">
        <div className="error-state">
          <AlertTriangle size={32} />
          <h3>Generation Not Found</h3>
          <p>{error || 'Invalid generation ID'}</p>
          <Link to="/history" className="btn btn-primary">
            <ArrowLeft size={16} /> Back to History
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="generation-detail">
      <div className="detail-header">
        <Link to="/history" className="btn btn-secondary btn-sm back-link">
          <ArrowLeft size={16} /> Back to History
        </Link>
        <div className="detail-title">
          <h1>Generation #{generation.id}</h1>
          <p className="detail-description">{generation.description}</p>
        </div>
      </div>

      <div className="detail-grid">
        <section className="detail-main">
          <TemplateDisplay
            generation={generation}
            onValidate={handleValidate}
            onEstimate={handleEstimate}
            onExport={handleExport}
          />
        </section>

        <aside className="detail-sidebar">
          <div className="sidebar-card">
            <h3>Metadata</h3>
            <dl className="metadata-list">
              <div>
                <dt>Provider</dt>
                <dd>
                  <span className={clsx('badge badge-provider', generation.provider)}>
                    {generation.provider.toUpperCase()}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Target</dt>
                <dd>
                  <span className={clsx('badge badge-target', generation.target)}>
                    {generation.target.toUpperCase()}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <span className={clsx('badge badge-status', generation.status)}>
                    {generation.status.charAt(0).toUpperCase() + generation.status.slice(1)}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{new Date(generation.created_at).toLocaleString()}</dd>
              </div>
              {generation.completed_at && (
                <div>
                  <dt>Completed</dt>
                  <dd>{new Date(generation.completed_at).toLocaleString()}</dd>
                </div>
              )}
              {generation.cost_estimate_usd !== undefined && (
                <div>
                  <dt>Est. Monthly Cost</dt>
                  <dd className="cost-highlight">${generation.cost_estimate_usd.toLocaleString()}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="sidebar-card">
            <CostPanel
              estimate={estimate}
              loading={estimateLoading}
              error={estimateError}
              onRefresh={handleEstimate}
            />
          </div>

          <div className="sidebar-card">
            <ValidationPanel
              validation={validation}
              loading={validationLoading}
              error={validationError}
              onRefresh={handleValidate}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}