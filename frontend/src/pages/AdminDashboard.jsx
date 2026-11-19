import React, { useCallback, useEffect, useState } from 'react';
import api, { extractErrorMessage } from '../api/client';

function getTodayDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('walkin'); // 'walkin' | 'appointments' | 'doctors' | 'departments'
  const [departments, setDepartments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [selectedDate, setSelectedDate] = useState(getTodayDateString());
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(false);

  // Walk-in form state
  const [walkinDoctorId, setWalkinDoctorId] = useState('');
  const [walkinPatientName, setWalkinPatientName] = useState('');
  const [walkinPatientPhone, setWalkinPatientPhone] = useState('');
  const [walkinPatientEmail, setWalkinPatientEmail] = useState('');
  const [walkinSlotTime, setWalkinSlotTime] = useState('');
  const [walkinReason, setWalkinReason] = useState('');

  // Department creation state
  const [newDeptName, setNewDeptName] = useState('');
  const [newDeptDesc, setNewDeptDesc] = useState('');

  // Doctor creation state
  const [docName, setDocName] = useState('');
  const [docEmail, setDocEmail] = useState('');
  const [docPassword, setDocPassword] = useState('Doctor@123');
  const [docCode, setDocCode] = useState('');
  const [docDeptId, setDocDeptId] = useState('');
  const [docSpecialization, setDocSpecialization] = useState('');
  const [docRoom, setDocRoom] = useState('');

  // Schedule form state
  const [schedDoctorId, setSchedDoctorId] = useState('');
  const [schedDay, setSchedDay] = useState(0);
  const [schedStart, setSchedStart] = useState('09:00');
  const [schedEnd, setSchedEnd] = useState('13:00');
  const [schedDuration, setSchedDuration] = useState(15);
  const [schedMaxPatients, setSchedMaxPatients] = useState(12);

  const loadInitialData = useCallback(async () => {
    setLoading(true);
    try {
      const [deptRes, docRes] = await Promise.all([
        api.get('/departments'),
        api.get('/doctors?include_schedules=true'),
      ]);
      setDepartments(deptRes.data.departments || []);
      const docList = docRes.data.doctors || [];
      setDoctors(docList);
      if (docList.length > 0 && !walkinDoctorId) {
        setWalkinDoctorId(String(docList[0].id));
        setSchedDoctorId(String(docList[0].id));
      }
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load master data.'));
    } finally {
      setLoading(false);
    }
  }, [walkinDoctorId]);

  const loadAppointments = useCallback(async () => {
    try {
      const res = await api.get(`/appointments?date=${selectedDate}`);
      setAppointments(res.data.appointments || []);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load appointments.'));
    }
  }, [selectedDate]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    loadAppointments();
  }, [loadAppointments]);

  const handleWalkinSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const payload = {
        doctor_id: Number(walkinDoctorId),
        appointment_date: selectedDate,
        patient_name: walkinPatientName.trim(),
        patient_phone: walkinPatientPhone.trim(),
        patient_email: walkinPatientEmail.trim() || undefined,
        reason: walkinReason.trim() || undefined,
      };
      if (walkinSlotTime.trim()) {
        payload.slot_time = walkinSlotTime.trim();
      }

      const res = await api.post('/appointments/walk-in', payload);
      const appt = res.data.appointment;
      setMessage(`Walk-in booked successfully! Token: ${appt.token_number} at ${appt.slot_time}`);
      setWalkinPatientName('');
      setWalkinPatientPhone('');
      setWalkinPatientEmail('');
      setWalkinSlotTime('');
      setWalkinReason('');
      await loadAppointments();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to register walk-in patient.'));
    }
  };

  const handleStatusChange = async (appointmentId, newStatus) => {
    setError(null);
    setMessage(null);
    try {
      const res = await api.patch(`/appointments/${appointmentId}/status`, {
        status: newStatus,
        note: `Status updated to ${newStatus} by Admin`,
      });
      setMessage(`Appointment updated to ${res.data.appointment.status}.`);
      await loadAppointments();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to update status.'));
    }
  };

  const handleCreateDepartment = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const res = await api.post('/departments', {
        name: newDeptName.trim(),
        description: newDeptDesc.trim() || undefined,
      });
      setMessage(`Department '${res.data.department.name}' created.`);
      setNewDeptName('');
      setNewDeptDesc('');
      await loadInitialData();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to create department.'));
    }
  };

  const handleCreateDoctor = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const res = await api.post('/doctors', {
        name: docName.trim(),
        email: docEmail.trim(),
        password: docPassword,
        doc_code: docCode.trim().toUpperCase(),
        department_id: Number(docDeptId),
        specialization: docSpecialization.trim(),
        room_number: docRoom.trim(),
      });
      setMessage(`Doctor ${res.data.doctor.name} (${res.data.doctor.doc_code}) created.`);
      setDocName('');
      setDocEmail('');
      setDocCode('');
      setDocSpecialization('');
      setDocRoom('');
      await loadInitialData();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to create doctor profile.'));
    }
  };

  const handleCreateSchedule = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await api.post(`/doctors/${schedDoctorId}/schedules`, {
        day_of_week: Number(schedDay),
        start_time: schedStart,
        end_time: schedEnd,
        slot_duration_minutes: Number(schedDuration),
        max_patients: Number(schedMaxPatients),
      });
      setMessage(`Schedule added for doctor.`);
      await loadInitialData();
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to add doctor schedule.'));
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Hospital Administration &amp; Reception</h1>
          <p className="text-muted">Register walk-ins, manage appointments, configure doctors and schedules.</p>
        </div>
        <div className="tab-navigation">
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'walkin' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('walkin')}
          >
            Walk-in Registration
          </button>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'appointments' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('appointments')}
          >
            All Appointments
          </button>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'doctors' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('doctors')}
          >
            Doctors &amp; Schedules
          </button>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'departments' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('departments')}
          >
            Departments
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {message && <div className="alert alert-success" role="status">{message}</div>}

      {/* Tab 1: Walk-In Registration */}
      {activeTab === 'walkin' && (
        <div className="dashboard-grid">
          <section className="card">
            <h2>Register Walk-In Patient</h2>
            <form onSubmit={handleWalkinSubmit}>
              <div className="form-group">
                <label htmlFor="walkin-doc">Select Doctor</label>
                <select
                  id="walkin-doc"
                  value={walkinDoctorId}
                  onChange={(e) => setWalkinDoctorId(e.target.value)}
                  required
                >
                  {doctors.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.doc_code} - {d.department_name}, {d.room_number})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="walkin-name">Patient Full Name</label>
                  <input
                    id="walkin-name"
                    type="text"
                    value={walkinPatientName}
                    onChange={(e) => setWalkinPatientName(e.target.value)}
                    placeholder="e.g. Ramesh Kumar"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="walkin-phone">Phone Number</label>
                  <input
                    id="walkin-phone"
                    type="tel"
                    value={walkinPatientPhone}
                    onChange={(e) => setWalkinPatientPhone(e.target.value)}
                    placeholder="9876500000"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="walkin-email">Email (Optional)</label>
                  <input
                    id="walkin-email"
                    type="email"
                    value={walkinPatientEmail}
                    onChange={(e) => setWalkinPatientEmail(e.target.value)}
                    placeholder="patient@example.com"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="walkin-slot">Slot Time (Optional, leave blank to auto-assign)</label>
                  <input
                    id="walkin-slot"
                    type="text"
                    value={walkinSlotTime}
                    onChange={(e) => setWalkinSlotTime(e.target.value)}
                    placeholder="HH:MM (e.g. 10:30)"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="walkin-reason">Reason / Symptoms</label>
                <input
                  id="walkin-reason"
                  type="text"
                  value={walkinReason}
                  onChange={(e) => setWalkinReason(e.target.value)}
                  placeholder="e.g. Acute stomach pain"
                />
              </div>

              <button type="submit" className="btn btn-primary">
                Confirm Walk-in &amp; Issue Token
              </button>
            </form>
          </section>

          <section className="card">
            <h2>Today's Appointments ({appointments.length})</h2>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Doctor</th>
                    <th>Slot</th>
                    <th>Patient</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.slice(0, 10).map((a) => (
                    <tr key={a.id}>
                      <td><span className="token-pill">{a.token_number}</span></td>
                      <td>{a.doctor_name}</td>
                      <td>{a.slot_time}</td>
                      <td>{a.patient_name}</td>
                      <td><span className={`status-badge status-${a.status.toLowerCase()}`}>{a.status}</span></td>
                      <td>
                        {a.status === 'BOOKED' && (
                          <button
                            type="button"
                            className="btn btn-sm btn-primary"
                            onClick={() => handleStatusChange(a.id, 'CONFIRMED')}
                          >
                            Confirm Arrival
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* Tab 2: All Appointments */}
      {activeTab === 'appointments' && (
        <section className="card">
          <div className="page-header">
            <h2>Appointments Management</h2>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
            />
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Token</th>
                  <th>Doctor</th>
                  <th>Patient</th>
                  <th>Date &amp; Slot</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Admin Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((a) => (
                  <tr key={a.id}>
                    <td><span className="token-pill">{a.token_number}</span></td>
                    <td>{a.doctor_name} ({a.room_number})</td>
                    <td>{a.patient_name} <br/><small className="text-muted">{a.patient_phone}</small></td>
                    <td>{a.appointment_date} {a.slot_time}</td>
                    <td>{a.booking_type}</td>
                    <td><span className={`status-badge status-${a.status.toLowerCase()}`}>{a.status}</span></td>
                    <td>
                      {a.status === 'BOOKED' && (
                        <button
                          type="button"
                          className="btn btn-sm btn-primary"
                          onClick={() => handleStatusChange(a.id, 'CONFIRMED')}
                        >
                          Confirm
                        </button>
                      )}
                      {(a.status === 'BOOKED' || a.status === 'CONFIRMED') && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          style={{ marginLeft: '4px' }}
                          onClick={() => handleStatusChange(a.id, 'CANCELLED')}
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Tab 3: Doctors & Schedules */}
      {activeTab === 'doctors' && (
        <div className="dashboard-grid">
          <section className="card">
            <h2>Add Doctor Profile</h2>
            <form onSubmit={handleCreateDoctor}>
              <div className="form-group">
                <label htmlFor="doc-name">Full Name</label>
                <input
                  id="doc-name"
                  type="text"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                  placeholder="Dr. Sangeeta Rao"
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="doc-email">Email</label>
                  <input
                    id="doc-email"
                    type="email"
                    value={docEmail}
                    onChange={(e) => setDocEmail(e.target.value)}
                    placeholder="sangeeta@hospital.test"
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="doc-code">Doc Code</label>
                  <input
                    id="doc-code"
                    type="text"
                    value={docCode}
                    onChange={(e) => setDocCode(e.target.value)}
                    placeholder="DOC4"
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="doc-dept">Department</label>
                  <select
                    id="doc-dept"
                    value={docDeptId}
                    onChange={(e) => setDocDeptId(e.target.value)}
                    required
                  >
                    <option value="">Select Department</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="doc-room">Room Number</label>
                  <input
                    id="doc-room"
                    type="text"
                    value={docRoom}
                    onChange={(e) => setDocRoom(e.target.value)}
                    placeholder="Room 105"
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="doc-spec">Specialization</label>
                <input
                  id="doc-spec"
                  type="text"
                  value={docSpecialization}
                  onChange={(e) => setDocSpecialization(e.target.value)}
                  placeholder="Pediatrician"
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">Create Doctor</button>
            </form>
          </section>

          <section className="card">
            <h2>Add Doctor Schedule</h2>
            <form onSubmit={handleCreateSchedule}>
              <div className="form-group">
                <label htmlFor="sched-doc">Doctor</label>
                <select
                  id="sched-doc"
                  value={schedDoctorId}
                  onChange={(e) => setSchedDoctorId(e.target.value)}
                  required
                >
                  {doctors.map((d) => (
                    <option key={d.id} value={d.id}>{d.name} ({d.doc_code})</option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="sched-day">Day of Week</label>
                  <select
                    id="sched-day"
                    value={schedDay}
                    onChange={(e) => setSchedDay(e.target.value)}
                  >
                    {DAYS_OF_WEEK.map((day, idx) => (
                      <option key={day} value={idx}>{day}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="sched-dur">Slot Duration (Minutes)</label>
                  <input
                    id="sched-dur"
                    type="number"
                    value={schedDuration}
                    onChange={(e) => setSchedDuration(e.target.value)}
                    min="5"
                    max="120"
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="sched-start">Start Time</label>
                  <input
                    id="sched-start"
                    type="time"
                    value={schedStart}
                    onChange={(e) => setSchedStart(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="sched-end">End Time</label>
                  <input
                    id="sched-end"
                    type="time"
                    value={schedEnd}
                    onChange={(e) => setSchedEnd(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="sched-max">Max Patients (Daily Cap)</label>
                <input
                  id="sched-max"
                  type="number"
                  value={schedMaxPatients}
                  onChange={(e) => setSchedMaxPatients(e.target.value)}
                  min="1"
                  max="100"
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">Add Schedule</button>
            </form>
          </section>
        </div>
      )}

      {/* Tab 4: Departments */}
      {activeTab === 'departments' && (
        <div className="dashboard-grid">
          <section className="card">
            <h2>Add Department</h2>
            <form onSubmit={handleCreateDepartment}>
              <div className="form-group">
                <label htmlFor="dept-name">Department Name</label>
                <input
                  id="dept-name"
                  type="text"
                  value={newDeptName}
                  onChange={(e) => setNewDeptName(e.target.value)}
                  placeholder="Dermatology"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="dept-desc">Description</label>
                <textarea
                  id="dept-desc"
                  rows="3"
                  value={newDeptDesc}
                  onChange={(e) => setNewDeptDesc(e.target.value)}
                  placeholder="Skin and aesthetic health services"
                />
              </div>
              <button type="submit" className="btn btn-primary">Save Department</button>
            </form>
          </section>

          <section className="card">
            <h2>Existing Departments ({departments.length})</h2>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.map((d) => (
                    <tr key={d.id}>
                      <td>{d.id}</td>
                      <td><strong>{d.name}</strong></td>
                      <td>{d.description || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
