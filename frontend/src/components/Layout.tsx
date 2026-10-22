// frontend/src/components/Layout.tsx
// Main layout with navigation

import { useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { Menu, X, LogOut, Settings, History, Plus, ChevronDown } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import clsx from 'clsx';
import '../styles/layout.css';

export function Layout() {
  const { user, logout, isAuthenticated } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const navItems = [
    { path: '/generate', label: 'Generate', icon: Plus },
    { path: '/history', label: 'History', icon: History },
  ];

  const handleLogout = async () => {
    await logout();
    setUserMenuOpen(false);
  };

  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          <Link to="/generate" className="logo">
            <span className="logo-icon">☁</span>
            <span className="logo-text">cloud-infra-planner</span>
          </Link>
        </div>

        <nav className={clsx('nav', { 'nav-open': mobileMenuOpen })}>
          <ul className="nav-list">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    clsx('nav-link', { 'nav-link-active': isActive })
                  }
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <item.icon size={18} />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="header-right">
          {isAuthenticated ? (
            <div className="user-menu">
              <button
                className="user-button"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                aria-expanded={userMenuOpen}
              >
                <span className="user-avatar">{user?.email?.charAt(0).toUpperCase()}</span>
                <span className="user-name">{user?.email}</span>
                <ChevronDown size={16} />
              </button>

              {userMenuOpen && (
                <div className="user-dropdown">
                  <div className="dropdown-header">
                    <span className="dropdown-email">{user?.email}</span>
                    <span className={clsx('dropdown-role', user?.role)}>{user?.role}</span>
                  </div>
                  <NavLink to="/settings" className="dropdown-item" onClick={() => setUserMenuOpen(false)}>
                    <Settings size={16} /> Settings
                  </NavLink>
                  <button className="dropdown-item dropdown-item-danger" onClick={handleLogout}>
                    <LogOut size={16} /> Logout
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link to="/login" className="btn btn-primary">
              Login
            </Link>
          )}

          <button
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </header>

      <main className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <p>cloud-infra-planner-alan-vo &copy; Alan Vo &#60;alanvo@gmail.com&#62;</p>
      </footer>
    </div>
  );
}