// TICKR — Profile Modal with Data Sources tab
import { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import { useNavigate } from 'react-router-dom';
import DataManagementPanel from '../data/DataManagementPanel';

interface Props { onClose: () => void; }

type Tab = 'profile' | 'data';

export default function ProfileModal({ onClose }: Props) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('profile');

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="profile-modal profile-modal--wide" onClick={(e) => e.stopPropagation()}>

        {/* Tab bar */}
        <div className="profile-tabs">
          <button
            id="profile-tab-btn"
            className={`profile-tab ${activeTab === 'profile' ? 'profile-tab--active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            Profile
          </button>
          <button
            id="data-sources-tab-btn"
            className={`profile-tab ${activeTab === 'data' ? 'profile-tab--active' : ''}`}
            onClick={() => setActiveTab('data')}
          >
            Data Sources
          </button>
        </div>

        {/* Profile tab */}
        {activeTab === 'profile' && (
          <>
            <div className="profile-avatar-lg">{user?.avatar_initials}</div>
            <div className="profile-name">{user?.full_name}</div>
            <div className="profile-email">{user?.email}</div>
            <div className="profile-username">@{user?.username}</div>
            <hr className="profile-divider" />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
              <div style={{ marginBottom: 4 }}>Member since account creation</div>
              <div>Trading Terminal v2.0</div>
            </div>
            <button id="logout-btn" className="btn-logout" onClick={handleLogout}>
              Sign out
            </button>
          </>
        )}

        {/* Data Sources tab */}
        {activeTab === 'data' && <DataManagementPanel />}
      </div>
    </div>
  );
}
