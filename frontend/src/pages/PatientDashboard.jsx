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

export default function PatientDashboard() {
  const { user } = useAuth();
  const [departments, setDepartments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [selectedDeptId, setSelectedDeptId] = useState('');
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [appointmentDate, setAppointmentDate] = useState(getTodayDateString());
  const [slotsInfo, setSlotsInfo] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [reason, setReason] = useState('');

  const [appointments, setAppointments] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const loadMasterAndAppointments = useCallback(async () => {
    try {
      const [deptRes, docRes, apptRes] = await Promise.all([
        api.get('/departments'),
        api.get('/doctors?active_only=true&include_schedules=true'),
        api.get('/appointments'),
      ]);
      const deptList = deptRes.data.departments || [];
      const docList = docRes.data.doctors || [];
      setDepartments(deptList);
      setDoctors(docList);
      setAppointments(apptRes.data.appointments || []);

      if (docList.length > 0 && !selectedDoctorId) {
        setSelectedDoctorId(String(docList[0].id));
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load hospital data.'));
    }
  }, [selectedDoctorId]);

  useEffect(() => {
    loadMasterAndAppointments();
  }, [loadMasterAndAppointments]);

  const loadSlots = useCallback(async (doctorId, dateStr) => {
    if (!doctorId || !dateStr) return;
    setLoadingSlots(true);
    setSelectedSlot('');
    try {
      const res = await api.get(`/doctors/${doctorId}/slots?date=${dateStr}`);
      setSlotsInfo(res.data);
    } catch (err) {
      setSlotsInfo(null);
      setError(extractErrorMessage(err, 'Could not load slots for the selected date.'));
    } finally {
      setLoadingSlots(false);
    }
  }, []);

  useEffect(() => {
    if (selectedDoctorId && appointmentDate) {
      loadSlots(selectedDoctorId, appointmentDate);
    }
  }, [selectedDoctorId, appointmentDate, loadSlots]);

  const filteredDoctors = selectedDeptId
    ? doctors.filter((d) => String(d.department_id) === String(selectedDeptId))
    : doctors;

  const handleBookAppointment = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!selectedDoctorId || !appointmentDate || !selectedSlot) {
      setError('Please select a doctor, date, and an open time slot.');
      return;
    }

    setBookingLoading(true);
    try {
      const res = await api.post('/appointments', {
        doctor_id: Number(selectedDoctorId),
        appointment_date: appointmentDate,
        slot_time: selectedSlot,
        reason: reason.trim() || undefined,
      });
      const booked = res.data.appointment;
      setMessage(
        `Appointment booked! Token Number: ${booked.token_number} (${booked.doctor_name} at ${booked.slot_time} on ${booked.appointment_date})`
      );
      setReason('');
      setSelectedSlot('');
      await Promise.all([
        loadMasterAndAppointments(),
        loadSlots(selectedDoctorId, appointmentDate),
      ]);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to book appointment.'));
    } finally {
      setBookingLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Patient Dashboard</h1>
          <p className="text-muted">
            Welcome, {user?.name}. Browse doctors, check real-time slot availability, and book your visit.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {message && (
        <div className="alert alert-success" role="status">
          {message}
        </div>
      )}

      <div className="dashboard-grid">
        <section className="card">
          <h2>Book Online Appointment</h2>
          <form onSubmit={handleBookAppointment}>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="dept-filter">Filter by Department</label>
                <select
                  id="dept-filter"
                  value={selectedDeptId}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedDeptId(val);
                    const matching = val
                      ? doctors.filter((d) => String(d.department_id) === String(val))
                      : doctors;
                    if (matching.length > 0) {
                      setSelectedDoctorId(String(matching[0].id));
                    } else {
                      setSelectedDoctorId('');
                    }
                  }}
                >
                  <option value="">All Departments</option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="doctor-select">Select Doctor</label>
                <select
                  id="doctor-select"
                  value={selectedDoctorId}
                  onChange={(e) => setSelectedDoctorId(e.target.value)}
                  required
                >
                  <option value="">-- Choose Doctor --</option>
                  {filteredDoctors.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.name} ({doc.doc_code} - {doc.specialization}, {doc.room_number})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="appointment-date">Appointment Date</label>
              <input
                id="appointment-date"
                type="date"
                value={appointmentDate}
                onChange={(e) => setAppointmentDate(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Available Time Slots</label>
              {loadingSlots && <p className="text-muted">Loading slots...</p>}
              {!loadingSlots && slotsInfo && (
                <div className="slots-meta">
                  <span>
                    Effective Capacity: <strong>{slotsInfo.effective_capacity}</strong> | Remaining:{' '}
                    <strong>{slotsInfo.remaining_capacity}</strong>
                  </span>
                </div>
              )}

              <div className="slots-grid" data-testid="slots-grid">
                {!loadingSlots &&
                  slotsInfo?.slots?.map((slot) => {
                    const isSelected = selectedSlot === slot.slot_time;
                    return (
                      <button
                        key={slot.slot_time}
                        type="button"
                        disabled={!slot.is_available}
                        onClick={() => setSelectedSlot(slot.slot_time)}
                        className={`slot-btn ${isSelected ? 'slot-selected' : ''} ${
                          !slot.is_available ? 'slot-disabled' : ''
                        }`}
                      >
                        {slot.slot_time}
                        {slot.is_booked ? ' (Booked)' : slot.is_past ? ' (Past)' : ''}
                      </button>
                    );
                  })}
                {!loadingSlots && (!slotsInfo?.slots || slotsInfo.slots.length === 0) && (
                  <p className="text-muted">No schedule slots configured for this date.</p>
                )}
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="booking-reason">Reason for Visit (Optional)</label>
              <input
                id="booking-reason"
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g., Routine checkup or consultation"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={bookingLoading || !selectedSlot}
            >
              {bookingLoading ? 'Booking...' : 'Confirm Online Booking'}
            </button>
          </form>
        </section>

        <section className="card">
          <h2>My Appointments</h2>
          {appointments.length === 0 ? (
            <p className="text-muted">You have no appointments yet.</p>
          ) : (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Doctor</th>
                    <th>Date &amp; Slot</th>
                    <th>Status</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appt) => (
                    <tr key={appt.id}>
                      <td>
                        <strong className="token-pill">{appt.token_number}</strong>
                        {appt.previous_token && (
                          <div className="text-xs text-muted">Prev: {appt.previous_token}</div>
                        )}
                      </td>
                      <td>
                        <div>{appt.doctor_name}</div>
                        <small className="text-muted">
                          {appt.department_name} • {appt.room_number}
                        </small>
                      </td>
                      <td>
                        <div>{appt.appointment_date}</div>
                        <small className="text-muted">{appt.slot_time}</small>
                      </td>
                      <td>
                        <span className={`status-badge status-${appt.status.toLowerCase()}`}>
                          {appt.status}
                        </span>
                      </td>
                      <td>{appt.reason || '-'}</td>
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
