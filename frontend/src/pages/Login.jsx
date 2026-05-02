/**
 * pages/Login.jsx
 * ───────────────
 * Single login page for all three roles (admin / student / official).
 * After successful login, redirects based on role.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Scale, Mail, Lock, Loader2, Eye, EyeOff } from 'lucide-react';
import client from '../api/client';
import useAuthStore from '../store/authStore';

const ROLE_REDIRECTS = {
  admin: '/admin',
  student: '/student',
  official: '/dashboard',
};

const DEMO_CREDS = [
  { role: 'Admin',    email: 'admin@lexflow.com',    password: 'admin123' },
  { role: 'Student',  email: 'student@lexflow.com',  password: 'student123' },
  { role: 'Official', email: 'official@lexflow.com', password: 'official123' },
];

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const [form, setForm] = useState({ email: '', password: '' });
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { data } = await client.post('/auth/login', form);
      login(data.access_token, data.user);
      navigate(ROLE_REDIRECTS[data.user.role] || '/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (email, password) => setForm({ email, password });

  return (
    <div className="login-page">
      <div className="login-live-bg" aria-hidden="true">
        <div className="case-thread thread-a" />
        <div className="case-thread thread-b" />
        <div className="case-thread thread-c" />
        <div className="intel-panel panel-a">
          <span />
          <span />
          <span />
        </div>
        <div className="intel-panel panel-b">
          <span />
          <span />
          <span />
        </div>
        <div className="intel-panel panel-c">
          <span />
          <span />
          <span />
        </div>
        <div className="signal-node node-a" />
        <div className="signal-node node-b" />
        <div className="signal-node node-c" />
        <div className="signal-node node-d" />
      </div>

      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <div className="logo-icon">
            <Scale size={28} className="text-neutral-200" />
          </div>
          <h1 className="login-title">
            Lex<span className="text-neutral-400">Flow</span>
          </h1>
          <p className="login-subtitle">AI-Powered Court Judgment Intelligence</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form" id="login-form">
          <div className="input-group">
            <label htmlFor="email" className="input-label">Email</label>
            <div className="input-wrapper">
              <Mail size={16} className="input-icon" />
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="text-input"
                placeholder="you@example.com"
                value={form.email}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="password" className="input-label">Password</label>
            <div className="input-wrapper">
              <Lock size={16} className="input-icon" />
              <input
                id="password"
                name="password"
                type={showPwd ? 'text' : 'password'}
                autoComplete="current-password"
                required
                className="text-input"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange}
              />
              <button
                type="button"
                className="pwd-toggle"
                onClick={() => setShowPwd((v) => !v)}
              >
                {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {error && <p className="login-error">{error}</p>}

          <button
            type="submit"
            className="login-btn"
            id="login-submit-btn"
            disabled={loading}
          >
            {loading ? (
              <><Loader2 size={17} className="spin" /> Signing in…</>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Demo credentials quick-fill */}
        <div className="demo-section">
          <p className="demo-label">Demo accounts</p>
          <div className="demo-pills">
            {DEMO_CREDS.map(({ role, email, password }) => (
              <button
                key={role}
                className="demo-pill"
                onClick={() => fillDemo(email, password)}
                id={`demo-${role.toLowerCase()}`}
              >
                {role}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
