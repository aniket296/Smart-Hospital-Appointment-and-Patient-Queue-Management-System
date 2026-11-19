import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import { getDefaultRouteForRole, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import PatientDashboard from './pages/PatientDashboard';
import RegisterPage from './pages/RegisterPage';

function RoleHomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={getDefaultRouteForRole(user.role)} replace />;
}

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<RoleHomeRedirect />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/patient"
            element={
              <ProtectedRoute allowedRoles={['PATIENT']}>
                <PatientDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/doctor"
            element={
              <ProtectedRoute allowedRoles={['DOCTOR']}>
                <div className="page-container">
                  <h1>Doctor Dashboard</h1>
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <div className="page-container">
                  <h1>Admin Dashboard</h1>
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/queue"
            element={
              <div className="page-container">
                <h1>Live Queue Board</h1>
              </div>
            }
          />
          <Route path="*" element={<RoleHomeRedirect />} />
        </Routes>
      </main>
    </div>
  );
}
