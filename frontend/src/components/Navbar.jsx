/**
 * components/Navbar.jsx
 * ─────────────────────
 * Top navigation bar — shows role badge, user name, and logout button.
 * Highlights active route with an underline indicator.
 */

import { Link, useLocation, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { Scale, LogOut, LayoutDashboard, BookOpen, Shield } from 'lucide-react';

const ROLE_LINKS = {
  admin:    [{ to: '/admin',    label: 'Admin Panel',  Icon: Shield }],
  student:  [{ to: '/student',  label: 'My Cases',     Icon: BookOpen }],
  official: [{ to: '/dashboard',label: 'Dashboard',    Icon: LayoutDashboard }],
};

const ROLE_COLORS = {
  admin:    'bg-white text-black border-white',
  student:  'bg-neutral-900 text-neutral-200 border-neutral-500',
  official: 'bg-black text-white border-white',
};

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();

  const links = ROLE_LINKS[user?.role] || [];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      {/* Brand */}
      <Link to="/" className="navbar-brand">
        <div className="brand-icon">
          <Scale size={18} className="text-neutral-200" />
        </div>
        <span className="brand-name">
          Lex<span className="brand-accent">Flow</span>
        </span>
      </Link>

      {/* Nav links */}
      <div className="navbar-links">
        {links.map(({ to, label, Icon }) => (
          <Link
            key={to}
            to={to}
            className={`nav-link ${location.pathname.startsWith(to) ? 'nav-link-active' : ''}`}
          >
            <Icon size={15} />
            {label}
          </Link>
        ))}
      </div>

      {/* User info + logout */}
      {user && (
        <div className="navbar-user">
          <span className={`role-badge ${ROLE_COLORS[user.role]}`}>
            {user.role}
          </span>
          <span className="user-name">{user.name}</span>
          <button className="logout-btn" onClick={handleLogout} title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      )}
    </nav>
  );
}
