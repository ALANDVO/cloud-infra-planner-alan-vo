// frontend/src/components/GenerateForm.tsx
// Generation form with validation and submission

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Loader2, AlertCircle, Info } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { api } from '../api/client';
import type { GenerateRequest, Provider, Target } from '../api/types';
import clsx from 'clsx';
import '../styles/components.css';

const PROVIDERS: { value: Provider; label: string }[] = [
  { value: 'terraform', label: 'Terraform (HCL)' },
  { value: 'cloudformation', label: 'CloudFormation (YAML)' },
  { value: 'arm', label: 'ARM Template (JSON)' },
];

const TARGETS: { value: Target; label: string }[] = [
  { value: 'aws', label: 'AWS' },
  { value: 'gcp', label: 'GCP' },
  { value: 'azure', label: 'Azure' },
];

const EXAMPLE_DESCRIPTIONS = [
  'A highly available 3-tier web app with ALB, RDS Postgres, ElastiCache Redis, and S3 on AWS',
  'Serverless API with Lambda, API Gateway, DynamoDB, and S3',
  'Kubernetes cluster (EKS) with managed node groups, ALB, and EBS volumes',
  'GCP Cloud Run service with Cloud SQL PostgreSQL and Cloud Storage',
  'Azure AKS cluster with Azure Database for PostgreSQL and Storage Account',
];

export function GenerateForm() {
  const { isOperator, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [description, setDescription] = useState('');
  const [provider, setProvider] = useState<Provider>('terraform');
  const [target, setTarget] = useState<Target>('aws');
  const [useLlm, setUseLlm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [generatedId, setGeneratedId] = useState<number | null>(null);

  const validate = () => {
    if (!description.trim()) {
      setError('Description is required');
      return false;
    }
    if (description.trim().length < 10) {
      setError('Description must be at least 10 characters');
      return false;
    }
    if (description.length > 5000) {
      setError('Description must not exceed 5000 characters');
      return false;
    }
    setError(null);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const payload: GenerateRequest = {
        description: description.trim(),
        provider,
        target,
        use_llm: useLlm,
      };
      const result = await api.generate(payload);
      setGeneratedId(result.id);
      setSuccess(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Generation failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewResult = () => {
    if (generatedId) {
      navigate(`/history/${generatedId}`);
    }
  };

  if (!isOperator && !authLoading) {
    return (
      <div className="generate-form-container">
        <div className="empty-state">
          <Info size={48} />
          <h2>Operator Access Required</h2>
          <p>You need operator or admin role to generate templates.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="generate-form-container">
      <div className="page-header">
        <h1>Generate IaC Template</h1>
        <p className="page-subtitle">
          Describe your infrastructure in natural language. The deterministic engine renders valid
          Terraform, CloudFormation, or ARM templates with optional LLM advisory.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="generate-form" noValidate>
        <div className="form-group">
          <label htmlFor="description" className="form-label">
            Infrastructure Description <span className="required">*</span>
          </label>
          <textarea
            id="description"
            className={clsx('form-textarea', { 'form-textarea-error': !!error })}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g., A highly available 3-tier web app with ALB, RDS Postgres, Redis cache, and S3 on AWS"
            rows={5}
            maxLength={5000}
            aria-describedby="description-hint"
          />
          <div id="description-hint" className="form-hint">
            {description.length}/5000 characters — minimum 10 characters
          </div>
          {error && (
            <div className="form-error" role="alert">
              <AlertCircle size={16} /> {error}
            </div>
          )}
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="provider" className="form-label">Provider</label>
            <select
              id="provider"
              className="form-select"
              value={provider}
              onChange={(e) => setProvider(e.target.value as Provider)}
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="target" className="form-label">Cloud Target</label>
            <select
              id="target"
              className="form-select"
              value={target}
              onChange={(e) => setTarget(e.target.value as Target)}
            >
              {TARGETS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group form-checkbox">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            <span className="checkbox-text">Use LLM advisory (opt-in, requires configured API key)</span>
          </label>
          <p className="form-hint">
            LLM suggestions are grounded in the allowed component set and validated; the deterministic
            engine always produces the final template.
          </p>
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className={clsx('btn btn-primary', { 'btn-loading': loading })}
            disabled={loading || authLoading}
          >
            {loading ? (
              <>
                <Loader2 size={18} className="btn-spinner" />
                Generating...
              </>
            ) : (
              <>
                <Send size={18} />
                Generate Template
              </>
            )}
          </button>
        </div>
      </form>

      {success && generatedId && (
        <div className="success-banner" role="status">
          <div className="success-content">
            <Info size={24} />
            <div>
              <h3>Template Generated Successfully</h3>
              <p>Generation ID: {generatedId}</p>
            </div>
          </div>
          <button className="btn btn-secondary" onClick={handleViewResult}>
            View Result
          </button>
        </div>
      )}

      <details className="examples-section">
        <summary>Example Descriptions</summary>
        <ul className="examples-list">
          {EXAMPLE_DESCRIPTIONS.map((ex, i) => (
            <li key={i}>
              <button
                type="button"
                className="example-btn"
                onClick={() => setDescription(ex)}
              >
                {ex}
              </button>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}