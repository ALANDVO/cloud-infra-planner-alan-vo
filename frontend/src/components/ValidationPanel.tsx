// frontend/src/components/ValidationPanel.tsx
// Validation results display panel

import { CheckCircle, AlertTriangle, Info, XCircle, AlertCircle } from 'lucide-react';
import type { ValidateResponse, ValidationIssue, Severity } from '../api/types';
import clsx from 'clsx';
import '../styles/components.css';

interface ValidationPanelProps {
  validation?: ValidateResponse;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

const SEVERITY_ICONS: Record<Severity, React.ReactNode> = {
  error: <XCircle size={16} className="severity-icon severity-error" />,
  warning: <AlertTriangle size={16} className="severity-icon severity-warning" />,
  info: <Info size={16} className="severity-icon severity-info" />,
};

const SEVERITY_LABELS: Record<Severity, string> = {
  error: 'Error',
  warning: 'Warning',
  info: 'Info',
};

export function ValidationPanel({ validation, loading, error, onRefresh }: ValidationPanelProps) {
  if (loading) {
    return (
      <div className="validation-panel loading">
        <div className="skeleton skeleton-title"></div>
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="validation-panel error">
        <div className="error-state">
          <AlertCircle size={32} />
          <h3>Validation Failed</h3>
          <p>{error}</p>
          {onRefresh && (
            <button className="btn btn-secondary btn-sm" onClick={onRefresh}>
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!validation) {
    return (
      <div className="validation-panel empty">
        <div className="empty-state">
          <CheckCircle size={48} />
          <h3>Not Validated</h3>
          <p>Run validation to check template quality.</p>
        </div>
      </div>
    );
  }

  const { valid, issues, summary } = validation;
  const errors = issues.filter((i) => i.severity === 'error').length;
  const warnings = issues.filter((i) => i.severity === 'warning').length;
  const infos = issues.filter((i) => i.severity === 'info').length;

  return (
    <div className="validation-panel">
      <div className="validation-header">
        <h2>
          {valid ? (
            <CheckCircle size={20} className="status-success" />
          ) : (
            <XCircle size={20} className="status-error" />
          )}
          Validation Result
        </h2>
        <div className="validation-status">
          <span className={clsx('status-badge', valid ? 'status-valid' : 'status-invalid')}>
            {valid ? 'Valid' : 'Invalid'}
          </span>
        </div>
      </div>

      <div className="validation-summary">
        <p>{summary}</p>
        <div className="issue-counts">
          {errors > 0 && (
            <span className="issue-count issue-count-error">
              <XCircle size={12} /> {errors} error{errors !== 1 ? 's' : ''}
            </span>
          )}
          {warnings > 0 && (
            <span className="issue-count issue-count-warning">
              <AlertTriangle size={12} /> {warnings} warning{warnings !== 1 ? 's' : ''}
            </span>
          )}
          {infos > 0 && (
            <span className="issue-count issue-count-info">
              <Info size={12} /> {infos} info
            </span>
          )}
        </div>
      </div>

      {issues.length > 0 && (
        <div className="validation-issues">
          <h3>Issues</h3>
          <div className="issues-list" role="list">
            {issues.map((issue: ValidationIssue, i) => (
              <article key={i} className={clsx('issue-card', `issue-${issue.severity}`)}>
                <div className="issue-header">
                  <span className="issue-severity">
                    {SEVERITY_ICONS[issue.severity]}
                    {SEVERITY_LABELS[issue.severity]}
                  </span>
                  {issue.rule && (
                    <span className="issue-rule">{issue.rule}</span>
                  )}
                </div>
                <p className="issue-message">{issue.message}</p>
                {(issue.line || issue.column) && (
                  <div className="issue-location">
                    {issue.line && <span>Line {issue.line}</span>}
                    {issue.column && <span>Column {issue.column}</span>}
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}