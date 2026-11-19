import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import api from '../api/client';
import { AuthProvider } from '../context/AuthContext';
import PatientDashboard from '../pages/PatientDashboard';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return {
    ...actual,
    default: {
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
    },
  };
});

describe('Sub-Phase 1D: Frontend Foundation, Route Guards, Auth & Patient Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('redirects unauthenticated users trying to access /patient to /login', () => {
    render(
      <MemoryRouter initialEntries={['/patient']}>
        <AuthProvider initialUser={null}>
          <App />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText(/Sign In to Smart Hospital/i)).toBeInTheDocument();
  });

  it('enforces role guards by redirecting a PATIENT trying to access /admin back to /patient', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/departments') return Promise.resolve({ data: { departments: [] } });
      if (url.startsWith('/doctors')) return Promise.resolve({ data: { doctors: [] } });
      if (url === '/appointments') return Promise.resolve({ data: { appointments: [] } });
      return Promise.resolve({ data: {} });
    });

    const patientUser = { id: 5, name: 'Ananya Gupta', email: 'patient1@hospital.test', role: 'PATIENT' };

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AuthProvider initialUser={patientUser}>
          <App />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByRole('heading', { name: /Patient Dashboard/i })).toBeInTheDocument();
  });

  it('validates login form and logs in a patient user', async () => {
    const user = userEvent.setup();
    api.post.mockResolvedValueOnce({
      data: {
        token: 'fake-jwt-token',
        user: { id: 5, name: 'Ananya Gupta', email: 'patient1@hospital.test', role: 'PATIENT' },
      },
    });
    api.get.mockImplementation((url) => {
      if (url === '/departments') return Promise.resolve({ data: { departments: [] } });
      if (url.startsWith('/doctors')) return Promise.resolve({ data: { doctors: [] } });
      if (url === '/appointments') return Promise.resolve({ data: { appointments: [] } });
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider initialUser={null}>
          <App />
        </AuthProvider>
      </MemoryRouter>
    );

    await user.click(screen.getByRole('button', { name: /Login/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/Email and password are required/i);

    await user.type(screen.getByLabelText(/Email Address/i), 'patient1@hospital.test');
    await user.type(screen.getByLabelText(/Password/i), 'Patient@123');
    await user.click(screen.getByRole('button', { name: /Login/i }));

    expect(await screen.findByRole('heading', { name: /Patient Dashboard/i })).toBeInTheDocument();
    expect(localStorage.getItem('hospital_jwt_token')).toBe('fake-jwt-token');
  });

  it('validates password length on RegisterPage and registers a new patient', async () => {
    const user = userEvent.setup();
    api.post.mockResolvedValueOnce({
      data: {
        token: 'new-patient-jwt',
        user: { id: 9, name: 'Riya Sen', email: 'riya@example.com', role: 'PATIENT' },
      },
    });
    api.get.mockResolvedValue({ data: { departments: [], doctors: [], appointments: [] } });

    render(
      <MemoryRouter initialEntries={['/register']}>
        <AuthProvider initialUser={null}>
          <App />
        </AuthProvider>
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/Full Name/i), 'Riya Sen');
    await user.type(screen.getByLabelText(/Email Address/i), 'riya@example.com');
    await user.type(screen.getByLabelText(/Phone Number/i), '9876501234');
    await user.type(screen.getByLabelText(/Password/i), 'short');
    await user.click(screen.getByRole('button', { name: /Create Patient Account/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/at least 8 characters/i);

    await user.clear(screen.getByLabelText(/Password/i));
    await user.type(screen.getByLabelText(/Password/i), 'ValidPass123');
    await user.click(screen.getByRole('button', { name: /Create Patient Account/i }));

    expect(await screen.findByRole('heading', { name: /Patient Dashboard/i })).toBeInTheDocument();
  });

  it('renders PatientDashboard, loads doctors & slots, books an appointment, and displays token', async () => {
    const user = userEvent.setup();
    const patientUser = { id: 5, name: 'Ananya Gupta', email: 'patient1@hospital.test', role: 'PATIENT' };

    api.get.mockImplementation((url) => {
      if (url === '/departments') {
        return Promise.resolve({
          data: { departments: [{ id: 1, name: 'Cardiology' }] },
        });
      }
      if (url.startsWith('/doctors?')) {
        return Promise.resolve({
          data: {
            doctors: [
              {
                id: 1,
                name: 'Dr. Aarav Sharma',
                doc_code: 'DOC1',
                department_id: 1,
                department_name: 'Cardiology',
                specialization: 'Senior Cardiologist',
                room_number: 'Room 101',
              },
            ],
          },
        });
      }
      if (url.startsWith('/doctors/1/slots')) {
        return Promise.resolve({
          data: {
            doctor_id: 1,
            effective_capacity: 12,
            remaining_capacity: 11,
            slots: [
              { slot_time: '09:00', is_booked: true, is_past: false, is_available: false },
              { slot_time: '09:15', is_booked: false, is_past: false, is_available: true },
            ],
          },
        });
      }
      if (url === '/appointments') {
        return Promise.resolve({
          data: {
            appointments: [
              {
                id: 101,
                token_number: 'DOC1-002',
                doctor_name: 'Dr. Aarav Sharma',
                department_name: 'Cardiology',
                room_number: 'Room 101',
                appointment_date: '2026-11-20',
                slot_time: '09:15',
                status: 'BOOKED',
                reason: 'Routine checkup',
              },
            ],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    api.post.mockResolvedValueOnce({
      data: {
        appointment: {
          id: 101,
          token_number: 'DOC1-002',
          doctor_name: 'Dr. Aarav Sharma',
          appointment_date: '2026-11-20',
          slot_time: '09:15',
          status: 'BOOKED',
        },
      },
    });

    render(
      <MemoryRouter>
        <AuthProvider initialUser={patientUser}>
          <PatientDashboard />
        </AuthProvider>
      </MemoryRouter>
    );

    const openSlotBtn = await screen.findByRole('button', { name: '09:15' });
    expect(openSlotBtn).not.toBeDisabled();

    const bookedSlotBtn = screen.getByRole('button', { name: /09:00 \(Booked\)/i });
    expect(bookedSlotBtn).toBeDisabled();

    await user.click(openSlotBtn);
    await user.type(screen.getByLabelText(/Reason for Visit/i), 'Routine checkup');
    await user.click(screen.getByRole('button', { name: /Confirm Online Booking/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/appointments',
        expect.objectContaining({
          doctor_id: 1,
          slot_time: '09:15',
          reason: 'Routine checkup',
        })
      );
    });

    expect(await screen.findByRole('status')).toHaveTextContent(/DOC1-002/i);
    expect(screen.getByText('Routine checkup')).toBeInTheDocument();
  });
});
