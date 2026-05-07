import { useCallback, useEffect, useState } from 'react';
import { Shield, Users, Loader2, CheckCircle, XCircle, Copy, Upload, FileText, History, RefreshCw } from 'lucide-react';
import Navbar from '../components/Navbar';
import client from '../api/client';

export default function AdminPanel() {
  const [tab, setTab] = useState('flagged');
  const [flagged, setFlagged] = useState([]);
  const [uploadedCases, setUploadedCases] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inviteCode, setInviteCode] = useState('');
  const [generatingCode, setGeneratingCode] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === 'flagged') {
        const { data } = await client.get('/verify/flagged');
        setFlagged(data);
      } else if (tab === 'history') {
        const { data } = await client.get('/cases/');
        setUploadedCases(data);
      } else if (tab === 'users') {
        const { data } = await client.get('/admin/users');
        setUsers(data);
      }
    } catch (err) {
      console.error('Failed to load admin data', err);
    }
    finally { setLoading(false); }
  }, [tab]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setExtracting(false);
    setUploadError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data: uploaded } = await client.post('/cases/upload', formData);
      // Extraction can take a while (OCR + LLM). Show separate UI state.
      setUploading(false);
      setExtracting(true);
      await client.post(`/extract/${uploaded.case_id}`);
      alert('Case uploaded and AI extraction completed!');
      setTab('history');
    } catch (err) {
      // Prefer backend's error detail so the admin sees the real cause
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Upload failed. Please check backend.';
      setUploadError(detail);
    } finally {
      setUploading(false);
      setExtracting(false);
    }
  };

  const handleVerify = async (caseId, action) => {
    setActionLoading(prev => ({ ...prev, [caseId]: true }));
    try {
      await client.post(`/verify/${caseId}`, { action });
      setFlagged(prev => prev.filter(c => c.id !== caseId));
    } catch (err) {
      console.error('Failed to verify case', err);
    }
    finally { setActionLoading(prev => ({ ...prev, [caseId]: false })); }
  };

  const generateInvite = async () => {
    setGeneratingCode(true);
    try {
      const { data } = await client.post('/auth/invite');
      setInviteCode(data.invite_code);
      fetchData();
    } catch (err) {
      console.error('Failed to generate invite', err);
    }
    finally { setGeneratingCode(false); }
  };

  const answerFor = (caseItem, question) => {
    const breakdown = caseItem.submission?.breakdown || [];
    const match = breakdown.find((item) => item.question_id === question.id || item.question_id === String(question.id));
    const studentAnswer =
      match?.student_answer ||
      caseItem.submission?.answers?.[question.id] ||
      caseItem.submission?.answers?.[String(question.id)] ||
      'No answer submitted';
    const aiAnswer = match?.ai_answer || question.correct_answer || 'No AI answer available';
    const score = typeof match?.score === 'number' ? match.score : null;
    return { studentAnswer, aiAnswer, score, matched: match?.match };
  };

  const hasStudentSubmission = (caseItem) =>
    Boolean(caseItem.submission || caseItem.submitted_at || caseItem.student_name);

  return (
    <div className="page-layout animate-in">
      <Navbar />
      <div className="admin-page animate-in delay-1 pb-20">
        <div className="page-header">
          <h1 className="page-title">Admin Management</h1>
          <p className="page-subtitle">Oversee cases, users, and system integrity</p>
        </div>

        {/* Tab bar */}
        <div className="tab-bar">
          <button className={`tab-btn ${tab === 'flagged' ? 'tab-active' : ''}`} onClick={() => setTab('flagged')}>
            <Shield size={15} /> Flagged
            {flagged.length > 0 && <span className="tab-badge">{flagged.length}</span>}
          </button>
          <button className={`tab-btn ${tab === 'upload' ? 'tab-active' : ''}`} onClick={() => setTab('upload')}>
            <Upload size={15} /> Upload Case
          </button>
          <button className={`tab-btn ${tab === 'history' ? 'tab-active' : ''}`} onClick={() => setTab('history')}>
            <History size={15} /> Uploaded Cases
            {uploadedCases.length > 0 && <span className="tab-badge">{uploadedCases.length}</span>}
          </button>
          <button className={`tab-btn ${tab === 'users' ? 'tab-active' : ''}`} onClick={() => setTab('users')}>
            <Users size={15} /> Active Users
          </button>
        </div>

        {/* ── Tab: Upload ──────────────────────────────────────────────────── */}
        {tab === 'upload' && (
          <div className="bg-white/5 border border-white/10 p-12 rounded-2xl flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center mb-6">
              <Upload size={32} className="text-white" />
            </div>
            <h2 className="text-xl font-bold mb-2">Upload New Judgment</h2>
            <p className="text-neutral-400 text-sm mb-8 max-w-sm">
              Uploading a PDF will automatically start the AI extraction process and assign it for verification.
            </p>
            <label className="bg-white text-black px-8 py-3 rounded-xl font-bold cursor-pointer hover:bg-neutral-200 transition-colors">
              {(uploading || extracting) ? <Loader2 className="spin" /> : null}
              <span className="ml-2">
                {uploading ? 'Uploading...' : extracting ? 'Extracting...' : 'Select PDF File'}
              </span>
              <input
                type="file"
                accept=".pdf,.PDF"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading || extracting}
              />
            </label>
            {uploadError && <p className="text-red-500 mt-4 text-xs font-bold">{uploadError}</p>}
          </div>
        )}

        {/* ── Tab: Uploaded History ───────────────────────────────────────── */}
        {tab === 'history' && (
          <div className="history-panel">
            <div className="history-toolbar">
              <div>
                <h2 className="history-title">Uploaded Cases</h2>
                <p className="history-subtitle">Every judgment uploaded by admin appears here, including pending student quizzes.</p>
              </div>
              <button className="icon-btn" onClick={fetchData} title="Refresh uploads">
                <RefreshCw size={15} />
              </button>
            </div>

            {loading ? (
              <div className="page-loading"><Loader2 size={24} className="spin text-neutral-400" /></div>
            ) : uploadedCases.length === 0 ? (
              <div className="page-empty"><p>No uploaded cases yet.</p></div>
            ) : (
              <div className="history-list">
                {uploadedCases.map((c) => (
                  <div key={c.id} className="history-card">
                    <div className="history-card-main">
                      <div>
                        <div className="case-number-pill">
                          <FileText size={13} />
                          <span>{c.case_number || `Case #${c.id}`}</span>
                        </div>
                        <h3>{c.parties || 'Parties not extracted yet'}</h3>
                        <p>{c.key_directions || 'AI direction not extracted yet'}</p>
                      </div>
                      <span className={`status-chip status-${c.status}`}>{c.status?.toUpperCase() || 'PENDING'}</span>
                    </div>
                    <div className="history-meta">
                      <span>Uploaded {c.created_at ? new Date(c.created_at).toLocaleString() : 'recently'}</span>
                      <span>{c.responsible_dept || 'Department pending'}</span>
                      <span>{c.compliance_deadline ? `Deadline ${c.compliance_deadline}` : 'Deadline pending'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tab: Flagged ─────────────────────────────────────────────────── */}
        {tab === 'flagged' && (
          <div className="flagged-list">
            {loading ? <div className="page-loading"><Loader2 size={24} className="spin text-neutral-400" /></div> :
             flagged.length === 0 ? <div className="page-empty"><p>No flagged cases.</p></div> :
             flagged.map((c) => (
              <div key={c.id} className="flagged-card">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-lg">{c.case_number}</h3>
                    {c.student_name ? (
                      <p className="text-xs text-neutral-400">Student: {c.student_name}</p>
                    ) : (
                      <p className="text-xs text-neutral-500 italic">
                        Uploaded by {c.uploaded_by_role === 'admin' ? 'Admin' : (c.uploaded_by_name || 'Admin')}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <span className="bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">
                      {c.match_score?.toFixed(1)}% Match
                    </span>
                  </div>
                </div>

                <div className="admin-review-summary">
                  <div>
                    <span className="admin-review-label">Parties</span>
                    <p>{c.parties || 'Not extracted'}</p>
                  </div>
                  <div>
                    <span className="admin-review-label">Department</span>
                    <p>{c.responsible_dept || 'Not extracted'}</p>
                  </div>
                  <div>
                    <span className="admin-review-label">Deadline</span>
                    <p>{c.compliance_deadline || 'Not extracted'}</p>
                  </div>
                  <div>
                    <span className="admin-review-label">AI Direction</span>
                    <p>{c.key_directions || 'Not extracted'}</p>
                  </div>
                </div>

                {hasStudentSubmission(c) ? (
                  <div className="admin-answer-review">
                    <div className="admin-answer-title">
                      <FileText size={14} />
                      Student vs AI Answers
                    </div>
                    {(c.questions || []).length > 0 ? (c.questions || []).map((q) => {
                      const answer = answerFor(c, q);
                      return (
                        <div key={q.id} className="admin-answer-row">
                          <div className="admin-question-line">
                            <span>Q{q.question_order}</span>
                            <p>{q.question_text}</p>
                            {answer.score !== null && (
                              <b className={answer.matched ? 'answer-pass' : 'answer-fail'}>
                                {answer.score}%
                              </b>
                            )}
                          </div>
                          <div className="answer-columns">
                            <div>
                              <label>Student answer</label>
                              <p>{answer.studentAnswer}</p>
                            </div>
                            <div>
                              <label>AI answer</label>
                              <p>{answer.aiAnswer}</p>
                            </div>
                          </div>
                        </div>
                      );
                    }) : (
                      <div className="admin-answer-row">
                        <p className="text-xs text-neutral-400">
                          Student submitted this quiz, but detailed question data is missing for this older record.
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="admin-answer-empty">
                    Student has not submitted the quiz yet. Keep this pending until answers arrive.
                  </div>
                )}

                <div className="flex gap-2 mt-6">
                  <button disabled={actionLoading[c.id]} onClick={() => handleVerify(c.id, 'approve')} className="bg-white text-black flex-1 py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-2">
                    {actionLoading[c.id] ? <Loader2 size={14} className="spin" /> : <CheckCircle size={14}/>} Approve
                  </button>
                  <button disabled={actionLoading[c.id]} onClick={() => handleVerify(c.id, 'reject')} className="bg-black border border-white/20 text-white flex-1 py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-2">
                    {actionLoading[c.id] ? <Loader2 size={14} className="spin" /> : <XCircle size={14}/>} Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Tab: Users ───────────────────────────────────────────────────── */}
        {tab === 'users' && (
          <div className="space-y-8">
            <div className="bg-white/5 border border-white/10 p-6 rounded-2xl">
              <h3 className="text-sm font-bold mb-4 uppercase tracking-widest text-neutral-400">Invite New Student</h3>
              <div className="flex gap-4">
                <button onClick={generateInvite} disabled={generatingCode} className="bg-white text-black px-6 py-2 rounded-xl font-bold text-xs">
                  {generatingCode ? <Loader2 size={14} className="spin" /> : 'Generate Code'}
                </button>
                {inviteCode && (
                  <div className="flex-1 bg-black border border-white/10 rounded-xl px-4 flex items-center justify-between">
                    <code className="text-xs font-mono">{inviteCode}</code>
                    <button onClick={() => navigator.clipboard.writeText(inviteCode)} className="text-neutral-400 hover:text-white"><Copy size={14}/></button>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-white/10 border-b border-white/10">
                  <tr>
                    <th className="px-6 py-4">NAME</th>
                    <th className="px-6 py-4">EMAIL</th>
                    <th className="px-6 py-4">ROLE</th>
                    <th className="px-6 py-4">JOINED</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {users.map(u => (
                    <tr key={u.id} className="hover:bg-white/5">
                      <td className="px-6 py-4 font-bold">{u.name}</td>
                      <td className="px-6 py-4 text-neutral-400">{u.email}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-[10px] font-black uppercase ${
                          u.role === 'admin' ? 'bg-purple-500/20 text-purple-400' : 
                          u.role === 'official' ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-neutral-500">{u.created_at?.split('T')[0]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
