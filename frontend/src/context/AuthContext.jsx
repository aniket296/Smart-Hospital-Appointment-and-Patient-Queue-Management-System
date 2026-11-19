import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children, initialUser = undefined }) {
  const [user, setUser] = useState(() => {
    if (initialUser !== undefined) return initialUser;
    const saved = localStorage.getItem('hospital_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });

  const [token, setToken] = useState(() => localStorage.getItem('hospital_jwt_token') || null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const handleUnauthorized = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener('hospital:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('hospital:unauthorized', handleUnauthorized);
  }, []);

  const saveSession = (jwtToken, userObj) => {
    localStorage.setItem('hospital_jwt_token', jwtToken);
    localStorage.setItem('hospital_user', JSON.stringify(userObj));
    setToken(jwtToken);
    setUser(userObj);
  };

  const login = async (email, password) => {
    setLoading(true);
    try {
      const res = await api.post('/auth/login', { email, password });
      const { token: jwtToken, user: userObj } = res.data;
      saveSession(jwtToken, userObj);
      return userObj;
    } finally {
      setLoading(false);
    }
  };

  const register = async (payload) => {
    setLoading(true);
    try {
      const res = await api.post('/auth/register', payload);
      const { token: jwtToken, user: userObj } = res.data;
      saveSession(jwtToken, userObj);
      return userObj;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('hospital_jwt_token');
    localStorage.removeItem('hospital_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside an AuthProvider');
  }
  return ctx;
}

export function getDefaultRouteForRole(role) {
  if (role === 'ADMIN') return '/admin';
  if (role === 'DOCTOR') return '/doctor';
  return '/patient';
}
