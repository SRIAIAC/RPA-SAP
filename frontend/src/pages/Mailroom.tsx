import { Fragment, useEffect, useState } from "react";
import { classifyAllMail, fetchMailMessages } from "../api";
import type { ClassifyResult, MailMessageListItem } from "../api";

export default function MailroomPage() {
  const [messages, setMessages] = useState<MailMessageListItem[]>([]);
  const [results, setResults] = useState<Record<number, ClassifyResult>>({});
  const [running, setRunning] = useState(false);
  const [ranOnce, setRanOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    fetchMailMessages().then(setMessages).catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  async function runTriage() {
    setError(null);
    setRunning(true);
    try {
      const res = await classifyAllMail();
      const byId: Record<number, ClassifyResult> = {};
      for (const r of res.results) byId[r.message_id] = r;
      setResults(byId);
      setRanOnce(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run triage");
    } finally {
      setRunning(false);
    }
  }

  const flaggedCount = Object.values(results).filter((r) => r.is_invoice).length;

  return (
    <div className="stack-lg">
      <h2 className="section-title">Mailroom — invoice triage</h2>
      <p className="section-subtitle">
        Mock inbox of {messages.length || 15} emails. Runs a heuristic classifier over subject/body/attachment
        signals, then OCRs (Tesseract) any attached document to extract invoice fields — proving the pipeline can
        pick invoice-bearing emails out of a mixed inbox without relying on filenames alone.
      </p>
      {error && <div className="form-error">{error}</div>}

      <div className="exception-actions" style={{ marginBottom: "1rem" }}>
        <button className="btn-primary" disabled={running} onClick={runTriage}>
          {running ? "Running AI triage…" : "Run AI triage"}
        </button>
        {ranOnce && (
          <span className="tag tag-dept">
            {flaggedCount} of {messages.length} flagged as invoices
          </span>
        )}
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sender</th>
              <th>Subject</th>
              <th>Department</th>
              <th>Attachment</th>
              <th>AI verdict</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {messages.map((m) => {
              const result = results[m.id];
              const isExpanded = expanded === m.id;
              return (
                <Fragment key={m.id}>
                  <tr>
                    <td>{m.sender_name}</td>
                    <td>{m.subject}</td>
                    <td>
                      <span className="tag tag-dept">{m.department}</span>
                    </td>
                    <td>{m.has_attachment ? "📎" : "—"}</td>
                    <td>
                      {!result && "—"}
                      {result && (
                        <span className={result.is_invoice ? "tag tag-success" : "tag"}>
                          {result.is_invoice ? "Invoice" : "Not invoice"} (
                          {Math.round(result.classifier_confidence * 100)}%)
                        </span>
                      )}
                    </td>
                    <td>
                      {result?.is_invoice && (
                        <button className="btn-ghost" onClick={() => setExpanded(isExpanded ? null : m.id)}>
                          {isExpanded ? "Hide" : "Details"}
                        </button>
                      )}
                    </td>
                  </tr>
                  {isExpanded && result?.extraction && (
                    <tr>
                      <td colSpan={6}>
                        <div className="exception-card">
                          <div className="exception-meta">Why flagged: {result.classifier_reasons.join("; ")}</div>
                          <div className="table-wrap">
                            <table>
                              <tbody>
                                <tr>
                                  <td>Vendor</td>
                                  <td>{result.extraction.vendor_name || "—"}</td>
                                </tr>
                                <tr>
                                  <td>Invoice number</td>
                                  <td>{result.extraction.invoice_number || "—"}</td>
                                </tr>
                                <tr>
                                  <td>Invoice date</td>
                                  <td>{result.extraction.invoice_date || "—"}</td>
                                </tr>
                                <tr>
                                  <td>PO number</td>
                                  <td>{result.extraction.po_number || "—"}</td>
                                </tr>
                                <tr>
                                  <td>Total amount</td>
                                  <td>
                                    {result.extraction.currency} {result.extraction.total_amount || "—"}
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                          <a
                            className="btn-ghost"
                            href={`/api/mailroom/messages/${m.id}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            View raw message JSON
                          </a>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
