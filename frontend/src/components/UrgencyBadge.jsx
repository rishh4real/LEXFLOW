/**
 * components/UrgencyBadge.jsx
 * ───────────────────────────
 * Displays a color-coded deadline badge.
 * Red   → ≤7 days  (CRITICAL)
 * Amber → ≤30 days (URGENT)
 * Green → >30 days (ON TRACK)
 */

import { Clock, AlertTriangle, CheckCircle } from 'lucide-react';

const CONFIG = {
  red: {
    label: 'CRITICAL',
    cls: 'urgency-red',
    Icon: AlertTriangle,
  },
  amber: {
    label: 'URGENT',
    cls: 'urgency-amber',
    Icon: Clock,
  },
  green: {
    label: 'ON TRACK',
    cls: 'urgency-green',
    Icon: CheckCircle,
  },
};

export default function UrgencyBadge({ urgency = 'green', deadline }) {
  const { label, cls, Icon } = CONFIG[urgency] || CONFIG.green;

  // Compute days remaining for tooltip
  let daysLeft = null;
  if (deadline) {
    const d = new Date(deadline);
    const today = new Date();
    daysLeft = Math.ceil((d - today) / (1000 * 60 * 60 * 24));
  }

  return (
    <div className={`urgency-badge ${cls}`} title={deadline ? `Deadline: ${deadline}` : ''}>
      <Icon size={12} />
      <span>{label}</span>
      {daysLeft !== null && (
        <span className="urgency-days">
          {daysLeft > 0 ? `${daysLeft}d left` : daysLeft === 0 ? 'TODAY' : 'OVERDUE'}
        </span>
      )}
    </div>
  );
}
