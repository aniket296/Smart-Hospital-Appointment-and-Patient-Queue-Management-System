import React, { useCallback, useEffect, useState } from 'react';
import api, { extractErrorMessage } from '../api/client';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchNotifications = useCallback(async (targetPage = 1) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/notifications?page=${targetPage}&per_page=15`);
      setNotifications(res.data.notifications || []);
      setTotalPages(res.data.pages || 1);
      setPage(res.data.page || 1);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to fetch notification logs.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications(page);
  }, [fetchNotifications, page]);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Notification Logs</h1>
          <p className="text-muted">Audit trail of email (SMTP / Simulated) and simulated SMS alerts.</p>
        </div>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}

      <div className="card">
        {loading ? (
          <p className="text-muted">Loading notifications...</p>
        ) : notifications.length === 0 ? (
          <p className="text-muted">No notification logs recorded.</p>
        ) : (
          <>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Channel</th>
                    <th>Recipient</th>
                    <th>Event</th>
                    <th>Subject &amp; Message</th>
                    <th>Delivery Mode</th>
                  </tr>
                </thead>
                <tbody>
                  {notifications.map((n) => (
                    <tr key={n.id}>
                      <td><small className="text-muted">{n.created_at}</small></td>
                      <td>
                        <span className={`status-badge ${n.channel === 'EMAIL' ? 'status-booked' : 'status-confirmed'}`}>
                          {n.channel}
                        </span>
                      </td>
                      <td><code>{n.recipient}</code></td>
                      <td><strong>{n.event_type}</strong></td>
                      <td>
                        <div><strong>{n.subject}</strong></div>
                        <small className="text-muted">{n.message}</small>
                        {n.error_message && (
                          <div className="text-xs" style={{ color: '#b91c1c' }}>
                            Fallback reason: {n.error_message}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`status-badge ${n.delivery_mode === 'SMTP_SENT' ? 'status-confirmed' : 'status-completed'}`}>
                          {n.delivery_mode}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', justifyContent: 'center' }}>
                <button
                  type="button"
                  className="btn btn-sm btn-outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </button>
                <span style={{ alignSelf: 'center', fontSize: '0.88rem' }}>
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  className="btn btn-sm btn-outline"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
