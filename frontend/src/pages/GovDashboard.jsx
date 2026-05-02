/**
 * pages/GovDashboard.jsx
 * ──────────────────────
 * Government officials see only verified cases.
 * Features: urgency badges, department filter, keyword search.
 * Clicking a case navigates to CaseDetail.jsx.
 */

import { useState, useEffect } from 'react';
import { Search, Loader2, RefreshCw } from 'lucide-react';
import Navbar from '../components/Navbar';
import CaseCard from '../components/CaseCard';
import client from '../api/client';

export default function GovDashboard() {
  const [cases, setCases] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState('');

  async function fetchAll() {
    setLoading(true);
    try {
      const [casesRes, deptsRes] = await Promise.all([
        client.get('/dashboard/cases'),
        client.get('/dashboard/departments'),
      ]);
      setCases(casesRes.data);
      setDepartments(deptsRes.data);
    } catch {
      // silently fail — show empty state
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAll();
  }, []);

  // Client-side filter for instant search UX
  const filtered = cases.filter((c) => {
    const matchSearch =
      !search ||
      c.case_number?.toLowerCase().includes(search.toLowerCase()) ||
      c.parties?.toLowerCase().includes(search.toLowerCase());
    const matchDept =
      !deptFilter || c.responsible_dept?.includes(deptFilter);
    const matchUrgency = !urgencyFilter || c.urgency === urgencyFilter;
    return matchSearch && matchDept && matchUrgency;
  });

  // Stats for header cards
  const stats = {
    total: cases.length,
    red: cases.filter((c) => c.urgency === 'red').length,
    amber: cases.filter((c) => c.urgency === 'amber').length,
    green: cases.filter((c) => c.urgency === 'green').length,
  };

  return (
    <div className="page-layout">
      <Navbar />

      <div className="dashboard-page">
        {/* Page header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Government Dashboard</h1>
            <p className="page-subtitle">Verified court orders requiring compliance action</p>
          </div>
          <button className="icon-btn" onClick={fetchAll}>
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Summary stats */}
        <div className="stats-row">
          {[
            { label: 'Total Cases', value: stats.total, color: 'stat-blue' },
            { label: 'Critical',    value: stats.red,   color: 'stat-red' },
            { label: 'Urgent',      value: stats.amber, color: 'stat-amber' },
            { label: 'On Track',    value: stats.green, color: 'stat-green' },
          ].map(({ label, value, color }) => (
            <div key={label} className={`stat-card ${color}`}>
              <span className="stat-value">{value}</span>
              <span className="stat-label">{label}</span>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="filter-bar">
          <div className="search-wrapper">
            <Search size={15} className="search-icon" />
            <input
              id="dashboard-search"
              type="text"
              placeholder="Search by case number or parties…"
              className="search-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            id="dept-filter"
            className="filter-select"
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>

          <select
            id="urgency-filter"
            className="filter-select"
            value={urgencyFilter}
            onChange={(e) => setUrgencyFilter(e.target.value)}
          >
            <option value="">All Urgency</option>
            <option value="red">Critical</option>
            <option value="amber">Urgent</option>
            <option value="green">On Track</option>
          </select>
        </div>

        {/* Cases grid */}
        {loading ? (
          <div className="page-loading">
            <Loader2 size={28} className="spin text-neutral-400" />
            <p>Loading verified cases…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="page-empty">
            <p>No verified cases found.</p>
          </div>
        ) : (
          <div className="cases-grid">
            {filtered.map((c) => (
              <CaseCard
                key={c.id}
                case={c}
                linkTo={`/dashboard/case/${c.id}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
