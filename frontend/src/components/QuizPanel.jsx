/**
 * components/QuizPanel.jsx
 * ────────────────────────
 * Shows 5 factual questions for a court case.
 * Rules:
 *  - NO AI answers shown before submission
 *  - After submission: show score + AI answers side by side
 *  - Correct and flagged answers use monochrome emphasis
 */

import { useState } from 'react';
import { Send, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import client from '../api/client';

export default function QuizPanel({ caseId, questions, onSubmitted }) {
  const [answers, setAnswers] = useState({});        // { questionId: answerText }
  const [result, setResult] = useState(null);         // post-submission result
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (qId, value) => {
    setAnswers((prev) => ({ ...prev, [qId]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate all answered
    const unanswered = questions.filter((q) => !answers[q.id]?.trim());
    if (unanswered.length > 0) {
      setError('Please answer all 5 questions before submitting.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const { data } = await client.post(`/quiz/${caseId}/submit`, { answers });
      setResult(data);
      if (onSubmitted) onSubmitted(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Submission failed. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Post-submission result view ────────────────────────────────────────────
  if (result) {
    return (
      <div className="quiz-panel">
        <div className="quiz-result-header">
          <div className={`score-circle ${result.match_score >= 80 ? 'score-pass' : 'score-fail'}`}>
            <span className="score-number">{result.match_score}%</span>
            <span className="score-label">Match</span>
          </div>
          <div className="score-status">
            <h3 className={result.status === 'approved' ? 'text-white' : 'text-neutral-200'}>
              {result.status === 'approved' ? '✓ Approved' : '⚠ Flagged for Review'}
            </h3>
            <p className="text-neutral-400 text-sm">
              {result.status === 'approved'
                ? 'Your answers matched the AI extraction. Case approved.'
                : 'Low match score. This case has been sent to admin for review.'}
            </p>
          </div>
        </div>

        <div className="quiz-breakdown">
          {result.breakdown?.map((item, i) => (
            <div key={i} className={`quiz-result-item ${item.match ? 'result-match' : 'result-mismatch'}`}>
              <div className="result-icon">
                {item.match
                  ? <CheckCircle size={16} className="text-white" />
                  : <XCircle size={16} className="text-white" />}
              </div>
              <div className="result-content">
                <p className="result-question">{questions[i]?.question_text}</p>
                <p className="result-your-answer">
                  <span className="label">Your answer:</span> {item.student_answer}
                </p>
                {!item.match && result.ai_answers && (
                  <p className="result-ai-answer">
                    <span className="label">AI answer:</span> {result.ai_answers[item.question_id]}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── Question form ──────────────────────────────────────────────────────────
  return (
    <div className="quiz-panel">
      <div className="quiz-header">
        <h2 className="quiz-title">Case Quiz</h2>
        <p className="quiz-subtitle">Answer all 5 questions based on the judgment PDF.</p>
      </div>

      <form onSubmit={handleSubmit} className="quiz-form">
        {questions.map((q, i) => (
          <div key={q.id} className="quiz-question">
            <label className="question-label">
              <span className="question-num">Q{i + 1}</span>
              {q.question_text}
            </label>
            <textarea
              id={`q-${q.id}`}
              className="question-input"
              rows={2}
              placeholder="Type your answer here…"
              value={answers[q.id] || ''}
              onChange={(e) => handleChange(q.id, e.target.value)}
            />
          </div>
        ))}

        {error && <p className="quiz-error">{error}</p>}

        <button
          type="submit"
          className="quiz-submit-btn"
          disabled={submitting}
          id="quiz-submit-btn"
        >
          {submitting ? (
            <><Loader2 size={16} className="spin" /> Submitting…</>
          ) : (
            <><Send size={16} /> Submit Answers</>
          )}
        </button>
      </form>
    </div>
  );
}
