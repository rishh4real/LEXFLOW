/**
 * pages/StudentPortal.jsx
 * ───────────────────────
 * Main page for law students.
 * Layout: Left panel (case list) | Centre (PDF viewer) | Right panel (Quiz)
 * Flow:
 *  1. Admin uploads a case → it appears here automatically
 *  2. Student picks a case → PDF renders on left
 *  3. 5 quiz questions appear on right
 *  4. On submission: match score shown, AI answers revealed
 */

import { useState, useEffect } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import Navbar from '../components/Navbar';
import PDFViewer from '../components/PDFViewer';
import QuizPanel from '../components/QuizPanel';
import CaseCard from '../components/CaseCard';
import client, { API_BASE } from '../api/client';

export default function StudentPortal() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [highlightPage, setHighlightPage] = useState(null);
  const [loadingCases, setLoadingCases] = useState(true);
  const [error, setError] = useState('');

  async function fetchCases() {
    setLoadingCases(true);
    try {
      const { data } = await client.get('/cases/');
      setCases(data);
      setError('');
    } catch {
      setError('Failed to load cases.');
    } finally {
      setLoadingCases(false);
    }
  }

  useEffect(() => { fetchCases(); }, []);

  // When a case is selected, load its quiz questions
  const selectCase = async (c) => {
    setSelectedCase(c);
    setQuestions([]);
    setHighlightPage(null);
    try {
      const { data } = await client.get(`/quiz/${c.id}`);
      setQuestions(data);
    } catch {
      setQuestions([]);
    }
  };

  const handleQuizSubmitted = () => {
    // After submission, admin sees the flagged case with comparison view
  };

  const pdfUrl = selectedCase
    ? selectedCase.pdf_url
      ? (selectedCase.pdf_url.startsWith('http')
          ? selectedCase.pdf_url
          : `${API_BASE}${selectedCase.pdf_url.startsWith('/') ? '' : '/'}${selectedCase.pdf_url}`)
      : (selectedCase.pdf_path ? `${API_BASE}/${selectedCase.pdf_path}` : null)
    : null;

  return (
    <div className="page-layout animate-in">
      <Navbar />

      <div className="student-layout animate-in delay-1">
        {/* ── Left sidebar: case list ──────────────────────────────────────── */}
        <aside className="case-sidebar">
          <div className="sidebar-header">
            <h2 className="sidebar-title">My Cases</h2>
            <div className="sidebar-actions">
              <button className="icon-btn" onClick={fetchCases} title="Refresh">
                <RefreshCw size={15} />
              </button>
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
                <p>No cases assigned yet.</p>
                <p className="text-sm text-neutral-500">Admin will upload cases for you to study.</p>
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
