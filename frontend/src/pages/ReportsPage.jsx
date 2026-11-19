import React, { useCallback, useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import api, { extractErrorMessage } from '../api/client';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
);

function getTodayDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function ReportsPage() {
  const [reportDate, setReportDate] = useState(getTodayDateString());
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchReport = useCallback(async (dateStr) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/reports/daily?date=${dateStr}`);
      setReportData(res.data);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to fetch daily report.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReport(reportDate);
  }, [fetchReport, reportDate]);

  const handleDownloadCSV = () => {
    const token = localStorage.getItem('hospital_jwt_token');
    const url = `/api/reports/daily/export?date=${reportDate}`;
    // Fetch directly via Axios blob to keep auth header
    api.get(`/reports/daily/export?date=${reportDate}`, { responseType: 'blob' })
      .then((res) => {
        const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = blobUrl;
        link.setAttribute('download', `daily_appointments_${reportDate}.csv`);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
      })
      .catch((err) => {
        setError(extractErrorMessage(err, 'Failed to download CSV export.'));
      });
  };

  // Status doughnut chart config
  const statusLabels = reportData ? Object.keys(reportData.status_breakdown || {}) : [];
  const statusCounts = reportData ? Object.values(reportData.status_breakdown || {}) : [];
  const statusChartData = {
    labels: statusLabels.length ? statusLabels : ['No Data'],
    datasets: [
      {
        data: statusCounts.length ? statusCounts : [1],
        backgroundColor: [
          '#0f62fe', // BOOKED
          '#24a148', // CONFIRMED
          '#f1c21b', // IN_CONSULTATION
          '#8d8d8d', // COMPLETED
          '#da1e28', // CANCELLED
          '#a2191f', // NO_SHOW
        ],
      },
    ],
  };

  // Doctor Bar Chart config
  const docLabels = reportData ? Object.keys(reportData.doctor_distribution || {}) : [];
  const docCounts = reportData ? Object.values(reportData.doctor_distribution || {}) : [];
  const docChartData = {
    labels: docLabels,
    datasets: [
      {
        label: 'Appointments',
        data: docCounts,
        backgroundColor: '#0f62fe',
      },
    ],
  };

  // Hourly Line Chart config
  const hourlyLabels = reportData ? Object.keys(reportData.hourly_distribution || {}) : [];
  const hourlyCounts = reportData ? Object.values(reportData.hourly_distribution || {}) : [];
  const hourlyChartData = {
    labels: hourlyLabels,
    datasets: [
      {
        label: 'Patient Arrivals / Slots',
        data: hourlyCounts,
        borderColor: '#1192e8',
        backgroundColor: 'rgba(17, 146, 232, 0.2)',
        tension: 0.3,
        fill: true,
      },
    ],
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Hospital Analytics &amp; Daily Reports</h1>
          <p className="text-muted">Operational throughput, queue status breakdown, and volume patterns.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <input
            type="date"
            value={reportDate}
            onChange={(e) => setReportDate(e.target.value)}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleDownloadCSV}
          >
            Download CSV Export
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error" role="alert">{error}</div>}

      {/* Summary KPI Cards */}
      <div className="dashboard-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="card text-center">
          <h3 className="text-muted">Total Appointments</h3>
          <p style={{ fontSize: '2.25rem', fontWeight: 800, margin: '0.5rem 0' }}>
            {reportData?.total_appointments ?? 0}
          </p>
        </div>
        <div className="card text-center">
          <h3 className="text-muted">Online Bookings</h3>
          <p style={{ fontSize: '2.25rem', fontWeight: 800, margin: '0.5rem 0', color: '#0f62fe' }}>
            {reportData?.booking_type_breakdown?.ONLINE ?? 0}
          </p>
        </div>
        <div className="card text-center">
          <h3 className="text-muted">Walk-In Bookings</h3>
          <p style={{ fontSize: '2.25rem', fontWeight: 800, margin: '0.5rem 0', color: '#198038' }}>
            {reportData?.booking_type_breakdown?.WALK_IN ?? 0}
          </p>
        </div>
      </div>

      {/* Visual Charts Grid */}
      <div className="dashboard-grid">
        <section className="card">
          <h2>Appointments by Status</h2>
          <div style={{ maxHeight: '300px', display: 'flex', justifyContent: 'center' }}>
            <Doughnut data={statusChartData} options={{ maintainAspectRatio: false }} />
          </div>
        </section>

        <section className="card">
          <h2>Appointments per Doctor</h2>
          <div style={{ maxHeight: '300px' }}>
            <Bar data={docChartData} options={{ maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }} />
          </div>
        </section>

        <section className="card" style={{ gridColumn: '1 / -1' }}>
          <h2>Hourly Patient Distribution</h2>
          <div style={{ maxHeight: '280px' }}>
            <Line data={hourlyChartData} options={{ maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }} />
          </div>
        </section>
      </div>
    </div>
  );
}
