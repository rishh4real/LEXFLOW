/**
 * components/PDFViewer.jsx
 * ────────────────────────
 * PDF viewer using react-pdf.
 * Supports:
 *  - Page navigation
 *  - Zoom in/out
 *  - Scrolling to a specific page (for source highlights)
 *  - Highlight overlay for source-referenced sentences
 */

import { useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText } from 'lucide-react';

// Point react-pdf worker to CDN (avoids build config complexity)
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export default function PDFViewer({ pdfUrl, highlightPage = null }) {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [loading, setLoading] = useState(true);

  const onDocumentLoadSuccess = useCallback(({ numPages }) => {
    setNumPages(numPages);
    setLoading(false);
  }, []);

  // Jump to highlighted page when source reference is clicked
  if (highlightPage && highlightPage !== currentPage) {
    setCurrentPage(highlightPage);
  }

  return (
    <div className="pdf-viewer">
      {/* Toolbar */}
      <div className="pdf-toolbar">
        <div className="pdf-page-controls">
          <button
            className="pdf-btn"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
          >
            <ChevronLeft size={16} />
          </button>
          <span className="pdf-page-info">
            {currentPage} / {numPages || '—'}
          </span>
          <button
            className="pdf-btn"
            onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
            disabled={currentPage >= numPages}
          >
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="pdf-zoom-controls">
          <button className="pdf-btn" onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}>
            <ZoomOut size={16} />
          </button>
          <span className="pdf-zoom-label">{Math.round(scale * 100)}%</span>
          <button className="pdf-btn" onClick={() => setScale((s) => Math.min(3, s + 0.2))}>
            <ZoomIn size={16} />
          </button>
        </div>
      </div>

      {/* PDF Document */}
      <div className="pdf-scroll-area">
        {!pdfUrl ? (
          <div className="pdf-placeholder">
            <FileText size={48} className="text-slate-600" />
            <p>No PDF loaded</p>
          </div>
        ) : (
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            loading={
              <div className="pdf-placeholder">
                <div className="spinner" />
                <p>Loading PDF…</p>
              </div>
            }
            error={
              <div className="pdf-placeholder">
                <p className="text-rose-400">Failed to load PDF.</p>
              </div>
            }
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              className={highlightPage === currentPage ? 'pdf-page-highlight' : ''}
            />
          </Document>
        )}
      </div>
    </div>
  );
}
