/**
 * pages/CaseDetail.jsx
 * Full case view for government officials.
 * Shows: action plan, source references, status tracker, PDF viewer.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Building2, Calendar, Clock3, Scale, CheckCircle2 } from 'lucide-react';
import Navbar from '../components/Navbar';
import PDFViewer from '../components/PDFViewer';
import UrgencyBadge from '../components/UrgencyBadge';
import client from '../api/client';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STATUS_STEPS = ['Pending', 'In Progress', 'Complied', 'Appeal Filed'];

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [highlightPage, setHighlightPage] = useState(null);

  useEffect(() => {
    client.get(`/dashboard/cases/${id}`)
      .then(r => setData(r.data))
      .catch(() => setError('Failed to load case.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="page-layout"><Navbar />
      <div className="page-loading"><Loader2 size={28} className="spin text-neutral-400" /><p>Loading case…</p></div>
    </div>
  );

  if (error || !data) return (
    <div className="page-layout"><Navbar />
      <div className="page-empty">
        <p className="text-white">{error}</p>
        <button className="back-btn" onClick={() => navigate(-1)}><ArrowLeft size={15} /> Back</button>
      </div>
    </div>
  );

  const { case: c, extraction, urgency } = data;
  const actionPlan = extraction?.action_plan || {};
  const sourceRefs = extraction?.source_references || {};
  const pdfUrl = c.pdf_path ? `${API_BASE}/${c.pdf_path}` : null;

  return (
    <div className="page-layout animate-in">
      <Navbar />
      <div className="case-detail-layout animate-in delay-1">
        {/* Left info panel */}
        <div className="case-detail-info">
          <button className="back-btn" onClick={() => navigate(-1)}>
            <ArrowLeft size={15} /> Back to Dashboard
          </button>
          <div className="detail-header">
            <div className="detail-title-row">
              <h1 className="detail-case-num">{c.case_number || `Case #${c.id}`}</h1>
              <UrgencyBadge urgency={urgency} deadline={extraction?.compliance_deadline} />
            </div>
            <p className="detail-parties">{extraction?.parties}</p>
          </div>

          <div className="detail-facts">
            {[
              { Icon: Scale,     label: 'Parties',       value: extraction?.parties },
              { Icon: Calendar,  label: 'Order Date',    value: extraction?.date_of_order },
              { Icon: Calendar,  label: 'Deadline',      value: extraction?.compliance_deadline },
              { Icon: Clock3,    label: 'Appeal Window', value: extraction?.appeal_window },
              { Icon: Building2, label: 'Department',    value: extraction?.responsible_dept },
            ].filter(f => f.value).map(({ Icon, label, value }) => (
              <div key={label} className="fact-row">
                <Icon size={14} className="fact-icon" />
                <span className="fact-label">{label}</span>
                <span className="fact-value">{value}</span>
              </div>
            ))}
          </div>

          {actionPlan.required_action && (
            <div className={`action-plan action-${actionPlan.recommendation}`}>
              <h3 className="action-title">
                {actionPlan.recommendation === 'comply' ? '✓ Comply' : '⚠ Consider Appeal'}
              </h3>
              <p className="action-body">{actionPlan.required_action}</p>
            </div>
          )}

          {extraction?.key_directions && (
            <div className="key-directions">
              <h3 className="section-label">Key Directions</h3>
              <p className="directions-text">{extraction.key_directions}</p>
            </div>
          )}

          {Object.keys(sourceRefs).length > 0 && (
            <div className="source-refs">
              <h3 className="section-label">Source References</h3>
              {Object.entries(sourceRefs).map(([field, sentence]) => (
                <div key={field} className="source-ref-item" onClick={() => setHighlightPage(1)}>
                  <span className="source-field">{field.replace(/_/g, ' ')}</span>
                  <blockquote className="source-sentence">"{sentence}"</blockquote>
                </div>
              ))}
            </div>
          )}

          <div className="status-tracker">
            <h3 className="section-label">Compliance Status</h3>
            <div className="tracker-steps">
              {STATUS_STEPS.map((step, i) => (
                <div key={step} className={`tracker-step ${i === 0 ? 'step-active' : 'step-pending'}`}>
                  <div className="step-dot">
                    {i === 0 ? <CheckCircle2 size={14} /> : <div className="dot-inner" />}
                  </div>
                  <span className="step-label">{step}</span>
                  {i < STATUS_STEPS.length - 1 && <div className="step-connector" />}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right PDF viewer */}
        <div className="case-detail-pdf">
          <PDFViewer pdfUrl={pdfUrl} highlightPage={highlightPage} />
        </div>
      </div>
    </div>
  );
}
