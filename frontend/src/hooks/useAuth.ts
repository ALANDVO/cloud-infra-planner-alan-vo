// frontend/src/hooks/useAuth.ts
// Authentication state management

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { UserResponse } from '../api/types';

export function useAuth() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    if (!api.isAuthenticated()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const userData = await api.getMe();
      setUser(userData);
      setError(null);
    } catch {
      setUser(null);
      api.clearAuth();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.loadStoredTokens();
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    setError(null);
    setLoading(true);
    try {
      await api.login({ email, password });
      await refreshUser();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const demoLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      await api.demoSetup();
      await refreshUser();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Demo setup failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  const hasRole = useCallback((requiredRole: UserResponse['role']) => {
    if (!user) return false;
    const roleHierarchy: Record<UserResponse['role'], number> = {
      viewer: 1,
      operator: 2,
      admin: 3,
    };
    return roleHierarchy[user.role] >= roleHierarchy[requiredRole];
  }, [user]);

  return {
    user,
    loading,
    error,
    login,
    demoLogin,
    logout,
    hasRole,
    isAuthenticated: !!user,
    isOperator: user?.role === 'operator' || user?.role === 'admin',
    isAdmin: user?.role === 'admin',
  };
}