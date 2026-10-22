// frontend/src/components/LoginForm.tsx
// Login form with demo mode option

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, Loader2, AlertCircle, Zap } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import clsx from 'clsx';
import '../styles/components.css';

export function LoginForm() {
  const { login, demoLogin, error: authError, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('operator@example.com');
  const [password, setPassword] = useState('operator123');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate('/generate');
    } catch {
      setError(authError || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async () => {
    setError(null);
    setLoading(true);
    try {
      await demoLogin();
      navigate('/generate');
    } catch {
      setError('Demo setup failed. Ensure backend is running in development mode.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">☁</div>
          <h1>cloud-infra-planner</h1>
          <p>Sign in to generate IaC templates</p>
        </div>

        {(authError || error) && (
          <div className="login-error" role="alert">
            <AlertCircle size={16} />
            {authError || error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form" noValidate>
          <div className="form-group">
            <label htmlFor="email" className="form-label">Email</label>
            <div className="input-wrapper">
              <Mail size={18} />
              <input
                id="email"
                type="email"
                className={clsx('form-input', { 'form-input-error': !!error })}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@example.com"
                required
                autoComplete="email"
                disabled={loading || authLoading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">Password</label>
            <div className="input-wrapper">
              <Lock size={18} />
              <input
                id="password"
                type="password"
                className={clsx('form-input', { 'form-input-error': !!error })}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
                disabled={loading || authLoading}
              />
            </div>
          </div>

          <button
            type="submit"
            className={clsx('btn btn-primary btn-block', { 'btn-loading': loading || authLoading })}
            disabled={loading || authLoading}
          >
            {loading ? (
              <>
                <Loader2 size={18} className="btn-spinner" />
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        <div className="login-divider">
          <span>or</span>
        </div>

        <button
          type="button"
          className={clsx('btn btn-secondary btn-block', { 'btn-loading': loading || authLoading })}
          onClick={handleDemo}
          disabled={loading || authLoading}
        >
          {loading ? (
            <>
              <Loader2 size={18} className="btn-spinner" />
              Setting up demo...
            </>
          ) : (
            <>
              <Zap size={18} />
              Demo Mode (Auto-login as Operator)
            </>
          )}
        </button>

        <p className="login-hint">
          Demo mode creates a temporary operator user. Requires backend running with
          <code>DEMO_MODE=true</code> or <code>ENVIRONMENT=development</code>.
        </p>
      </div>
    </div>
  );
}