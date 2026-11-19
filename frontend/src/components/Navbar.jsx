import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getDefaultRouteForRole, useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <Link to={user ? getDefaultRouteForRole(user.role) : '/login'} className="brand-link">
          Smart Hospital Queue System
        </Link>
      </div>
      <nav className="navbar-links">
        <Link to="/queue">Live Queue Board</Link>
        {user && user.role === 'PATIENT' && <Link to="/patient">Patient Dashboard</Link>}
        {user && user.role === 'DOCTOR' && <Link to="/doctor">Doctor Dashboard</Link>}
        {user && user.role === 'ADMIN' && <Link to="/admin">Admin Dashboard</Link>}
        {user && <Link to="/notifications">Notifications</Link>}
        {user && user.role === 'ADMIN' && <Link to="/reports">Daily Reports</Link>}
      </nav>
      <div className="navbar-user">
        {user ? (
          <>
            <span className="user-badge" data-testid="navbar-user-badge">
              {user.name} ({user.role})
            </span>
            <button type="button" className="btn btn-outline btn-sm" onClick={handleLogout}>
              Logout
            </button>
          </>
        ) : (
          <div className="auth-links">
            <Link to="/login" className="btn btn-outline btn-sm">
              Login
            </Link>
            <Link to="/register" className="btn btn-primary btn-sm">
              Register
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
