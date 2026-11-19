import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api from '../api/client';
import { AuthProvider } from '../context/AuthContext';
import QueueBoard from '../pages/QueueBoard';
import NotificationsPage from '../pages/NotificationsPage';

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

// Mock ChartJS rendering so tests don't fail in headless JSDOM without canvas
vi.mock('react-chartjs-2', () => ({
  Bar: () => <div data-testid="bar-chart" />,
  Doughnut: () => <div data-testid="doughnut-chart" />,
  Line: () => <div data-testid="line-chart" />,
}));

describe('Staff Screens & Queue Board Vitest Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders Live Queue Board and displays current in consultation token', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/departments') return Promise.resolve({ data: { departments: [] } });
      if (url.startsWith('/doctors')) return Promise.resolve({ data: { doctors: [] } });
      if (url.startsWith('/queue')) {
        return Promise.resolve({
          data: {
            date: '2026-11-20',
            current_in_consultation: {
              id: 1,
              token_number: 'DOC1-001',
              patient_name: 'Ananya Gupta',
              doctor_name: 'Dr. Aarav Sharma',
              room_number: 'Room 101',
              slot_time: '09:00',
              department_name: 'Cardiology',
            },
            next_waiting: [
              {
                id: 2,
                token_number: 'DOC1-002',
                patient_name: 'Vikram Singh',
                doctor_name: 'Dr. Aarav Sharma',
                room_number: 'Room 101',
                slot_time: '09:15',
                status: 'CONFIRMED',
              },
            ],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter>
        <QueueBoard />
      </MemoryRouter>
    );

    expect(await screen.findByText('DOC1-001')).toBeInTheDocument();
    expect(screen.getByText('Ananya Gupta')).toBeInTheDocument();
    expect(screen.getByText('DOC1-002')).toBeInTheDocument();
  });

  it('renders NotificationsPage audit trail', async () => {
    api.get.mockImplementation((url) => {
      if (url.startsWith('/notifications')) {
        return Promise.resolve({
          data: {
            notifications: [
              {
                id: 1,
                channel: 'EMAIL',
                event_type: 'BOOKING_CREATED',
                recipient: 'patient@hospital.test',
                subject: 'Appointment Booked',
                message: 'Your token is DOC1-001',
                delivery_mode: 'SIMULATED',
                created_at: '2026-11-20 09:00:00',
              },
            ],
            total: 1,
            page: 1,
            pages: 1,
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(
      <MemoryRouter>
        <AuthProvider initialUser={{ id: 1, role: 'ADMIN', name: 'Admin' }}>
          <NotificationsPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Appointment Booked')).toBeInTheDocument();
    expect(screen.getByText('patient@hospital.test')).toBeInTheDocument();
    expect(screen.getByText('SIMULATED')).toBeInTheDocument();
  });
});
