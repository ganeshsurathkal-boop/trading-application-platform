// TICKR — Auth page (Login / Register)
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function LoginPage() {
  const { login, register } = useAuthStore();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ username: '', password: '', email: '', full_name: '' });

  const handle = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register({ username: form.username, password: form.password, email: form.email, full_name: form.full_name });
      } else {
        await login(form.username, form.password);
      }
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">TICKR</div>
        <div className="auth-subtitle">
          {isRegister ? 'Create your trading account' : 'Sign in to your trading terminal'}
        </div>

        <form onSubmit={submit}>
          {isRegister && (
            <div className="form-group">
              <label className="form-label">Full name</label>
              <input id="full-name-input" className="form-input" type="text" placeholder="Ganesh Kumar" value={form.full_name} onChange={handle('full_name')} required />
            </div>
          )}
          {isRegister && (
            <div className="form-group">
              <label className="form-label">Email</label>
              <input id="email-input" className="form-input" type="email" placeholder="you@example.com" value={form.email} onChange={handle('email')} required />
            </div>
          )}
          <div className="form-group">
            <label className="form-label">Username</label>
            <input id="username-input" className="form-input" type="text" placeholder="username" value={form.username} onChange={handle('username')} required autoComplete="username" />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input id="password-input" className="form-input" type="password" placeholder="••••••••" value={form.password} onChange={handle('password')} required autoComplete="current-password" />
          </div>

          {error && <div className="error-msg">{error}</div>}

          <button id="submit-auth-btn" className="btn-primary" type="submit" disabled={loading}>
            {loading ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
          </button>
        </form>

        <div className="auth-switch">
          {isRegister ? 'Already have an account? ' : "Don't have an account? "}
          <span onClick={() => { setIsRegister((r) => !r); setError(''); }}>
            {isRegister ? 'Sign in' : 'Register'}
          </span>
        </div>
      </div>
    </div>
  );
}
