import { useState, useEffect } from 'react';
import { Search, Loader2, RefreshCw, Users, Upload, CheckCircle2 } from 'lucide-react';
import Navbar from '../components/Navbar';
import CaseCard from '../components/CaseCard';
import NotificationTicker from '../components/NotificationTicker';
import ChatBot from '../components/ChatBot';
import client from '../api/client';

export default function GovDashboard() {
  const [view, setView] = useState('cases'); // 'cases' or 'students'
  const [cases, setCases] = useState([]);
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deptFilter, setDeptFilter] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState('');
  const [uploading, setUploading] = useState(false);

  async function fetchData() {
    setLoading(true);
    try {
      if (view === 'cases') {
        const [casesRes, deptsRes] = await Promise.all([
          client.get('/dashboard/cases'),
          client.get('/dashboard/departments'),
        ]);
        setCases(casesRes.data);
        setDepartments(deptsRes.data);
      } else {
        const { data } = await client.get('/admin/users'); // Reuse admin route
        setUsers(data.filter(u => u.role === 'student'));
      }
    } catch { } finally { setLoading(false); }
  }

  useEffect(() => { fetchData(); }, [view]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data: uploaded } = await client.post('/cases/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      await client.post(`/extract/${uploaded.case_id}`);
      alert('Judgment uploaded successfully!');
      fetchData();
    } catch { alert('Upload failed'); }
    finally { setUploading(false); }
  };

  const filtered = cases.filter((c) => {
    const matchSearch = !search || c.case_number?.toLowerCase().includes(search.toLowerCase()) || c.parties?.toLowerCase().includes(search.toLowerCase());
    const matchDept = !deptFilter || c.responsible_dept?.includes(deptFilter);
    const matchUrgency = !urgencyFilter || c.urgency === urgencyFilter;
    return matchSearch && matchDept && matchUrgency;
  });

  const stats = {
    total: cases.length,
    red: cases.filter((c) => c.urgency === 'red').length,
    students: users.length
  };

  return (
    <div className="page-layout animate-in relative">
      <NotificationTicker />
      <Navbar />

      <div className="dashboard-page animate-in delay-1 pb-20">
        <div className="page-header">
          <div>
            <h1 className="page-title">Compliance Dashboard</h1>
            <p className="page-subtitle">Monitoring legal orders and student activity</p>
          </div>
          <div className="flex gap-2">
            <label className="bg-white text-black px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 cursor-pointer hover:bg-neutral-200">
              {uploading ? <Loader2 className="spin" size={14}/> : <Upload size={14}/>}
              <span>{uploading ? 'Processing...' : 'Upload Judgment'}</span>
              <input type="file" className="hidden" accept=".pdf" onChange={handleUpload} disabled={uploading}/>
            </label>
            <button className="icon-btn" onClick={fetchData}><RefreshCw size={16} /></button>
          </div>
        </div>

        {/* View Switcher */}
        <div className="flex gap-4 mb-8 border-b border-white/10 pb-4">
          <button onClick={() => setView('cases')} className={`text-sm font-bold pb-2 transition-all ${view === 'cases' ? 'text-white border-b-2 border-white' : 'text-neutral-500'}`}>
            Verified Cases
          </button>
          <button onClick={() => setView('students')} className={`text-sm font-bold pb-2 transition-all ${view === 'students' ? 'text-white border-b-2 border-white' : 'text-neutral-500'}`}>
            Active Students
          </button>
        </div>

        {view === 'cases' ? (
          <>
            <div className="stats-row">
              {[
                { label: 'Total Cases', value: stats.total, color: 'stat-blue' },
                { label: 'Critical',    value: stats.red,   color: 'stat-red' },
                { label: 'Departments', value: departments.length, color: 'stat-green' },
              ].map(({ label, value, color }) => (
                <div key={label} className={`stat-card ${color}`}>
                  <span className="stat-value">{value}</span>
                  <span className="stat-label">{label}</span>
                </div>
              ))}
            </div>

            <div className="filter-bar">
              <div className="search-wrapper">
                <Search size={15} className="search-icon" />
                <input
                  type="text"
                  placeholder="Search cases..."
                  className="search-input"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>

              <select className="filter-select" value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}>
                <option value="">All Departments</option>
                {departments.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            {loading ? <div className="page-loading"><Loader2 className="spin" /></div> :
             filtered.length === 0 ? <div className="page-empty"><p>No cases found.</p></div> :
             <div className="cases-grid">
               {filtered.map((c) => (
                 <CaseCard key={c.id} case={c} linkTo={`/dashboard/case/${c.id}`} />
               ))}
             </div>
            }
          </>
        ) : (
          <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden animate-in">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/10 border-b border-white/10">
                <tr>
                  <th className="px-6 py-4">STUDENT NAME</th>
                  <th className="px-6 py-4">EMAIL</th>
                  <th className="px-6 py-4">STATUS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-white/5">
                    <td className="px-6 py-4 font-bold flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      {u.name}
                    </td>
                    <td className="px-6 py-4 text-neutral-400">{u.email}</td>
                    <td className="px-6 py-4"><span className="text-[10px] bg-white/10 px-2 py-1 rounded font-black">ACTIVE</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ChatBot />
    </div>
  );
}
