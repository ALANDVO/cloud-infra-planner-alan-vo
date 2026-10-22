// frontend/src/components/Settings.tsx
// User settings page

import { useAuth } from '../hooks/useAuth';
import { User, Shield, Key, Bell, Palette, CheckCircle } from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';
import '../styles/components.css';

export function Settings() {
  const { user } = useAuth();
  const [saved, _setSaved] = useState(false);

  if (!user) {
    return (
      <div className="settings-page">
        <div className="empty-state">
          <User size={48} />
          <h3>Not Signed In</h3>
          <p>Please sign in to access settings.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="page-header">
        <h1>Settings</h1>
        <p className="page-subtitle">Manage your account and preferences</p>
      </div>

      <div className="settings-grid">
        <section className="settings-section">
          <h2>
            <User size={20} /> Profile
          </h2>
          <dl className="profile-info">
            <div>
              <dt>Email</dt>
              <dd>{user.email}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>
                <span className={clsx('badge', user.role)}>{user.role}</span>
              </dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{user.is_active ? 'Active' : 'Inactive'}</dd>
            </div>
          </dl>
        </section>

        <section className="settings-section">
          <h2>
            <Shield size={20} /> Permissions
          </h2>
          <ul className="permission-list">
            <li>
              <span>View generations</span>
              <span className="permission-badge granted">Granted</span>
            </li>
            <li>
              <span>Generate templates</span>
              <span className={clsx('permission-badge', user.role === 'operator' || user.role === 'admin' ? 'granted' : 'denied')}>
                {user.role === 'operator' || user.role === 'admin' ? 'Granted' : 'Requires Operator'}
              </span>
            </li>
            <li>
              <span>Delete generations</span>
              <span className={clsx('permission-badge', user.role === 'operator' || user.role === 'admin' ? 'granted' : 'denied')}>
                {user.role === 'operator' || user.role === 'admin' ? 'Granted' : 'Requires Operator'}
              </span>
            </li>
            <li>
              <span>Admin panel</span>
              <span className={clsx('permission-badge', user.role === 'admin' ? 'granted' : 'denied')}>
                {user.role === 'admin' ? 'Granted' : 'Requires Admin'}
              </span>
            </li>
          </ul>
        </section>

        <section className="settings-section">
          <h2>
            <Key size={20} /> Security
          </h2>
          <div className="security-options">
            <button className="btn btn-secondary" disabled>
              Change Password
            </button>
            <button className="btn btn-secondary" disabled>
              Manage Sessions
            </button>
            <button className="btn btn-secondary" disabled>
              Two-Factor Authentication
            </button>
          </div>
          <p className="settings-note">Security features require Keycloak SSO integration (planned).</p>
        </section>

        <section className="settings-section">
          <h2>
            <Bell size={20} /> Notifications
          </h2>
          <div className="notification-options">
            <label className="toggle-label">
              <input type="checkbox" defaultChecked />
              <span>Generation completion</span>
            </label>
            <label className="toggle-label">
              <input type="checkbox" defaultChecked />
              <span>Validation failures</span>
            </label>
            <label className="toggle-label">
              <input type="checkbox" />
              <span>Cost estimate alerts</span>
            </label>
          </div>
        </section>

        <section className="settings-section">
          <h2>
            <Palette size={20} /> Appearance
          </h2>
          <div className="appearance-options">
            <label className="radio-label">
              <input type="radio" name="theme" defaultChecked />
              <span>System</span>
            </label>
            <label className="radio-label">
              <input type="radio" name="theme" />
              <span>Light</span>
            </label>
            <label className="radio-label">
              <input type="radio" name="theme" />
              <span>Dark</span>
            </label>
          </div>
        </section>
      </div>

      {saved && (
        <div className="save-toast" role="status">
          <CheckCircle size={20} />
          <span>Settings saved</span>
        </div>
      )}
    </div>
  );
}