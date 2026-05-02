/**
 * pages/StudentPortal.jsx
 * ───────────────────────
 * Main page for law students.
 * Layout: Left panel (PDF viewer) | Right panel (Quiz)
 * Flow:
 *  1. Student selects / uploads a case PDF
 *  2. PDF renders on left
 *  3. 5 quiz questions appear on right
 *  4. On submission: match score shown, AI answers revealed
 *  5. Clicking a result highlights the source page in PDF
 */

import { useState, useEffect } from 'react';
import { Upload, Loader2, RefreshCw } from 'lucide-react';
import Navbar from '../components/Navbar';
import PDFViewer from '../components/PDFViewer';
import QuizPanel from '../components/QuizPanel';
import CaseCard from '../components/CaseCard';
import client from '../api/client';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function StudentPortal() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [highlightPage, setHighlightPage] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loadingCases, setLoadingCases] = useState(true);
  const [error, setError] = useState('');

  // Load student's cases on mount
  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setLoadingCases(true);
    try {
      const { data } = await client.get('/cases/');
      setCases(data);
    } catch {
      setError('Failed to load cases.');
    } finally {
      setLoadingCases(false);
    }
  };

  // When a case is selected, load its questions
  const selectCase = async (c) => {
    setSelectedCase(c);
    setHighlightPage(null);
    try {
      const { data } = await client.get(`/quiz/${c.id}`);
      setQuestions(data);
    } catch {
      setQuestions([]);
    }
  };

  // Upload a new PDF
  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data: uploaded } = await client.post('/cases/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // Trigger extraction immediately after upload
      await client.post(`/extract/${uploaded.case_id}`);

      // Refresh case list
      await fetchCases();
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  // After quiz submitted, optionally jump PDF to a source page
  const handleQuizSubmitted = (result) => {
    // In Phase 6 we map source references to page numbers
    // For now: no page jump
  };

  const pdfUrl = selectedCase
    ? `${API_BASE}/${selectedCase.pdf_path}`
    : null;

  return (
    <div className="page-layout">
      <Navbar />

      <div className="student-layout">
        {/* ── Left sidebar: case list ──────────────────────────────────────── */}
        <aside className="case-sidebar">
          <div className="sidebar-header">
            <h2 className="sidebar-title">My Cases</h2>
            <div className="sidebar-actions">
              <button className="icon-btn" onClick={fetchCases} title="Refresh">
                <RefreshCw size={15} />
              </button>
              <label className="upload-btn" title="Upload PDF">
                {uploading ? <Loader2 size={15} className="spin" /> : <Upload size={15} />}
                <span>{uploading ? 'Uploading…' : 'Upload PDF'}</span>
                <input
                  id="pdf-upload-input"
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={handleUpload}
                  disabled={uploading}
                />
              </label>
            </div>
          </div>

          {error && <p className="sidebar-error">{error}</p>}

          <div className="case-list">
            {loadingCases ? (
              <div className="list-loading">
                <Loader2 size={20} className="spin text-neutral-400" />
                <span>Loading cases…</span>
              </div>
            ) : cases.length === 0 ? (
              <div className="list-empty">
                <p>No cases yet.</p>
                <p className="text-sm text-neutral-500">Upload a court PDF to get started.</p>
              </div>
            ) : (
              cases.map((c) => (
                <div
                  key={c.id}
                  className={`case-list-item ${selectedCase?.id === c.id ? 'case-list-item-active' : ''}`}
                  onClick={() => selectCase(c)}
                >
                  <CaseCard case={c} />
                </div>
              ))
            )}
          </div>
        </aside>

        {/* ── Centre: PDF viewer ───────────────────────────────────────────── */}
        <main className="pdf-main">
          <PDFViewer pdfUrl={pdfUrl} highlightPage={highlightPage} />
        </main>

        {/* ── Right panel: Quiz ────────────────────────────────────────────── */}
        <aside className="quiz-sidebar">
          {selectedCase ? (
            <QuizPanel
              caseId={selectedCase.id}
              questions={questions}
              onSubmitted={handleQuizSubmitted}
            />
          ) : (
            <div className="quiz-placeholder">
              <p>Select a case to start the quiz</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
