import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { extractErrorMessage } from '../api/client';
import { getDefaultRouteForRole, useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password) {
      setError('Email and password are required.');
      return;
    }

    try {
      const userObj = await login(email.trim(), password);
      navigate(getDefaultRouteForRole(userObj.role));
    } catch (err) {
      setError(extractErrorMessage(err, 'Login failed. Please check your credentials.'));
    }
  };

  return (
    <div className="auth-container">
      <div className="card auth-card">
        <h2>Sign In to Smart Hospital</h2>
        <p className="text-muted">Access appointments, live queues, and clinical consoles.</p>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="patient1@hospital.test"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Signing In...' : 'Login'}
          </button>
        </form>

        <p className="auth-footer">
          New patient? <Link to="/register">Create a Patient Account</Link>
        </p>
      </div>
    </div>
  );
}
