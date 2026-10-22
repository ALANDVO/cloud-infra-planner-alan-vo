// frontend/src/App.tsx
// Main application with routing

import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Index } from './components/Index';
import { GenerateForm } from './components/GenerateForm';
import { HistoryList } from './components/HistoryList';
import { GenerationDetail } from './components/GenerationDetail';
import { LoginForm } from './components/LoginForm';
import { Settings } from './components/Settings';
import { useAuth } from './hooks/useAuth';
import './styles/app.css';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen" role="status" aria-label="Loading authentication">
        <div className="spinner"></div>
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}
function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginForm />} />
      <Route element={<Layout />}>
        <Route index element={<Index />} />
        <Route path="generate" element={<GenerateForm />} />
        <Route path="history" element={<PrivateRoute><HistoryList /></PrivateRoute>} />
        <Route path="history/:id" element={<PrivateRoute><GenerationDetail /></PrivateRoute>} />
        <Route path="settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;