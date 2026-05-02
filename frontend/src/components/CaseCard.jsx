/**
 * components/CaseCard.jsx
 * ───────────────────────
 * Card summary for a court case — used in GovDashboard and StudentPortal.
 * Shows case number, parties, deadline badge, department, and a CTA.
 */

import { useNavigate } from 'react-router-dom';
import UrgencyBadge from './UrgencyBadge';
import { FileText, Building2, Calendar, ArrowRight } from 'lucide-react';

export default function CaseCard({ case: c, linkTo }) {
  const navigate = useNavigate();

  const handleClick = () => {
    if (linkTo) navigate(linkTo);
  };

  return (
    <div className="case-card" onClick={handleClick}>
      {/* Header row */}
      <div className="case-card-header">
        <div className="case-number-pill">
          <FileText size={13} />
          <span>{c.case_number || `Case #${c.id}`}</span>
        </div>
        <UrgencyBadge urgency={c.urgency} deadline={c.compliance_deadline} />
      </div>

      {/* Parties */}
      <h3 className="case-parties">{c.parties || 'Parties not extracted yet'}</h3>

      {/* Meta row */}
      <div className="case-meta">
        {c.responsible_dept && (
          <div className="case-meta-item">
            <Building2 size={13} />
            <span>{c.responsible_dept}</span>
          </div>
        )}
        {c.date_of_order && (
          <div className="case-meta-item">
            <Calendar size={13} />
            <span>Order: {c.date_of_order}</span>
          </div>
        )}
        {c.compliance_deadline && (
          <div className="case-meta-item">
            <Calendar size={13} />
            <span>Deadline: {c.compliance_deadline}</span>
          </div>
        )}
      </div>

      {/* Status chip */}
      <div className="case-card-footer">
        <span className={`status-chip status-${c.status}`}>
          {c.status?.toUpperCase()}
        </span>
        {linkTo && (
          <button className="view-btn">
            View Details <ArrowRight size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
