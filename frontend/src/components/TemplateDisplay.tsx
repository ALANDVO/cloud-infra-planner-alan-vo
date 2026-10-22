// frontend/src/components/TemplateDisplay.tsx
// Template display with syntax highlighting and actions

import { Copy, Download, ExternalLink, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Generation, Provider } from '../api/types';
import clsx from 'clsx';
import '../styles/components.css';

interface TemplateDisplayProps {
  generation: Generation;
  onValidate?: () => void;
  onEstimate?: () => void;
  onExport?: () => void;
}

const LANGUAGE_MAP: Record<Provider, string> = {
  terraform: 'hcl',
  cloudformation: 'yaml',
  arm: 'json',
};

const FILE_EXTENSION: Record<Provider, string> = {
  terraform: 'tf',
  cloudformation: 'yaml',
  arm: 'json',
};

export function TemplateDisplay({ generation, onValidate, onEstimate, onExport }: TemplateDisplayProps) {
  const language = LANGUAGE_MAP[generation.provider] || 'text';
  const extension = FILE_EXTENSION[generation.provider] || 'txt';
  const filename = `infra-${generation.id}.${extension}`;

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(generation.template || '');
    } catch {
      // fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = generation.template || '';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
  };

  const downloadTemplate = () => {
    const blob = new Blob([generation.template || ''], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getStatusIcon = () => {
    switch (generation.status) {
      case 'completed':
        return <CheckCircle size={20} className="status-icon status-success" />;
      case 'failed':
        return <XCircle size={20} className="status-icon status-error" />;
      default:
        return <AlertTriangle size={20} className="status-icon status-warning" />;
    }
  };

  if (!generation.template) {
    return (
      <div className="template-display empty">
        <div className="empty-state">
          <XCircle size={48} />
          <h3>No Template</h3>
          <p>This generation did not produce a template.</p>
          {generation.error_message && (
            <p className="error-message">{generation.error_message}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="template-display">
      <div className="template-header">
        <div className="template-meta">
          <span className={clsx('badge badge-provider', generation.provider)}>
            {generation.provider.toUpperCase()}
          </span>
          <span className={clsx('badge badge-target', generation.target)}>
            {generation.target.toUpperCase()}
          </span>
          <span className={clsx('badge badge-status', generation.status)}>
            {getStatusIcon()}
            {generation.status.charAt(0).toUpperCase() + generation.status.slice(1)}
          </span>
        </div>
        <div className="template-actions">
          {onValidate && (
            <button className="btn btn-secondary btn-sm" onClick={onValidate}>
              Validate
            </button>
          )}
          {onEstimate && (
            <button className="btn btn-secondary btn-sm" onClick={onEstimate}>
              Estimate Cost
            </button>
          )}
          {onExport && (
            <button className="btn btn-secondary btn-sm" onClick={onExport}>
              <ExternalLink size={16} /> Export
            </button>
          )}
          <button className="btn btn-primary btn-sm" onClick={copyToClipboard} title="Copy to clipboard">
            <Copy size={16} />
          </button>
          <button className="btn btn-primary btn-sm" onClick={downloadTemplate} title="Download template">
            <Download size={16} />
          </button>
        </div>
      </div>

      <div className="template-content">
        <SyntaxHighlighter
          language={language}
          style={atomDark}
          customStyle={{
            fontSize: '13px',
            lineHeight: '1.5',
            maxHeight: '600px',
            overflow: 'auto',
          }}
          showLineNumbers
          wrapLines
        >
          {generation.template}
        </SyntaxHighlighter>
      </div>

      {generation.validation_notes && (
        <details className="validation-notes">
          <summary>Validation Notes</summary>
          <pre className="validation-notes-content">{generation.validation_notes}</pre>
        </details>
      )}

      {generation.components.length > 0 && (
        <details className="components-list">
          <summary>Detected Components ({generation.components.length})</summary>
          <ul className="components-tags">
            {generation.components.map((comp, i) => (
              <li key={i} className="component-tag">{comp}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="template-footer">
        <span className="generation-info">
          Generated: {new Date(generation.created_at).toLocaleString()}
        </span>
        {generation.completed_at && (
          <span className="generation-info">
            Completed: {new Date(generation.completed_at).toLocaleString()}
          </span>
        )}
        {generation.cost_estimate_usd !== undefined && (
          <span className="generation-info cost-info">
            Est. Monthly Cost: ${generation.cost_estimate_usd.toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
}