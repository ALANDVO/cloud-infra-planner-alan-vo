// frontend/src/components/CostPanel.tsx
// Cost estimation display panel

import { DollarSign, MapPin, AlertCircle } from 'lucide-react';
import type { EstimateResponse, ResourceCost } from '../api/types';
import '../styles/components.css';

interface CostPanelProps {
  estimate?: EstimateResponse;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

const formatCost = (cost: number) => `$${cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function CostPanel({ estimate, loading, error, onRefresh }: CostPanelProps) {
  if (loading) {
    return (
      <div className="cost-panel loading">
        <div className="skeleton skeleton-title"></div>
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
        <div className="skeleton skeleton-row"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cost-panel error">
        <div className="error-state">
          <AlertCircle size={32} />
          <h3>Estimation Failed</h3>
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

  if (!estimate) {
    return (
      <div className="cost-panel empty">
        <div className="empty-state">
          <DollarSign size={48} />
          <h3>No Cost Estimate</h3>
          <p>Generate a template or run estimation to see costs.</p>
        </div>
      </div>
    );
  }

  const total = estimate.total_monthly_usd;
  const resources = estimate.resources;

  return (
    <div className="cost-panel">
      <div className="cost-header">
        <h2>
          <DollarSign size={20} />
          Monthly Cost Estimate
        </h2>
        <div className="cost-total">
          <span className="cost-total-label">Total</span>
          <span className="cost-total-value">{formatCost(total)}/mo</span>
        </div>
      </div>

      {estimate.assumptions.length > 0 && (
        <details className="cost-assumptions">
          <summary>Assumptions</summary>
          <ul>
            {estimate.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </details>
      )}

      {resources.length > 0 && (
        <div className="cost-breakdown">
          <h3>Breakdown by Resource</h3>
          <table className="cost-table" role="table">
            <thead>
              <tr>
                <th scope="col">Resource</th>
                <th scope="col">Type</th>
                <th scope="col">Region</th>
                <th scope="col" className="numeric">Monthly Cost</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((resource: ResourceCost, i) => (
                <tr key={i}>
                  <td>
                    <span className="resource-name">{resource.resource_name}</span>
                  </td>
                  <td>
                    <span className="resource-type">{resource.resource_type}</span>
                  </td>
                  <td>
                    <span className="resource-region">
                      <MapPin size={12} /> {resource.region}
                    </span>
                  </td>
                  <td className="numeric">
                    {formatCost(resource.monthly_cost_usd)}
                  </td>
                </tr>
              ))}
              <tr className="cost-table-total">
                <td colSpan={3}>Total</td>
                <td className="numeric">{formatCost(total)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {(estimate.breakdown_by_service && Object.keys(estimate.breakdown_by_service).length > 0) &&
        <details className="cost-breakdown">
          <summary>By Service</summary>
          <ul className="cost-service-list">
            {Object.entries(estimate.breakdown_by_service).map(([service, cost]) => (
              <li key={service}>
                <span>{service}</span>
                <span className="numeric">{formatCost(cost)}</span>
              </li>
            ))}
          </ul>
        </details>
      }

      {(estimate.breakdown_by_region && Object.keys(estimate.breakdown_by_region).length > 0) &&
        <details className="cost-breakdown">
          <summary>By Region</summary>
          <ul className="cost-service-list">
            {Object.entries(estimate.breakdown_by_region).map(([region, cost]) => (
              <li key={region}>
                <span>
                  <MapPin size={12} /> {region}
                </span>
                <span className="numeric">{formatCost(cost)}</span>
              </li>
            ))}
          </ul>
        </details>
      }
    </div>
  );
}