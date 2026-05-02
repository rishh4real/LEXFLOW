/**
 * pages/AdminPanel.jsx
 * ─────────────────────
 * Admin-only panel with two tabs:
 *  Tab 1 — Flagged Cases: shows AI answer vs student answer, approve/reject controls
 *  Tab 2 — Manage Users:  invite code generation, user list
 */

import { useState, useEffect } from 'react';
import { Shield, Users, Loader2, CheckCircle, XCircle, Copy } from 'lucide-react';
import Navbar from '../components/Navbar';
import client from '../api/client';

export default function AdminPanel() {
  const [tab, setTab] = useState('flagged');
  const [flagged, setFlagged] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inviteCode, setInviteCode] = useState('');
  const [generatingCode, setGeneratingCode] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  async function fetchFlagged() {
    setLoading(true);
    try {
      const { data } = await client.get('/verify/flagged');
      setFlagged(data);
    } catch { /* empty */ }
    finally { setLoading(false); }
  }

  useEffect(() => { fetchFlagged(); }, []);

  const handleVerify = async (caseId, action) => {
    setActionLoading(prev => ({ ...prev, [caseId]: true }));
    try {
      await client.post(`/verify/${caseId}`, { action });
      setFlagged(prev => prev.filter(c => c.id !== caseId));
    } catch { /* show toast in Phase 6 */ }
    finally {
      setActionLoading(prev => ({ ...prev, [caseId]: false }));
    }
  };

  const generateInvite = async () => {
    setGeneratingCode(true);
    try {
      const { data } = await client.post('/auth/invite');
      setInviteCode(data.invite_code);
    } catch { /* */ }
    finally { setGeneratingCode(false); }
  };

  const copyCode = () => navigator.clipboard.writeText(inviteCode);

  return (
    <div className="page-layout animate-in">
      <Navbar />
      <div className="admin-page animate-in delay-1">
        <div className="page-header">
          <div className="page-header-copy">
            <h1 className="page-title">Admin Panel</h1>
            <p className="page-subtitle">Review flagged cases and manage user access</p>
          </div>
        </div>

        {/* Tab bar */}
        <div className="tab-bar">
          <button
            id="tab-flagged"
            className={`tab-btn ${tab === 'flagged' ? 'tab-active' : ''}`}
            onClick={() => setTab('flagged')}
          >
            <Shield size={15} /> Flagged Cases
            {flagged.length > 0 && <span className="tab-badge">{flagged.length}</span>}
          </button>
          <button
            id="tab-users"
            className={`tab-btn ${tab === 'users' ? 'tab-active' : ''}`}
            onClick={() => setTab('users')}
          >
            <Users size={15} /> Manage Users
          </button>
        </div>

        {/* ── Tab 1: Flagged Cases ─────────────────────────────────────────── */}
        {tab === 'flagged' && (
          <div className="flagged-list">
            {loading ? (
              <div className="page-loading">
                <Loader2 size={24} className="spin text-neutral-400" />
                <p>Loading flagged cases…</p>
              </div>
            ) : flagged.length === 0 ? (
              <div className="page-empty">
                <CheckCircle size={36} className="text-white" />
                <p>No flagged cases. All clear!</p>
              </div>
            ) : (
              flagged.map((c) => (
                <div key={c.id} className="flagged-card">
                  <div className="flagged-header">
                    <div>
                      <h3 className="flagged-case-num">{c.case_number || `Case #${c.id}`}</h3>
                      <p className="flagged-student">
                        Student: {c.student_name} ({c.student_email})
                      </p>
                    </div>
                    <div className="flagged-score">
                      <span className="score-pill score-low">
                        {c.match_score?.toFixed(1)}% match
                      </span>
                    </div>
                  </div>

                  <p className="flagged-meta">Submitted: {c.submitted_at}</p>

                  {/* Action buttons */}
                  <div className="flagged-actions">
                    <button
                      id={`approve-${c.id}`}
                      className="action-approve"
                      disabled={actionLoading[c.id]}
                      onClick={() => handleVerify(c.id, 'approve')}
                    >
                      {actionLoading[c.id]
                        ? <Loader2 size={14} className="spin" />
                        : <CheckCircle size={14} />}
                      Approve
                    </button>
                    <button
                      id={`reject-${c.id}`}
                      className="action-reject"
                      disabled={actionLoading[c.id]}
                      onClick={() => handleVerify(c.id, 'reject')}
                    >
                      <XCircle size={14} /> Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* ── Tab 2: Manage Users ──────────────────────────────────────────── */}
        {tab === 'users' && (
          <div className="users-panel">
            <div className="invite-section">
              <h3 className="section-label">Generate Student Invite Code</h3>
              <p className="text-neutral-400 text-sm mb-4">
                Share this code with a student so they can register.
              </p>
              <div className="invite-row">
                <button
                  id="generate-invite-btn"
                  className="invite-btn"
                  onClick={generateInvite}
                  disabled={generatingCode}
                >
                  {generatingCode ? <Loader2 size={15} className="spin" /> : 'Generate Code'}
                </button>
                {inviteCode && (
                  <div className="invite-code-display">
                    <code className="invite-code">{inviteCode}</code>
                    <button className="copy-btn" onClick={copyCode} title="Copy">
                      <Copy size={14} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
