// TICKR — AppBar component
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import ProfileModal from '../profile/ProfileModal';

export default function AppBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const [showProfile, setShowProfile] = useState(false);

  const screenLabel =
    location.pathname.startsWith('/scanner') ? 'SCREEN 2 — STOCK SCANNER' :
    location.pathname.startsWith('/results') ? 'SCREEN 3 — SCAN RESULTS' :
    'SCREEN 1 — CHART TERMINAL';

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <>
      <header className="appbar" style={{ position: 'relative' }}>
        <span className="appbar-screen-label">{screenLabel}</span>

        <div className="appbar-logo" onClick={() => navigate('/')}>TICKR</div>

        <nav className="appbar-nav">
          <span
            id="nav-chart"
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
            onClick={() => navigate('/')}
          >Chart</span>

          <span
            id="nav-scanner"
            className={`nav-link ${isActive('/scanner') || isActive('/results') ? 'active' : ''}`}
            onClick={() => navigate('/scanner')}
          >Scanner</span>

          <span
            id="nav-watchlists"
            className={`nav-link`}
            onClick={() => navigate('/')}
          >Watchlists</span>

          <button
            id="profile-btn"
            className="avatar-btn"
            onClick={() => setShowProfile(true)}
            title={user?.full_name}
          >
            {user?.avatar_initials || '??'}
          </button>
        </nav>
      </header>

      {showProfile && <ProfileModal onClose={() => setShowProfile(false)} />}
    </>
  );
}
