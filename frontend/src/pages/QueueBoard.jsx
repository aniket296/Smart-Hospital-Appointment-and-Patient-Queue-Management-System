import React, { useCallback, useEffect, useState } from 'react';
import api, { extractErrorMessage } from '../api/client';

function getTodayDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function QueueBoard() {
  const [departments, setDepartments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [selectedDeptId, setSelectedDeptId] = useState('');
  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [queueDate, setQueueDate] = useState(getTodayDateString());
  const [queueData, setQueueData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadFilters() {
      try {
        const [deptRes, docRes] = await Promise.all([
          api.get('/departments'),
          api.get('/doctors?active_only=true'),
        ]);
        setDepartments(deptRes.data.departments || []);
        setDoctors(docRes.data.doctors || []);
      } catch (err) {
        setError(extractErrorMessage(err, 'Failed to load filter metadata.'));
      }
    }
    loadFilters();
  }, []);

  const fetchQueue = useCallback(async () => {
    try {
      let url = `/queue?date=${queueDate}`;
      if (selectedDoctorId) url += `&doctor_id=${selectedDoctorId}`;
      if (selectedDeptId) url += `&department_id=${selectedDeptId}`;
      const res = await api.get(url);
      setQueueData(res.data);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to fetch live queue data.'));
    }
  }, [queueDate, selectedDoctorId, selectedDeptId]);

  useEffect(() => {
    fetchQueue();
    // 5.9: React Queue Board polls every 5-10 seconds
    const interval = setInterval(() => {
      fetchQueue();
    }, 6000);
    return () => clearInterval(interval);
  }, [fetchQueue]);

  const filteredDoctors = selectedDeptId
    ? doctors.filter((d) => String(d.department_id) === String(selectedDeptId))
    : doctors;

  const currentServing = queueData?.current_in_consultation;
  const waitingList = queueData?.next_waiting || [];

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Outpatient Live Queue Board</h1>
          <p className="text-muted">
            Auto-refreshing every 6s {lastRefreshed && `(Last updated: ${lastRefreshed})`}
          </p>
        </div>
        <div className="queue-controls" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <div>
            <label htmlFor="q-dept" className="text-xs">Dept:</label>
            <select
              id="q-dept"
              value={selectedDeptId}
              onChange={(e) => {
                setSelectedDeptId(e.target.value);
                setSelectedDoctorId('');
              }}
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="q-doc" className="text-xs">Doctor:</label>
            <select
              id="q-doc"
              value={selectedDoctorId}
              onChange={(e) => setSelectedDoctorId(e.target.value)}
            >
              <option value="">All Doctors</option>
              {filteredDoctors.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.doc_code})</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="q-date" className="text-xs">Date:</label>
            <input
              id="q-date"
              type="date"
              value={queueDate}
              onChange={(e) => setQueueDate(e.target.value)}
            />
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}

      <div className="queue-display-grid">
        <section className="card current-serving-hero">
          <div className="serving-header">NOW CONSULTING</div>
          {currentServing ? (
            <div className="serving-body">
              <div className="large-token">{currentServing.token_number}</div>
              <div className="serving-details">
                <h3>{currentServing.patient_name}</h3>
                <p>Doctor: <strong>{currentServing.doctor_name}</strong> ({currentServing.room_number})</p>
                <p className="text-muted">Slot: {currentServing.slot_time} | Dept: {currentServing.department_name}</p>
              </div>
            </div>
          ) : (
            <div className="no-serving">
              <p>No token currently in consultation.</p>
            </div>
          )}
        </section>

        <section className="card">
          <h2>Upcoming Patients ({waitingList.length})</h2>
          {waitingList.length === 0 ? (
            <p className="text-muted">No patients currently waiting in queue.</p>
          ) : (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Time</th>
                    <th>Doctor</th>
                    <th>Room</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {waitingList.map((item) => (
                    <tr key={item.id}>
                      <td><span className="token-pill">{item.token_number}</span></td>
                      <td>{item.slot_time}</td>
                      <td>{item.doctor_name}</td>
                      <td>{item.room_number}</td>
                      <td>
                        <span className={`status-badge status-${item.status.toLowerCase()}`}>
                          {item.status}
                        </span>
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
