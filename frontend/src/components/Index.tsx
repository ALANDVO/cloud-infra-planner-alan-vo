// frontend/src/components/Index.tsx
// Dashboard index page

import { Link } from 'react-router-dom';
import { Plus, FileText, DollarSign, CheckCircle, Zap } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import clsx from 'clsx';
import '../styles/components.css';

const STAT_CARDS = [
  { icon: Plus, label: 'Generate', description: 'Create new IaC from description', href: '/generate', color: 'blue' },
  { icon: FileText, label: 'History', description: 'View past generations', href: '/history', color: 'green' },
  { icon: DollarSign, label: 'Estimate', description: 'Cost estimation from templates', href: '/generate', color: 'orange' },
  { icon: CheckCircle, label: 'Validate', description: 'Validate template quality', href: '/generate', color: 'purple' },
];

export function Index() {
  const { isAuthenticated, isOperator } = useAuth();

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p className="dashboard-subtitle">
          {isAuthenticated
            ? 'Welcome back! Choose an action to get started.'
            : 'Sign in to access the full IaC generation workflow.'}
        </p>
      </div>

      <div className="stats-grid">
        {STAT_CARDS.map((card) => (
          <Link key={card.label} to={card.href} className={clsx('stat-card', `stat-card-${card.color}`)}>
            <div className="stat-icon">
              <card.icon size={28} />
            </div>
            <div className="stat-content">
              <h3>{card.label}</h3>
              <p>{card.description}</p>
            </div>
          </Link>
        ))}
      </div>

      {!isAuthenticated && (
        <div className="demo-banner">
          <div className="demo-content">
            <Zap size={24} />
            <div>
              <h3>Try Demo Mode</h3>
              <p>No account? Use demo mode to instantly access the generator as an operator.</p>
            </div>
          </div>
          <Link to="/login" className="btn btn-primary">
            Go to Login
          </Link>
        </div>
      )}

      {isAuthenticated && !isOperator && (
        <div className="info-banner">
          <CheckCircle size={24} />
          <div>
            <h3>Viewer Access</h3>
            <p>You have read-only access. Operator role required for generation.</p>
          </div>
        </div>
      )}
    </div>
  );
}