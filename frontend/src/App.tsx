// TICKR — Main App with routing, auth guard, and Kite OAuth callback handler
import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import AppBar from './components/layout/AppBar';
import ChartPage from './pages/ChartPage';
import ScannerPage from './pages/ScannerPage';
import ScanResultsPage from './pages/ScanResultsPage';
import AdminPluginsPage from './pages/AdminPluginsPage';
import LoginPage from './pages/LoginPage';
import api from './api/client';

/**
 * Handles the Kite OAuth redirect callback.
 * After the user logs in on Zerodha, Kite redirects back to:
 *   http://localhost:5173?request_token=xyz&status=success&action=login
 * This hook detects that param, exchanges it for an access token, and cleans the URL.
 */
function KiteCallbackHandler() {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const requestToken = params.get('request_token');
    const status = params.get('status');

    if (requestToken && status === 'success') {
      console.log('[TICKR] Kite OAuth callback detected — exchanging request_token...');
      api.post('/api/kite/session', { request_token: requestToken })
        .then(() => {
          console.log('[TICKR] Kite session established successfully.');
          // Clean the URL — remove Kite params without triggering a navigation
          const clean = location.pathname;
          navigate(clean, { replace: true });
        })
        .catch((err) => {
          console.error('[TICKR] Failed to exchange Kite request_token:', err);
          navigate(location.pathname, { replace: true });
        });
    }
  }, []); // Run once on mount

  return null;
}

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return (
    <div className="app-shell">
      <AppBar />
      <main className="app-main">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <KiteCallbackHandler />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedLayout><ChartPage /></ProtectedLayout>} />
        <Route path="/scanner" element={<ProtectedLayout><ScannerPage /></ProtectedLayout>} />
        <Route path="/results" element={<ProtectedLayout><ScanResultsPage /></ProtectedLayout>} />
        <Route path="/admin/plugins" element={<ProtectedLayout><AdminPluginsPage /></ProtectedLayout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
