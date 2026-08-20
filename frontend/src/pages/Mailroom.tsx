import { Fragment, useEffect, useRef, useState } from "react";
import {
  classifyAllMail,
  fetchAttachmentObjectUrl,
  fetchMailMessageDetail,
  fetchMailMessages,
  fetchMessageJsonObjectUrl,
  importGmail,
  uploadDocument,
} from "../api";
import type { ClassifyResult, MailMessageDetail, MailMessageListItem } from "../api";
import { useAuth } from "../auth/AuthContext";

export default function MailroomPage() {
  const { user } = useAuth();
  const canImportGmail = user?.level === "Senior Manager" || user?.level === "Department Head" || user?.level === "Admin";

  const [messages, setMessages] = useState<MailMessageListItem[]>([]);
  const [results, setResults] = useState<Record<number, ClassifyResult>>({});
  const [running, setRunning] = useState(false);
  const [ranOnce, setRanOnce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [detailCache, setDetailCache] = useState<Record<number, MailMessageDetail>>({});
  const [detailBusy, setDetailBusy] = useState<number | null>(null);
  const [attachmentBusy, setAttachmentBusy] = useState<number | null>(null);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function reload() {
    return fetchMailMessages().then(setMessages).catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }

  useEffect(() => {
    reload();
  }, []);

  async function runImportGmail() {
    setError(null);
    setImportMessage(null);
    setImporting(true);
    try {
      const res = await importGmail(25); // MAX_IMPORT_LIMIT in app/services/gmail_import.py
      setImportMessage(
        `Imported ${res.imported} new message(s) from Gmail (${res.skipped_duplicates} already imported, ${res.total_fetched} fetched).`
      );
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gmail import failed");
    } finally {
      setImporting(false);
    }
  }

  async function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file later
    if (!file) return;

    setError(null);
    setImportMessage(null);
    setUploading(true);
    try {
      const detail = await uploadDocument(file, file.name);
      setImportMessage(`Uploaded "${detail.subject}" — run AI triage to classify it.`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

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

  async function toggleExpanded(messageId: number) {
    if (expanded === messageId) {
      setExpanded(null);
      return;
    }
    setExpanded(messageId);
    if (detailCache[messageId]) return;
    setAttachmentError(null);
    setDetailBusy(messageId);
    try {
      const detail = await fetchMailMessageDetail(messageId);
      setDetailCache((prev) => ({ ...prev, [messageId]: detail }));
    } catch (err) {
      setAttachmentError(err instanceof Error ? err.message : "Failed to load full message");
    } finally {
      setDetailBusy(null);
    }
  }

  async function openAttachment(messageId: number) {
    setAttachmentError(null);
    setAttachmentBusy(messageId);
    try {
      const detail = await fetchMailMessageDetail(messageId);
      if (!detail.attachment) throw new Error("This message has no attachment.");
      const url = await fetchAttachmentObjectUrl(detail.attachment.id);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setAttachmentError(err instanceof Error ? err.message : "Failed to open attachment");
    } finally {
      setAttachmentBusy(null);
    }
  }

  async function openRawJson(messageId: number) {
    setAttachmentError(null);
    setAttachmentBusy(messageId);
    try {
      const url = await fetchMessageJsonObjectUrl(messageId);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setAttachmentError(err instanceof Error ? err.message : "Failed to open message JSON");
    } finally {
      setAttachmentBusy(null);
    }
  }

  return (
    <div className="stack-lg">
      <h2 className="section-title">Mailroom — invoice triage</h2>
      <p className="section-subtitle">
        Mock inbox of {messages.length || 15} emails. Runs a heuristic classifier over subject/body/attachment
        signals, then OCRs (Tesseract) any attached document to extract invoice fields — proving the pipeline can
        pick invoice-bearing emails out of a mixed inbox without relying on filenames alone.
      </p>
      {error && <div className="form-error">{error}</div>}
      {attachmentError && <div className="form-error">{attachmentError}</div>}
      {importMessage && <div className="tag tag-dept">{importMessage}</div>}

      <div className="exception-actions" style={{ marginBottom: "1rem" }}>
        <button className="btn-primary" disabled={running} onClick={runTriage}>
          {running ? "Running AI triage…" : "Run AI triage"}
        </button>
        {ranOnce && (
          <span className="tag tag-dept">
            {flaggedCount} of {messages.length} flagged as invoices
          </span>
        )}
        {canImportGmail && (
          <button className="btn-ghost" disabled={importing} onClick={runImportGmail} title="Requires GMAIL_ADDRESS/GMAIL_APP_PASSWORD configured on the backend">
            {importing ? "Importing…" : "Import from Gmail"}
          </button>
        )}
        <button className="btn-ghost" disabled={uploading} onClick={() => fileInputRef.current?.click()}>
          {uploading ? "Uploading…" : "Upload a real invoice"}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,application/pdf"
          style={{ display: "none" }}
          onChange={onFileSelected}
        />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sender</th>
              <th>Subject</th>
              <th>Department</th>
              <th>Source</th>
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
                    <td>
                      <span className={m.source === "seed" ? "tag" : "tag tag-success"}>
                        {m.source === "gmail_import" ? "Gmail (real)" : m.source === "upload" ? "Uploaded (real)" : "Demo"}
                      </span>
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
                      <button className="btn-ghost" onClick={() => toggleExpanded(m.id)}>
                        {isExpanded ? "Hide" : "View mail"}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={7}>
                        <div className="exception-card">
                          {detailBusy === m.id && !detailCache[m.id] && <div className="exception-meta">Loading full message…</div>}
                          {detailCache[m.id] && (
                            <>
                              <div className="exception-meta">
                                From: {detailCache[m.id].sender_name} &lt;{detailCache[m.id].sender}&gt; · {new Date(detailCache[m.id].received_at).toLocaleString()}
                              </div>
                              <pre
                                style={{
                                  whiteSpace: "pre-wrap",
                                  wordBreak: "break-word",
                                  margin: 0,
                                  fontFamily: "inherit",
                                  fontSize: "13px",
                                }}
                              >
                                {detailCache[m.id].body || "(no body content)"}
                              </pre>
                            </>
                          )}
                          {result?.extraction && (
                            <>
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
                            </>
                          )}
                          <div className="exception-actions">
                            {m.has_attachment && (
                              <button
                                className="btn-ghost"
                                disabled={attachmentBusy === m.id}
                                onClick={() => openAttachment(m.id)}
                              >
                                {attachmentBusy === m.id ? "Opening…" : "View attachment"}
                              </button>
                            )}
                            <button
                              className="btn-ghost"
                              disabled={attachmentBusy === m.id}
                              onClick={() => openRawJson(m.id)}
                            >
                              View raw message JSON
                            </button>
                          </div>
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
