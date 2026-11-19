import React, { useCallback, useEffect, useState } from 'react';
import api, { extractErrorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';

function getTodayDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function DoctorDashboard() {
  const { user } = useAuth();
  const [selectedDate, setSelectedDate] = useState(getTodayDateString());
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const fetchDoctorAppointments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/appointments?date=${selectedDate}&include_history=true`);
      setAppointments(res.data.appointments || []);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to fetch doctor appointments.'));
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    fetchDoctorAppointments();
  }, [fetchDoctorAppointments]);

  const handleStatusUpdate = async (appointmentId, newStatus, note = '') => {
    setActionLoading(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api.patch(`/appointments/${appointmentId}/status`, {
        status: newStatus,
        note,
      });
      const updated = res.data.appointment;
      setMessage(`Appointment ${updated.token_number} updated to ${updated.status}.`);
      await fetchDoctorAppointments();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to update status.'));
    } finally {
      setActionLoading(false);
    }
  };

  const inConsultation = appointments.find((a) => a.status === 'IN_CONSULTATION');
  const waitingList = appointments.filter((a) => a.status === 'CONFIRMED' || a.status === 'BOOKED');

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Doctor Console</h1>
          <p className="text-muted">
            {user?.name} | Specialization: {user?.doc_code || 'Attending Doctor'}
          </p>
        </div>
        <div className="form-group" style={{ margin: 0 }}>
          <label htmlFor="doc-date-picker">Queue Date:</label>
          <input
            id="doc-date-picker"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />
        </div>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {message && <div className="alert alert-success" role="status">{message}</div>}

      <div className="dashboard-grid">
        <section className="card active-consultation-card">
          <h2>Active Consultation</h2>
          {inConsultation ? (
            <div className="active-card-content">
              <div className="token-hero">
                <span className="token-hero-badge">{inConsultation.token_number}</span>
                <h3>{inConsultation.patient_name}</h3>
                <p className="text-muted">
                  Slot: {inConsultation.slot_time} | Phone: {inConsultation.patient_phone}
                </p>
                {inConsultation.reason && <p><strong>Reason:</strong> {inConsultation.reason}</p>}
              </div>
              <div className="action-buttons">
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={actionLoading}
                  onClick={() => handleStatusUpdate(inConsultation.id, 'COMPLETED', 'Consultation finished')}
                >
                  Mark Completed
                </button>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p className="text-muted">No patient currently in consultation.</p>
              {waitingList.length > 0 && waitingList[0].status === 'CONFIRMED' && (
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={actionLoading}
                  onClick={() => handleStatusUpdate(waitingList[0].id, 'IN_CONSULTATION', 'Doctor called next patient')}
                >
                  Call Next Patient ({waitingList[0].token_number})
                </button>
              )}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Daily Queue ({appointments.length})</h2>
          {loading ? (
            <p className="text-muted">Loading appointments...</p>
          ) : appointments.length === 0 ? (
            <p className="text-muted">No appointments booked for this date.</p>
          ) : (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Time</th>
                    <th>Patient</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appt) => (
                    <tr key={appt.id}>
                      <td><span className="token-pill">{appt.token_number}</span></td>
                      <td>{appt.slot_time}</td>
                      <td>
                        <div>{appt.patient_name}</div>
                        <small className="text-muted">{appt.patient_phone}</small>
                      </td>
                      <td>{appt.booking_type}</td>
                      <td>
                        <span className={`status-badge status-${appt.status.toLowerCase()}`}>
                          {appt.status}
                        </span>
                      </td>
                      <td>
                        {appt.status === 'CONFIRMED' && !inConsultation && (
                          <button
                            type="button"
                            className="btn btn-sm btn-primary"
                            disabled={actionLoading}
                            onClick={() => handleStatusUpdate(appt.id, 'IN_CONSULTATION', 'Doctor called token')}
                          >
                            Call
                          </button>
                        )}
                        {(appt.status === 'CONFIRMED' || appt.status === 'BOOKED') && (
                          <button
                            type="button"
                            className="btn btn-sm btn-outline"
                            style={{ marginLeft: '4px' }}
                            disabled={actionLoading}
                            onClick={() => handleStatusUpdate(appt.id, 'NO_SHOW', 'Patient did not arrive')}
                          >
                            No Show
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
